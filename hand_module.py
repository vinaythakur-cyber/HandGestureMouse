# =============================================================================
#  hand_module.py
#  ─────────────────────────────────────────────────────────────────────────────
#  Wraps MediaPipe Hand Landmarker.
#  Responsible for:
#    - Setting up the detector
#    - Running detection on each frame
#    - Giving back pixel coordinates of all 21 landmarks
#    - Telling you which fingers are up or down
#    - Telling you thumb direction (up / down / neutral) for fist gestures
#    - Drawing landmarks on the frame
# =============================================================================

import cv2
import math
import mediapipe as mp
import config

# ── MediaPipe setup ───────────────────────────────────────────────────────────
BaseOptions        = mp.tasks.BaseOptions
HandLandmarker     = mp.tasks.vision.HandLandmarker
HandLandmarkerOpts = mp.tasks.vision.HandLandmarkerOptions
RunningMode        = mp.tasks.vision.RunningMode

# Skeleton connections — pairs of landmark IDs to draw lines between
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),          # thumb
    (0,5),(5,6),(6,7),(7,8),          # index finger
    (5,9),(9,10),(10,11),(11,12),     # middle finger
    (9,13),(13,14),(14,15),(15,16),   # ring finger
    (13,17),(17,18),(18,19),(19,20),  # pinky
    (0,17)                            # palm base
]


class HandDetector:
    """
    Detects one hand in a video frame and exposes landmark data.

    Usage
    -----
        detector = HandDetector()
        while True:
            ok, frame = cap.read()
            hand_data = detector.process(frame, timestamp_ms)
            if hand_data:
                fingers = hand_data.fingers_up()
    """

    def __init__(self):
        opts = HandLandmarkerOpts(
            base_options=BaseOptions(model_asset_path=config.MODEL_PATH),
            running_mode=RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=config.DETECT_CONF,
            min_hand_presence_confidence=config.DETECT_CONF,
            min_tracking_confidence=config.TRACK_CONF,
        )
        self._detector = HandLandmarker.create_from_options(opts)

    def process(self, bgr_frame, timestamp_ms):
        """
        Run detection on one frame.

        Parameters
        ----------
        bgr_frame    : numpy array from cv2.VideoCapture (already flipped)
        timestamp_ms : int — monotonic millisecond timestamp

        Returns
        -------
        HandData object if a hand is found, else None
        """
        rgb      = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results  = self._detector.detect_for_video(mp_image, timestamp_ms)

        if results.hand_landmarks:
            landmarks  = results.hand_landmarks[0]
            handedness = results.handedness[0][0].category_name if results.handedness else 'Left'
            h, w, _    = bgr_frame.shape
            return HandData(landmarks, handedness, w, h)
        return None


class HandData:
    """
    Holds landmark data for ONE detected hand and provides helper methods.

    Landmarks (normalised 0-1 coords, origin = top-left of frame):
        0  = Wrist
        4  = Thumb tip
        8  = Index tip
        12 = Middle tip
        16 = Ring tip
        20 = Pinky tip
        (and all intermediate joints)

    After cv2.flip(frame,1):  smaller y = higher on screen
    MediaPipe 'Left' label   = actual right hand (mirror effect)
    """

    def __init__(self, landmarks, handedness_label, frame_w, frame_h):
        self.lm    = landmarks
        self.label = handedness_label
        self.w     = frame_w
        self.h     = frame_h

    # ── Coordinate helpers ─────────────────────────────────────────────────────
    def px(self, lm_id):
        """Return pixel (x, y) for a landmark ID."""
        return (int(self.lm[lm_id].x * self.w),
                int(self.lm[lm_id].y * self.h))

    def dist(self, id_a, id_b):
        """Euclidean pixel distance between two landmark IDs."""
        ax, ay = self.px(id_a)
        bx, by = self.px(id_b)
        return math.hypot(bx - ax, by - ay)

    def avg_spread(self, tip_ids, anchor_id=4):
        """
        Average pixel distance from anchor landmark to a list of tip landmarks.
        Used for the brightness gesture — measures how spread the fingers are
        relative to the thumb tip (landmark 4).
        """
        anchor = self.px(anchor_id)
        total  = sum(
            math.hypot(self.px(t)[0] - anchor[0],
                       self.px(t)[1] - anchor[1])
            for t in tip_ids
        )
        return total / len(tip_ids)

    # ── Finger state helpers ───────────────────────────────────────────────────
    def _finger_up(self, tip, pip):
        """True if tip landmark is above (smaller y) than pip joint."""
        return self.lm[tip].y < self.lm[pip].y

    def _thumb_up(self):
        """
        Thumb moves laterally, not vertically.
        After mirror-flip: MediaPipe 'Left' label = real right hand.
        Used only inside fingers_up() — NOT for fist thumb direction.
        """
        is_right = (self.label == 'Left')
        if is_right:
            return self.lm[4].x > self.lm[3].x
        else:
            return self.lm[4].x < self.lm[3].x

    def fingers_up(self):
        """
        Returns a list of 5 booleans:
            [thumb, index, middle, ring, pinky]
            True  = finger is raised / open
            False = finger is folded / closed
        """
        return [
            self._thumb_up(),
            self._finger_up(8,  6),    # index
            self._finger_up(12, 10),   # middle
            self._finger_up(16, 14),   # ring
            self._finger_up(20, 18),   # pinky
        ]

    def thumb_direction(self):
        """
        Detects whether the thumb is pointing UP or DOWN
        when the hand is in a FIST (other fingers folded).

        Returns
        -------
        'up'      — thumb tip is well ABOVE the wrist  (👍 like button)
        'down'    — thumb tip is well BELOW the wrist  (👎 dislike button)
        'neutral' — thumb is not clearly pointing either way

        How it works:
            In a normal camera view with cv2.flip(frame,1):
                Smaller y value = higher on the screen.
            Wrist = landmark 0.
            Thumb tip = landmark 4.
            Thumb UP   → tip.y  <  wrist.y  − THUMB_DIR_THRESH
            Thumb DOWN → tip.y  >  wrist.y  + THUMB_DIR_THRESH
        """
        tip_y   = self.lm[4].y * self.h    # thumb tip   y in pixels
        wrist_y = self.lm[0].y * self.h    # wrist joint y in pixels
        thresh  = config.THUMB_DIR_THRESH

        if tip_y < wrist_y - thresh:
            return 'up'
        elif tip_y > wrist_y + thresh:
            return 'down'
        return 'neutral'

    # ── Drawing ────────────────────────────────────────────────────────────────
    def draw(self, frame):
        """Draw all 21 landmark dots and skeleton lines onto frame."""
        pts = [self.px(i) for i in range(21)]

        # Skeleton lines
        for s, e in HAND_CONNECTIONS:
            cv2.line(frame, pts[s], pts[e], (0, 220, 0), 2)

        # Landmark dots
        for cx, cy in pts:
            cv2.circle(frame, (cx, cy), 4, (0, 180, 0), cv2.FILLED)

        # Highlight key tips with colours
        cv2.circle(frame, pts[4],  10, (255, 100,   0), cv2.FILLED)  # thumb  = orange
        cv2.circle(frame, pts[8],  12, (0,     0, 255), cv2.FILLED)  # index  = red
        cv2.circle(frame, pts[12], 10, (255, 255,   0), cv2.FILLED)  # middle = yellow
        cv2.circle(frame, pts[16], 10, (0,   200, 200), cv2.FILLED)  # ring   = teal
        cv2.circle(frame, pts[20], 10, (200,   0, 200), cv2.FILLED)  # pinky  = purple
