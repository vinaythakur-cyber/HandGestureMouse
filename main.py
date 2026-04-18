# =============================================================================
#  main.py  —  NIYANTA  |  Hand Gesture Virtual Mouse
#  Cross-platform: Windows 11 · macOS · Linux
# =============================================================================

import cv2
import sys
import time
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

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
    print("Place hand_landmarker.task in the same folder as this file.")
    sys.exit(1)

# ── Camera ────────────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(config.CAMERA_INDEX)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("ERROR: Cannot open camera")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
cap.set(cv2.CAP_PROP_FPS,          config.CAMERA_FPS)

# MJPG gives better FPS on Windows/Linux but causes issues on macOS
if sys.platform != "darwin":
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

# ── Window ────────────────────────────────────────────────────────────────────
WINDOW_NAME = "Niyanta - Hand Gesture Mouse"
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, config.FRAME_WIDTH, config.FRAME_HEIGHT)

# ── Hand detector ─────────────────────────────────────────────────────────────
detector = hm.HandDetector()

pTime = 0
start = time.time()

LEGEND = [
    ("VOL    : Pinch + Mid UP",         (0,   200, 255)),
    ("R-CLK  : Thumb+Mid tight",        (0,   100, 255)),
    ("WIN-TAB: 4 fingers, thumb DOWN",  (200, 100, 255)),
    ("BRIGHT : All 5 open, spread",     (180, 100, 255)),
    ("PG-UP  : Fist + thumb UP",        (100, 255, 100)),
    ("PG-DN  : Fist + thumb DOWN",      (100, 100, 255)),
    ("MOVE   : Index UP + open pinch",  (0,   255,   0)),
    ("DRAG   : Pinch + Ring UP",        (0,   200, 200)),
    ("L-CLK  : Pinch + Ring DOWN",      (0,   255, 255)),
]

print("=" * 55)
print("  NIYANTA — Hand Gesture Virtual Mouse")
print(f"  Platform : {sys.platform}")
print("  Quit     : Press Q or ESC inside the window")
print("=" * 55)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════
while True:

    # ── Window-close detection (X button) ─────────────────────────────────────
    # WND_PROP_VISIBLE works on Windows and Linux.
    # On macOS it always returns -1, so we skip the check there.
    if sys.platform != "darwin":
        try:
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
        except Exception:
            break

    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)
    h, w  = frame.shape[:2]
    ts_ms = int((time.time() - start) * 1000)

    # ── Active zone box ────────────────────────────────────────────────────────
    m = config.MARGIN
    cv2.rectangle(frame, (m, m), (w - m, h - m), (80, 80, 80), 1)
    cv2.putText(frame, "Active zone", (m + 4, m - 6),
                cv2.FONT_HERSHEY_PLAIN, 1, (80, 80, 80), 1)

    # ── Detection + dispatch ───────────────────────────────────────────────────
    hand_data = detector.process(frame, ts_ms)

    if hand_data:
        hand_data.draw(frame)
        gesture = gd.detect(hand_data)

        if gesture == gd.VOLUME:
            act.do_volume(hand_data, frame)
            act.release_drag(); act.reset_clicks()
            act.reset_scroll(); act.reset_win_switch()

        elif gesture == gd.RIGHT_CLICK:
            act.do_right_click(hand_data, frame)
            act.release_drag()
            act.reset_scroll(); act.reset_win_switch()

        elif gesture == gd.WIN_TAB:
            act.do_win_tab(frame)
            act.release_drag(); act.reset_clicks(); act.reset_scroll()

        elif gesture == gd.BRIGHTNESS:
            act.do_brightness(hand_data, frame)
            act.release_drag(); act.reset_clicks()
            act.reset_scroll(); act.reset_win_switch()

        elif gesture == gd.PAGE_UP:
            act.do_page_up(frame)
            act.release_drag(); act.reset_clicks(); act.reset_win_switch()

        elif gesture == gd.PAGE_DOWN:
            act.do_page_down(frame)
            act.release_drag(); act.reset_clicks(); act.reset_win_switch()

        elif gesture == gd.MOVE:
            act.do_move(hand_data, frame)
            act.release_drag(); act.reset_clicks()
            act.reset_scroll(); act.reset_win_switch()

        elif gesture == gd.DRAG:
            act.do_drag(hand_data, frame)
            act.reset_clicks(); act.reset_scroll(); act.reset_win_switch()

        elif gesture == gd.LEFT_CLICK:
            act.do_left_click(hand_data, frame)
            act.release_drag()
            act.reset_scroll(); act.reset_win_switch()

        else:   # NEUTRAL
            act.release_drag(); act.reset_clicks()
            act.reset_scroll(); act.reset_win_switch()
            cv2.putText(frame, "---", (10, 90),
                        cv2.FONT_HERSHEY_PLAIN, 2, (150, 150, 150), 2)

        cv2.putText(frame, f"Gesture: {gesture}", (10, h - 10),
                    cv2.FONT_HERSHEY_PLAIN, 1.2, (200, 200, 200), 1)

    else:
        act.release_drag(); act.reset_clicks()
        act.reset_scroll(); act.reset_win_switch()

    # ── Drag indicator bar ─────────────────────────────────────────────────────
    if act.is_dragging():
        cv2.rectangle(frame, (0, 0), (10, h), (0, 200, 200), cv2.FILLED)

    # ── Legend ─────────────────────────────────────────────────────────────────
    for i, (text, col) in enumerate(LEGEND):
        cv2.putText(frame, text, (w - 340, 26 + i * 22),
                    cv2.FONT_HERSHEY_PLAIN, 1, col, 1)

    # ── Watermark ─────────────────────────────────────────────────────────────
    cv2.putText(frame, "NIYANTA", (w - 100, h - 10),
                cv2.FONT_HERSHEY_PLAIN, 1.2, (0, 255, 200), 1)

    # ── FPS ────────────────────────────────────────────────────────────────────
    cTime = time.time()
    fps   = 1 / (cTime - pTime + 1e-9)
    pTime = cTime
    cv2.putText(frame, f"FPS: {int(fps)}", (10, 50),
                cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 2)

    cv2.imshow(WINDOW_NAME, frame)

    # ── Q or ESC to quit ───────────────────────────────────────────────────────
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == 27:
        break

# ── Cleanup ───────────────────────────────────────────────────────────────────
act.release_drag()
cap.release()
cv2.destroyAllWindows()
sys.exit(0)
