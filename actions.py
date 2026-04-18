# =============================================================================
#  actions.py  —  CROSS-PLATFORM VERSION
#  Works on Windows, macOS, Linux.
#  Volume  : pycaw (Win) | osascript (macOS) | amixer (Linux)
#  Hotkeys : platform-branched Alt+Tab / Win+Tab equivalents
#  Cursor  : pyautogui on all platforms
# =============================================================================

import cv2
import platform
import subprocess
import numpy as np
import pyautogui
import config

OS = platform.system()   # 'Windows' | 'Darwin' | 'Linux'

# ── Volume backend — chosen once at import time ───────────────────────────────
VOLUME_ENABLED = False
VOL_MIN = 0
VOL_MAX = 100
_vol_obj = None          # pycaw object, Windows only

if OS == "Windows":
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        _devices   = AudioUtilities.GetSpeakers()
        _interface = _devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        _vol_obj   = cast(_interface, POINTER(IAudioEndpointVolume))
        VOL_MIN, VOL_MAX = _vol_obj.GetVolumeRange()[:2]
        VOLUME_ENABLED   = True
        print("[actions] Volume: pycaw (Windows)")
    except Exception as e:
        print(f"[actions] Volume: pycaw unavailable ({e})")

elif OS == "Darwin":
    # macOS — use AppleScript via osascript
    try:
        subprocess.run(["osascript", "-e", "set volume output volume 50"],
                       capture_output=True, check=True)
        VOLUME_ENABLED = True
        VOL_MIN, VOL_MAX = 0, 100
        print("[actions] Volume: osascript (macOS)")
    except Exception as e:
        print(f"[actions] Volume: osascript unavailable ({e})")

else:
    # Linux — use amixer
    try:
        subprocess.run(["amixer", "sset", "Master", "50%"],
                       capture_output=True, check=True)
        VOLUME_ENABLED = True
        VOL_MIN, VOL_MAX = 0, 100
        print("[actions] Volume: amixer (Linux)")
    except Exception as e:
        print(f"[actions] Volume: amixer unavailable ({e})")


def _set_volume(pct):
    """Set system volume to pct (0-100). Called by do_volume()."""
    pct = max(0, min(100, int(pct)))

    if OS == "Windows" and _vol_obj is not None:
        db = np.interp(pct, [0, 100], [VOL_MIN, VOL_MAX])
        _vol_obj.SetMasterVolumeLevel(db, None)

    elif OS == "Darwin":
        subprocess.Popen(["osascript", "-e",
                          f"set volume output volume {pct}"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    else:   # Linux
        subprocess.Popen(["amixer", "sset", "Master", f"{pct}%"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── Brightness backend ────────────────────────────────────────────────────────
BRIGHTNESS_ENABLED = False
try:
    import screen_brightness_control as sbc
    sbc.get_brightness()     # test call — raises if no monitor API
    BRIGHTNESS_ENABLED = True
    print("[actions] Brightness: screen-brightness-control")
except Exception as e:
    print(f"[actions] Brightness: unavailable ({e})")


# =============================================================================
#  CURSOR STATE  (shared between move and drag)
# =============================================================================
class CursorState:
    def __init__(self):
        try:
            sw, sh = pyautogui.size()
        except Exception:
            sw, sh = 1920, 1080    # safe fallback if display not ready
        self.x = sw // 2
        self.y = sh // 2

cursor = CursorState()


def _smooth_move(raw_x, raw_y, frame_w, frame_h):
    sw, sh = pyautogui.size()
    target_x = np.interp(raw_x, (config.MARGIN, frame_w - config.MARGIN), (0, sw))
    target_y = np.interp(raw_y, (config.MARGIN, frame_h - config.MARGIN), (0, sh))
    cursor.x = int(cursor.x + (target_x - cursor.x) * config.SMOOTH)
    cursor.y = int(cursor.y + (target_y - cursor.y) * config.SMOOTH)
    pyautogui.moveTo(cursor.x, cursor.y)


# =============================================================================
#  ACTION FUNCTIONS
# =============================================================================

def do_move(hand_data, frame):
    ix, iy = hand_data.px(8)
    h, w   = frame.shape[:2]
    _smooth_move(ix, iy, w, h)
    cv2.putText(frame, "MOVE", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)


# ── Drag ──────────────────────────────────────────────────────────────────────
_dragging = False

def do_drag(hand_data, frame):
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
    cv2.putText(frame, "DRAGGING...", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 200, 200), 2)

def release_drag():
    global _dragging
    if _dragging:
        pyautogui.mouseUp()
        _dragging = False

def is_dragging():
    return _dragging


# ── Clicks ────────────────────────────────────────────────────────────────────
_left_count  = 0;  _left_fired  = False
_right_count = 0;  _right_fired = False

def do_left_click(hand_data, frame):
    global _left_count, _left_fired, _right_count, _right_fired
    _right_count = 0;  _right_fired = False
    tx, ty = hand_data.px(4);  ix, iy = hand_data.px(8)
    cx_l = (tx + ix) // 2;    cy_l = (ty + iy) // 2
    _left_count += 1
    prog  = min(_left_count / config.HOLD_NEEDED, 1.0)
    color = (0, int(255 * prog), 255)
    cv2.line(frame,   (tx, ty), (ix, iy), (0, 255, 255), 3)
    cv2.circle(frame, (cx_l, cy_l), 18, color, cv2.FILLED)
    if _left_count >= config.HOLD_NEEDED and not _left_fired:
        pyautogui.click()
        _left_fired = True
        cv2.putText(frame, "LEFT CLICKED!", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)
    else:
        cv2.putText(frame, f"L-Hold... {_left_count}/{config.HOLD_NEEDED}", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 2, (255, 200, 0), 2)

def do_right_click(hand_data, frame):
    global _right_count, _right_fired, _left_count, _left_fired
    _left_count = 0;  _left_fired = False
    tx, ty = hand_data.px(4);  mx, my = hand_data.px(12)
    cx_r = (tx + mx) // 2;    cy_r = (ty + my) // 2
    _right_count += 1
    prog  = min(_right_count / config.HOLD_NEEDED, 1.0)
    color = (0, int(255 * prog), 180)
    cv2.line(frame,   (tx, ty), (mx, my), (0, 100, 255), 3)
    cv2.circle(frame, (cx_r, cy_r), 18, color, cv2.FILLED)
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
    _left_count = 0;  _left_fired  = False
    _right_count = 0; _right_fired = False


# ── Volume ────────────────────────────────────────────────────────────────────
_vol_bar = 400
_vol_pct = 0

def do_volume(hand_data, frame):
    global _vol_bar, _vol_pct
    if not VOLUME_ENABLED:
        cv2.putText(frame, "VOL: not available", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 100, 255), 2)
        return
    dist     = hand_data.dist(4, 8)
    _vol_pct = np.interp(dist, [20, 200], [0, 100])
    _vol_bar = np.interp(dist, [20, 200], [400, 150])
    _set_volume(_vol_pct)
    cv2.putText(frame, "VOL MODE", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 200, 255), 2)
    cv2.rectangle(frame, (50, 150), (82, 400), (0, 200, 255), 2)
    cv2.rectangle(frame, (50, int(_vol_bar)), (82, 400), (0, 200, 255), cv2.FILLED)
    cv2.putText(frame, f'{int(_vol_pct)}%', (30, 430),
                cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 200, 255), 2)


# ── Brightness (NEW — cross-platform) ─────────────────────────────────────────
_bright_bar = 400
_bright_pct = 50

def do_brightness(hand_data, frame):
    global _bright_bar, _bright_pct
    if not BRIGHTNESS_ENABLED:
        cv2.putText(frame, "BRIGHT: not available", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 1.5, (100, 100, 255), 2)
        return
    dist        = hand_data.dist(4, 8)
    _bright_pct = int(np.interp(dist, [20, 220], [0, 100]))
    _bright_bar = np.interp(dist, [20, 220], [400, 150])
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(_bright_pct)
    except Exception:
        pass
    cv2.putText(frame, "BRIGHTNESS", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (180, 100, 255), 2)
    cv2.rectangle(frame, (100, 150), (132, 400), (180, 100, 255), 2)
    cv2.rectangle(frame, (100, int(_bright_bar)), (132, 400),
                  (180, 100, 255), cv2.FILLED)
    cv2.putText(frame, f'{int(_bright_pct)}%', (90, 430),
                cv2.FONT_HERSHEY_PLAIN, 1.5, (180, 100, 255), 2)


# ── Swipe ─────────────────────────────────────────────────────────────────────
class SwipeState:
    def __init__(self):
        self.history     = []
        self.cooldown    = 0
        self.label       = ""
        self.label_timer = 0

_swipe = SwipeState()

def do_swipe(hand_data, frame):
    ix, _ = hand_data.px(8)
    _swipe.history.append(ix)
    if len(_swipe.history) > config.SWIPE_WINDOW:
        _swipe.history.pop(0)
    cv2.putText(frame, "SWIPE MODE", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (200, 100, 255), 2)
    if len(_swipe.history) == config.SWIPE_WINDOW and _swipe.cooldown == 0:
        delta = _swipe.history[-1] - _swipe.history[0]
        speed = abs(delta) / config.SWIPE_WINDOW
        if speed > config.SWIPE_SPEED and abs(delta) > config.SWIPE_THRESH:
            if delta > 0:
                pyautogui.press('tab')
                _swipe.label = ">> NEXT FILE"
            else:
                pyautogui.hotkey('shift', 'tab')
                _swipe.label = "<< PREV FILE"
            _swipe.label_timer = config.SWIPE_LABEL_FRAMES
            _swipe.history.clear()
            _swipe.cooldown = config.SWIPE_COOLDOWN

def tick_swipe():
    if _swipe.cooldown    > 0: _swipe.cooldown    -= 1
    if _swipe.label_timer > 0: _swipe.label_timer -= 1
    else: _swipe.label = ""

def draw_swipe_label(frame):
    if _swipe.label:
        color = (0, 200, 255) if ">>" in _swipe.label else (255, 150, 0)
        cv2.putText(frame, _swipe.label, (10, 205),
                    cv2.FONT_HERSHEY_PLAIN, 2.2, color, 2)

def reset_swipe():
    _swipe.history.clear()


# ── Window switching — PLATFORM AWARE ─────────────────────────────────────────
class WinSwitchState:
    def __init__(self):
        self.hold_count = 0
        self.fired      = False

_alt_tab_state = WinSwitchState()
_win_tab_state = WinSwitchState()

def do_alt_tab(frame):
    _alt_tab_state.hold_count += 1
    _win_tab_state.hold_count  = 0
    _win_tab_state.fired       = False
    prog  = min(_alt_tab_state.hold_count / config.WIN_SWITCH_HOLD, 1.0)
    color = (0, int(255 * prog), 200)
    cv2.putText(frame, "OPEN PALM", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, color, 2)
    if _alt_tab_state.hold_count >= config.WIN_SWITCH_HOLD and not _alt_tab_state.fired:
        # Platform-correct window switcher
        if OS == "Darwin":
            pyautogui.hotkey("command", "tab")    # macOS app switcher
        else:
            pyautogui.hotkey("alt", "tab")        # Windows + Linux
        _alt_tab_state.fired = True
        cv2.putText(frame, "SWITCH WINDOW!", (10, 118),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 200), 2)

def do_win_tab(frame):
    _win_tab_state.hold_count += 1
    _alt_tab_state.hold_count  = 0
    _alt_tab_state.fired       = False
    prog  = min(_win_tab_state.hold_count / config.WIN_SWITCH_HOLD, 1.0)
    color = (int(255 * prog), 100, 255)
    cv2.putText(frame, "4 FINGERS OPEN", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, color, 2)
    if _win_tab_state.hold_count >= config.WIN_SWITCH_HOLD and not _win_tab_state.fired:
        # Platform-correct task view / mission control
        if OS == "Windows":
            pyautogui.hotkey("win", "tab")        # Task View
        elif OS == "Darwin":
            pyautogui.hotkey("ctrl", "up")        # Mission Control
        else:
            pyautogui.hotkey("super", "w")        # GNOME Activities (or similar)
        _win_tab_state.fired = True
        cv2.putText(frame, "TASK VIEW!", (10, 118),
                    cv2.FONT_HERSHEY_PLAIN, 2, (200, 100, 255), 2)

def reset_win_switch():
    _alt_tab_state.hold_count = 0;  _alt_tab_state.fired = False
    _win_tab_state.hold_count = 0;  _win_tab_state.fired = False
