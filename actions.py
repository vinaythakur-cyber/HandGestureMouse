# =============================================================================
#  actions.py
#  ─────────────────────────────────────────────────────────────────────────────
#  Each function here DOES something:
#    moves cursor / clicks / drags / volume / brightness / scroll / win-switch
#
#  main.py calls the right function based on gesture_detector output.
#  This file has ZERO gesture logic — it only executes actions.
#
#  PLATFORM INDEPENDENCE:
#    Volume    → pycaw (Windows) / osascript (macOS) / amixer (Linux)
#    Brightness→ screen-brightness-control  (works on all 3 OS)
#    Scroll    → pyautogui.scroll()         (works on all 3 OS)
#    Win-switch→ per-OS hotkey              (Win+Tab / Ctrl+Up / Super+Tab)
#    Camera    → MJPG codec skipped on Mac  (handled in main.py)
# =============================================================================

import sys
import subprocess
import cv2
import numpy as np
import pyautogui
import config

OS = sys.platform
# sys.platform values:
#   'win32'  → Windows
#   'darwin' → macOS
#   'linux'  → Linux (all distros)


# =============================================================================
#  VOLUME  — platform-specific backends
# =============================================================================
VOLUME_ENABLED = False

def _try_init_volume():
    global VOLUME_ENABLED, _win_vol_obj, VOL_MIN, VOL_MAX
    VOL_MIN = 0
    VOL_MAX = 100

    if OS == 'win32':
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices    = AudioUtilities.GetSpeakers()
            interface  = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            from ctypes import cast, POINTER
            _win_vol_obj       = cast(interface, POINTER(IAudioEndpointVolume))
            VOL_MIN, VOL_MAX   = _win_vol_obj.GetVolumeRange()[:2]
            VOLUME_ENABLED     = True
        except Exception as e:
            print(f"[Volume] Windows init failed: {e}")
    elif OS == 'darwin':
        # macOS — test if osascript is available
        try:
            subprocess.run(["osascript", "-e", "output volume of (get volume settings)"],
                           check=True, capture_output=True)
            VOLUME_ENABLED = True
        except Exception as e:
            print(f"[Volume] macOS init failed: {e}")
    else:
        # Linux — test if amixer is available
        try:
            subprocess.run(["amixer", "sget", "Master"],
                           check=True, capture_output=True)
            VOLUME_ENABLED = True
        except Exception as e:
            print(f"[Volume] Linux init failed: {e}")
            print("  Install: sudo apt install alsa-utils")

_win_vol_obj = None
_try_init_volume()


def _set_volume(pct):
    """Set system volume. pct = 0 to 100."""
    pct = max(0, min(100, int(pct)))
    if OS == 'win32' and _win_vol_obj is not None:
        # Convert 0-100 to dB range
        vol_db = np.interp(pct, [0, 100], [VOL_MIN, VOL_MAX])
        _win_vol_obj.SetMasterVolumeLevel(float(vol_db), None)
    elif OS == 'darwin':
        subprocess.run(["osascript", "-e", f"set volume output volume {pct}"],
                       capture_output=True)
    else:
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{pct}%"],
                       capture_output=True)


# =============================================================================
#  BRIGHTNESS  — uses screen-brightness-control (cross-platform pip package)
# =============================================================================
BRIGHTNESS_ENABLED = False

try:
    import screen_brightness_control as sbc
    BRIGHTNESS_ENABLED = True
except ImportError:
    print("[Brightness] Install: pip install screen-brightness-control")

def _set_brightness(pct):
    """Set screen brightness. pct = 0 to 100."""
    if not BRIGHTNESS_ENABLED:
        return
    pct = max(0, min(100, int(pct)))
    try:
        sbc.set_brightness(pct)
    except Exception as e:
        print(f"[Brightness] set failed: {e}")


# =============================================================================
#  CURSOR STATE  (shared between move and drag)
# =============================================================================
class CursorState:
    """Holds smoothed cursor position so movement stays fluid."""
    def __init__(self):
        sw, sh = pyautogui.size()
        self.x = sw // 2
        self.y = sh // 2

cursor = CursorState()


def _smooth_move(raw_x, raw_y, frame_w, frame_h):
    """
    Map a pixel position inside the active zone to full screen coordinates,
    apply exponential smoothing, move the cursor, save state.
    """
    target_x = np.interp(raw_x, (config.MARGIN, frame_w - config.MARGIN),
                         (0, pyautogui.size()[0]))
    target_y = np.interp(raw_y, (config.MARGIN, frame_h - config.MARGIN),
                         (0, pyautogui.size()[1]))
    cursor.x = int(cursor.x + (target_x - cursor.x) * config.SMOOTH)
    cursor.y = int(cursor.y + (target_y - cursor.y) * config.SMOOTH)
    pyautogui.moveTo(cursor.x, cursor.y)


# =============================================================================
#  ACTION FUNCTIONS — one per gesture
# =============================================================================

# ── MOVE ───────────────────────────────────────────────────────────────────────
def do_move(hand_data, frame):
    """Move cursor using index fingertip position."""
    ix, iy = hand_data.px(8)
    h, w   = frame.shape[:2]
    _smooth_move(ix, iy, w, h)
    cv2.putText(frame, "MOVE", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)


# ── DRAG ───────────────────────────────────────────────────────────────────────
_dragging = False

def do_drag(hand_data, frame):
    """Hold mouse button down and move cursor with pinch midpoint."""
    global _dragging
    tx, ty = hand_data.px(4)
    ix, iy = hand_data.px(8)
    cx_d   = (tx + ix) // 2
    cy_d   = (ty + iy) // 2
    h, w   = frame.shape[:2]

    if not _dragging:
        pyautogui.mouseDown()
        _dragging = True

    _smooth_move(cx_d, cy_d, w, h)

    cv2.line(frame,   (tx, ty), (ix, iy), (0, 200, 200), 3)
    cv2.circle(frame, (cx_d, cy_d), 20, (0, 200, 200), cv2.FILLED)
    cv2.circle(frame, (cx_d, cy_d), 24, (255, 255, 255), 2)
    cv2.putText(frame, "DRAGGING...", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 200, 200), 2)
    cv2.putText(frame, "Lower ring finger to DROP", (10, 118),
                cv2.FONT_HERSHEY_PLAIN, 1.1, (0, 200, 200), 1)

def release_drag():
    global _dragging
    if _dragging:
        pyautogui.mouseUp()
        _dragging = False

def is_dragging():
    return _dragging


# ── CLICKS ─────────────────────────────────────────────────────────────────────
_left_count  = 0
_left_fired  = False
_right_count = 0
_right_fired = False

def do_left_click(hand_data, frame):
    """Left click fires after HOLD_NEEDED consecutive frames of tight pinch."""
    global _left_count, _left_fired, _right_count, _right_fired
    _right_count = 0
    _right_fired = False

    tx, ty = hand_data.px(4)
    ix, iy = hand_data.px(8)
    cx_l   = (tx + ix) // 2
    cy_l   = (ty + iy) // 2
    _left_count += 1

    prog  = min(_left_count / config.HOLD_NEEDED, 1.0)
    cv2.line(frame,   (tx, ty), (ix, iy), (0, 255, 255), 3)
    cv2.circle(frame, (cx_l, cy_l), 18, (0, int(255 * prog), 255), cv2.FILLED)

    if _left_count >= config.HOLD_NEEDED and not _left_fired:
        pyautogui.click()
        _left_fired = True
        cv2.putText(frame, "LEFT CLICKED!", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)
    else:
        cv2.putText(frame, f"L-Hold... {_left_count}/{config.HOLD_NEEDED}", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 2, (255, 200, 0), 2)

def do_right_click(hand_data, frame):
    """Right click fires after HOLD_NEEDED consecutive frames of mid-pinch."""
    global _right_count, _right_fired, _left_count, _left_fired
    _left_count  = 0
    _left_fired  = False

    tx, ty = hand_data.px(4)
    mx, my = hand_data.px(12)
    cx_r   = (tx + mx) // 2
    cy_r   = (ty + my) // 2
    _right_count += 1

    prog  = min(_right_count / config.HOLD_NEEDED, 1.0)
    cv2.line(frame,   (tx, ty), (mx, my), (0, 100, 255), 3)
    cv2.circle(frame, (cx_r, cy_r), 18, (0, int(255 * prog), 180), cv2.FILLED)

    if _right_count >= config.HOLD_NEEDED and not _right_fired:
        pyautogui.rightClick()
        _right_fired = True
        cv2.putText(frame, "RIGHT CLICKED!", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 100, 255), 2)
    else:
        cv2.putText(frame, f"R-Hold... {_right_count}/{config.HOLD_NEEDED}", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 255), 2)

def reset_clicks():
    global _left_count, _left_fired, _right_count, _right_fired
    _left_count  = 0
    _left_fired  = False
    _right_count = 0
    _right_fired = False


# ── VOLUME ─────────────────────────────────────────────────────────────────────
_vol_bar = 400
_vol_pct = 0.0

def do_volume(hand_data, frame):
    """
    Volume control — maps thumb-index pinch distance to system volume.
    Closer pinch = lower volume. Wider = louder.
    """
    global _vol_bar, _vol_pct

    if not VOLUME_ENABLED:
        cv2.putText(frame, "VOL: not available on this system", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 1.4, (0, 100, 255), 2)
        return

    dist     = hand_data.dist(4, 8)
    _vol_bar = np.interp(dist, [20, 200], [400, 150])
    _vol_pct = np.interp(dist, [20, 200], [0, 100])

    _set_volume(_vol_pct)

    cv2.putText(frame, "VOL MODE", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 200, 255), 2)
    cv2.rectangle(frame, (50, 150), (82, 400), (0, 200, 255), 2)
    cv2.rectangle(frame, (50, int(_vol_bar)), (82, 400), (0, 200, 255), cv2.FILLED)
    cv2.putText(frame, f'{int(_vol_pct)}%', (30, 430),
                cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 200, 255), 2)


# ── BRIGHTNESS ─────────────────────────────────────────────────────────────────
_bright_pct  = 50.0
_bright_bar  = 275   # bar y position (middle of 150-400 range)

def do_brightness(hand_data, frame):
    """
    Brightness control — 'dinosaur / spread hand' gesture.

    All 5 fingers open. The AVERAGE distance from thumb tip (landmark 4)
    to the 4 fingertips [8, 12, 16, 20] controls screen brightness:
        fingers spread far apart  →  high brightness  (bright screen)
        fingers closed toward thumb → low brightness  (dim screen)

    Visual feedback:
        Yellow bar on the RIGHT side of frame (opposite to volume bar)
    """
    global _bright_pct, _bright_bar

    if not BRIGHTNESS_ENABLED:
        cv2.putText(frame, "Brightness: install screen-brightness-control", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 1.2, (0, 200, 255), 1)
        return

    # CORRECT — thumb is folded, measure distance from WRIST (0)
    # to middle fingertip (12) as proxy for how open the 4 fingers are
    # OR measure thumb tip (4) to index tip (8) — the beak opening distance
    spread = hand_data.dist(4, 20)   # thumb tip to index tip = beak distanc
    _bright_pct = np.interp(spread,
                            [config.BRIGHT_MIN_DIST, config.BRIGHT_MAX_DIST],
                            [0, 100])
    _bright_bar = np.interp(spread,
                            [config.BRIGHT_MIN_DIST, config.BRIGHT_MAX_DIST],
                            [400, 150])

    _set_brightness(_bright_pct)

    h, w = frame.shape[:2]

    # Bar on right side so it doesn't overlap volume bar
    bar_x = w - 90
    cv2.putText(frame, "BRIGHTNESS", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 230, 255), 2)
    cv2.putText(frame, "Open/close fingers like duck face", (10, 118),
                cv2.FONT_HERSHEY_PLAIN, 1.1, (0, 230, 255), 1)
    cv2.rectangle(frame, (bar_x, 150), (bar_x + 32, 400), (0, 230, 255), 2)
    cv2.rectangle(frame, (bar_x, int(_bright_bar)), (bar_x + 32, 400),
                  (0, 230, 255), cv2.FILLED)
    cv2.putText(frame, f'{int(_bright_pct)}%', (bar_x - 10, 430),
                cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 230, 255), 2)

    # Draw lines from thumb tip to each fingertip to visualise spread
    tx, ty = hand_data.px(4)
    for tip_id in [8, 12, 16, 20]:
        fx, fy = hand_data.px(tip_id)
        cv2.line(frame, (tx, ty), (fx, fy), (0, 230, 255), 1)


# ── PAGE UP / PAGE DOWN ────────────────────────────────────────────────────────
_scroll_timer = 0   # counts frames since last scroll tick

def do_page_up(frame):
    """
    Continuous slow scroll UP.
    Gesture: FIST with thumb pointing UP (👍 like button).
    Scroll fires every SCROLL_INTERVAL frames while gesture is held.
    """
    global _scroll_timer
    _scroll_timer += 1

    # Progress indicator — fills toward SCROLL_INTERVAL
    prog = (_scroll_timer % config.SCROLL_INTERVAL) / config.SCROLL_INTERVAL

    if _scroll_timer >= config.SCROLL_INTERVAL:
        pyautogui.scroll(config.SCROLL_AMOUNT)   # positive = scroll UP
        _scroll_timer = 0

    cv2.putText(frame, "PAGE UP  👍", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (100, 255, 100), 2)
    cv2.putText(frame, "Hold to keep scrolling UP", (10, 118),
                cv2.FONT_HERSHEY_PLAIN, 1.1, (100, 255, 100), 1)

    # Small animated arrow pointing up
    h, w = frame.shape[:2]
    arrow_x, arrow_y = w // 2, h // 2
    thickness = 3
    cv2.arrowedLine(frame,
                    (arrow_x, arrow_y + 30),
                    (arrow_x, arrow_y - 30),
                    (100, 255, 100), thickness, tipLength=0.4)

def do_page_down(frame):
    """
    Continuous slow scroll DOWN.
    Gesture: FIST with thumb pointing DOWN (👎 dislike button).
    Scroll fires every SCROLL_INTERVAL frames while gesture is held.
    """
    global _scroll_timer
    _scroll_timer += 1

    if _scroll_timer >= config.SCROLL_INTERVAL:
        pyautogui.scroll(-config.SCROLL_AMOUNT)  # negative = scroll DOWN
        _scroll_timer = 0

    cv2.putText(frame, "PAGE DOWN  👎", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (100, 100, 255), 2)
    cv2.putText(frame, "Hold to keep scrolling DOWN", (10, 118),
                cv2.FONT_HERSHEY_PLAIN, 1.1, (100, 100, 255), 1)

    # Small animated arrow pointing down
    h, w = frame.shape[:2]
    arrow_x, arrow_y = w // 2, h // 2
    cv2.arrowedLine(frame,
                    (arrow_x, arrow_y - 30),
                    (arrow_x, arrow_y + 30),
                    (100, 100, 255), 3, tipLength=0.4)

def reset_scroll():
    """Reset scroll timer — called when leaving page-scroll modes."""
    global _scroll_timer
    _scroll_timer = 0


# ── WINDOW SWITCHING  (platform-aware) ─────────────────────────────────────────
class WinSwitchState:
    def __init__(self):
        self.hold_count = 0
        self.fired      = False

_win_tab_state = WinSwitchState()

def do_win_tab(frame):
    """
    Open the window / task overview.
    Windows → Win + Tab
    macOS   → Ctrl + Up  (Mission Control)
    Linux   → Super + Tab  (may vary by desktop environment)
    """
    _win_tab_state.hold_count += 1
    prog  = min(_win_tab_state.hold_count / config.WIN_SWITCH_HOLD, 1.0)
    color = (int(255 * prog), 100, 255)

    cv2.putText(frame, "4 FINGERS OPEN", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, color, 2)

    if _win_tab_state.hold_count >= config.WIN_SWITCH_HOLD and not _win_tab_state.fired:
        if OS == 'win32':
            pyautogui.hotkey('win', 'tab')
        elif OS == 'darwin':
            pyautogui.hotkey('ctrl', 'up')       # Mission Control
        else:
            pyautogui.hotkey('super', 'tab')     # Linux (GNOME / KDE default)

        _win_tab_state.fired = True
        label = {'win32': 'WIN+TAB', 'darwin': 'MISSION CTRL'}.get(OS, 'SUPER+TAB')
        cv2.putText(frame, label + "!", (10, 118),
                    cv2.FONT_HERSHEY_PLAIN, 2, (200, 100, 255), 2)
    else:
        remaining = max(0, config.WIN_SWITCH_HOLD - _win_tab_state.hold_count)
        cv2.putText(frame, f"Hold {remaining} more frames...", (10, 118),
                    cv2.FONT_HERSHEY_PLAIN, 1.4, (180, 180, 180), 1)

def reset_win_switch():
    _win_tab_state.hold_count = 0
    _win_tab_state.fired      = False
