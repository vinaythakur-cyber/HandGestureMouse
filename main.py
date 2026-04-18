# =============================================================================
#  main.py  —  THE ONLY FILE YOU NEED TO RUN
#  ─────────────────────────────────────────────────────────────────────────────
#  Flow per frame:
#    1. Read camera frame
#    2. hand_module   → detect hand landmarks
#    3. gesture_detector → classify gesture
#    4. actions       → execute the action
#    5. Draw HUD + legend, show frame
#
#  ┌──────────────────────┬────────────────────────────────────────────────┐
#  │ File                 │ Responsible for                                │
#  ├──────────────────────┼────────────────────────────────────────────────┤
#  │ config.py            │ All tunable numbers (margins, thresholds…)    │
#  │ hand_module.py       │ MediaPipe wrapper, landmark coords, finger up  │
#  │ gesture_detector.py  │ Which gesture is the user making               │
#  │ actions.py           │ What to DO for each gesture (platform-aware)  │
#  │ main.py  (this file) │ Camera loop, dispatch, HUD                    │
#  └──────────────────────┴────────────────────────────────────────────────┘
#
#  SUPPORTED GESTURES:
#    VOLUME      → Pinch (thumb+index) + Middle UP
#    RIGHT_CLICK → Thumb + Middle tight pinch, others DOWN
#    WIN_TAB     → 4 fingers UP, thumb folded  (Win+Tab / Mission Ctrl / Super+Tab)
#    BRIGHTNESS  → All 5 fingers open — spread = brighter, close = dimmer
#    PAGE_UP     → Fist + thumb pointing UP  👍  (hold to keep scrolling)
#    PAGE_DOWN   → Fist + thumb pointing DOWN 👎  (hold to keep scrolling)
#    MOVE        → Index UP + open pinch + middle DOWN
#    DRAG        → Tight pinch + Ring UP + middle DOWN
#    LEFT_CLICK  → Tight pinch + Ring DOWN + middle DOWN
# =============================================================================

import cv2
import sys
import time
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'   # suppress TensorFlow info logs

import config
import hand_module      as hm
import gesture_detector as gd
import actions          as act

import pyautogui
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0

# ── Sanity check ──────────────────────────────────────────────────────────────
if not os.path.exists(config.MODEL_PATH):
    print(f"ERROR: hand_landmarker.task not found at:\n  {config.MODEL_PATH}")
    print("Place hand_landmarker.task in the same folder as main.py")
    sys.exit()

# ── Camera ────────────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(config.CAMERA_INDEX)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
cap.set(cv2.CAP_PROP_FPS,          config.CAMERA_FPS)

# MJPG codec works on Windows & Linux but NOT on macOS — skip it on Mac
if sys.platform != "darwin":
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

# ── Hand detector ─────────────────────────────────────────────────────────────
detector = hm.HandDetector()

# ── Timing ────────────────────────────────────────────────────────────────────
pTime = 0
start = time.time()

# ── Gesture legend (top-right corner) ────────────────────────────────────────
LEGEND = [
    ("VOL    : Pinch + Mid UP",         (0,   200, 255)),
    ("R-CLK  : Thumb+Mid tight",        (0,   100, 255)),
    ("WIN-TAB: 4 fingers, thumb DOWN",  (200, 100, 255)),
    ("BRIGHT : All 5 open, spread",     (0,   230, 255)),
    ("PG-UP  : Fist + thumb UP  👍",   (100, 255, 100)),
    ("PG-DN  : Fist + thumb DOWN 👎",  (100, 100, 255)),
    ("MOVE   : Index UP + open pinch",  (0,   255,   0)),
    ("DRAG   : Pinch + Ring UP",        (0,   200, 200)),
    ("L-CLK  : Pinch + Ring DOWN",      (0,   255, 255)),
]

# ── Console summary ───────────────────────────────────────────────────────────
print("=" * 58)
print("  Hand Gesture Virtual Mouse — running")
print(f"  Platform: {sys.platform}")
print("=" * 58)
for text, _ in LEGEND:
    print(f"  {text}")
print("-" * 58)
print("  Press Q to quit")
print("=" * 58)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════
while True:
    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)       # mirror — makes movement feel natural
    h, w  = frame.shape[:2]
    ts_ms = int((time.time() - start) * 1000)   # monotonic ms timestamp

    # ── Active zone guide box ──────────────────────────────────────────────────
    m = config.MARGIN
    cv2.rectangle(frame, (m, m), (w - m, h - m), (80, 80, 80), 1)
    cv2.putText(frame, "Active zone", (m + 4, m - 6),
                cv2.FONT_HERSHEY_PLAIN, 1, (80, 80, 80), 1)

    # ── Hand detection ─────────────────────────────────────────────────────────
    hand_data = detector.process(frame, ts_ms)

    if hand_data:
        hand_data.draw(frame)
        gesture = gd.detect(hand_data)

        # ── Dispatch ───────────────────────────────────────────────────────────
        if gesture == gd.VOLUME:
            act.do_volume(hand_data, frame)
            act.release_drag()
            act.reset_clicks()
            act.reset_scroll()
            act.reset_win_switch()

        elif gesture == gd.RIGHT_CLICK:
            act.do_right_click(hand_data, frame)
            act.release_drag()
            act.reset_scroll()
            act.reset_win_switch()

        elif gesture == gd.WIN_TAB:
            act.do_win_tab(frame)
            act.release_drag()
            act.reset_clicks()
            act.reset_scroll()

        elif gesture == gd.BRIGHTNESS:
            act.do_brightness(hand_data, frame)
            act.release_drag()
            act.reset_clicks()
            act.reset_scroll()
            act.reset_win_switch()

        elif gesture == gd.PAGE_UP:
            act.do_page_up(frame)
            act.release_drag()
            act.reset_clicks()
            act.reset_win_switch()
            # Note: do NOT reset_scroll — it tracks scroll timing

        elif gesture == gd.PAGE_DOWN:
            act.do_page_down(frame)
            act.release_drag()
            act.reset_clicks()
            act.reset_win_switch()

        elif gesture == gd.MOVE:
            act.do_move(hand_data, frame)
            act.release_drag()
            act.reset_clicks()
            act.reset_scroll()
            act.reset_win_switch()

        elif gesture == gd.DRAG:
            act.do_drag(hand_data, frame)
            act.reset_clicks()
            act.reset_scroll()
            act.reset_win_switch()

        elif gesture == gd.LEFT_CLICK:
            act.do_left_click(hand_data, frame)
            act.release_drag()
            act.reset_scroll()
            act.reset_win_switch()

        else:   # NEUTRAL
            act.release_drag()
            act.reset_clicks()
            act.reset_scroll()
            act.reset_win_switch()
            cv2.putText(frame, "---", (10, 90),
                        cv2.FONT_HERSHEY_PLAIN, 2, (150, 150, 150), 2)

        # Current gesture name — bottom-left for debugging
        cv2.putText(frame, f"Gesture: {gesture}", (10, h - 10),
                    cv2.FONT_HERSHEY_PLAIN, 1.2, (200, 200, 200), 1)

    else:
        # No hand detected — always release mouse so it never stays stuck
        act.release_drag()
        act.reset_clicks()
        act.reset_scroll()
        act.reset_win_switch()

    # ── Drag indicator (thin teal bar on left edge) ────────────────────────────
    if act.is_dragging():
        cv2.rectangle(frame, (0, 0), (10, h), (0, 200, 200), cv2.FILLED)

    # ── Legend ─────────────────────────────────────────────────────────────────
    for i, (text, col) in enumerate(LEGEND):
        cv2.putText(frame, text, (w - 340, 26 + i * 22),
                    cv2.FONT_HERSHEY_PLAIN, 1, col, 1)

    # ── FPS ────────────────────────────────────────────────────────────────────
    cTime = time.time()
    fps   = 1 / (cTime - pTime + 1e-9)
    pTime = cTime
    cv2.putText(frame, f"FPS: {int(fps)}", (10, 50),
                cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 2)

    cv2.imshow("Hand Gesture Virtual Mouse", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ── Cleanup ───────────────────────────────────────────────────────────────────
act.release_drag()
cap.release()
cv2.destroyAllWindows()
