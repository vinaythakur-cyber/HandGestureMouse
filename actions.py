# =============================================================================
#  actions.py  —  CROSS-PLATFORM  (Windows + macOS + Linux)
# =============================================================================

import cv2
import sys
import os
import platform
import subprocess
import tempfile
import numpy as np
import pyautogui
import config

OS = platform.system()

# ── Volume backend ─────────────────────────────────────────────────────────────
VOLUME_ENABLED = False
VOL_MIN = 0
VOL_MAX = 100
_vol_obj = None

if OS == "Windows":
    try:
        # ── CRITICAL FIX for frozen .exe ──────────────────────────────────────
        # comtypes generates .py cache files at runtime.
        # In a frozen exe it tries to write them next to Niyanta.exe and FAILS.
        # Force it to use the system temp folder instead.
        import tempfile
        os.environ['COMTYPES_CACHE_DIR'] = tempfile.gettempdir()

        # comtypes must be explicitly initialised in a frozen exe
        import comtypes
        comtypes.CoInitialize()

        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        _devices   = AudioUtilities.GetSpeakers()
        _interface = _devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        _vol_obj   = cast(_interface, POINTER(IAudioEndpointVolume))
        VOL_MIN, VOL_MAX = _vol_obj.GetVolumeRange()[:2]
        VOLUME_ENABLED   = True
        print(f"[Niyanta] Volume OK  range={VOL_MIN:.1f} to {VOL_MAX:.1f} dB")

    except Exception as e:
        print(f"[Niyanta] Volume FAILED: {type(e).__name__}: {e}")

elif OS == "Darwin":
    try:
        subprocess.run(["osascript", "-e", "set volume output volume 50"],
                       capture_output=True, check=True)
        VOLUME_ENABLED = True
        VOL_MIN, VOL_MAX = 0, 100
        print("[Niyanta] Volume: macOS osascript ready")
    except Exception as e:
        print(f"[Niyanta] Volume FAILED: {e}")

else:
    try:
        subprocess.run(["amixer", "sset", "Master", "50%"],
                       capture_output=True, check=True)
        VOLUME_ENABLED = True
        VOL_MIN, VOL_MAX = 0, 100
        print("[Niyanta] Volume: Linux amixer ready")
    except Exception as e:
        print(f"[Niyanta] Volume FAILED: {e}")


def _set_volume_pct(pct):
    pct = max(0, min(100, int(pct)))
    if OS == "Windows" and _vol_obj is not None:
        db = np.interp(pct, [0, 100], [VOL_MIN, VOL_MAX])
        _vol_obj.SetMasterVolumeLevel(db, None)
    elif OS == "Darwin":
        subprocess.Popen(
            ["osascript", "-e", f"set volume output volume {pct}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(
            ["amixer", "sset", "Master", f"{pct}%"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── Brightness backend ─────────────────────────────────────────────────────────
BRIGHTNESS_ENABLED = False
try:
    import screen_brightness_control as sbc
    current = sbc.get_brightness()
    if current is not None:
        BRIGHTNESS_ENABLED = True
        print("[Niyanta] Brightness: ready")
except Exception as e:
    print(f"[Niyanta] Brightness unavailable: {e}")


# ── Cursor state ───────────────────────────────────────────────────────────────
class CursorState:
    def __init__(self):
        try:
            sw, sh = pyautogui.size()
        except Exception:
            sw, sh = 1920, 1080
        self.x = sw // 2
        self.y = sh // 2

cursor = CursorState()


def _smooth_move(raw_x, raw_y, frame_w, frame_h):
    sw, sh = pyautogui.size()
    target_x = np.interp(raw_x,
                         (config.MARGIN, frame_w - config.MARGIN), (0, sw))
    target_y = np.interp(raw_y,
                         (config.MARGIN, frame_h - config.MARGIN), (0, sh))
    cursor.x = int(cursor.x + (target_x - cursor.x) * config.SMOOTH)
    cursor.y = int(cursor.y + (target_y - cursor.y) * config.SMOOTH)
    pyautogui.moveTo(cursor.x, cursor.y)


# =============================================================================
#  MOVE
# =============================================================================
def do_move(hand_data, frame):
    ix, iy = hand_data.px(8)
    h, w   = frame.shape[:2]
    _smooth_move(ix, iy, w, h)
    cv2.putText(frame, "MOVE", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)


# =============================================================================
#  DRAG
# =============================================================================
_dragging = False

def do_drag(hand_data, frame):
    global _dragging
    tx, ty = hand_data.px(4);  ix, iy = hand_data.px(8)
    cx_d = (tx + ix) // 2;     cy_d = (ty + iy) // 2
    h, w = frame.shape[:2]
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


# =============================================================================
#  CLICKS
# =============================================================================
_left_count  = 0;  _left_fired  = False
_right_count = 0;  _right_fired = False

def do_left_click(hand_data, frame):
    global _left_count, _left_fired, _right_count, _right_fired
    _right_count = 0;  _right_fired = False
    tx, ty = hand_data.px(4);  ix, iy = hand_data.px(8)
    cx_l = (tx + ix) // 2;     cy_l = (ty + iy) // 2
    _left_count += 1
    prog = min(_left_count / config.HOLD_NEEDED, 1.0)
    cv2.line(frame,   (tx, ty), (ix, iy), (0, 255, 255), 3)
    cv2.circle(frame, (cx_l, cy_l), 18, (0, int(255*prog), 255), cv2.FILLED)
    if _left_count >= config.HOLD_NEEDED and not _left_fired:
        pyautogui.click()
        _left_fired = True
        cv2.putText(frame, "LEFT CLICKED!", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)
    else:
        cv2.putText(frame, f"L-Hold {_left_count}/{config.HOLD_NEEDED}",
                    (10, 90), cv2.FONT_HERSHEY_PLAIN, 2, (255, 200, 0), 2)

def do_right_click(hand_data, frame):
    global _right_count, _right_fired, _left_count, _left_fired
    _left_count = 0;  _left_fired = False
    tx, ty = hand_data.px(4);  mx, my = hand_data.px(12)
    cx_r = (tx + mx) // 2;     cy_r = (ty + my) // 2
    _right_count += 1
    prog = min(_right_count / config.HOLD_NEEDED, 1.0)
    cv2.line(frame,   (tx, ty), (mx, my), (0, 100, 255), 3)
    cv2.circle(frame, (cx_r, cy_r), 18, (0, int(255*prog), 180), cv2.FILLED)
    if _right_count >= config.HOLD_NEEDED and not _right_fired:
        pyautogui.rightClick()
        _right_fired = True
        cv2.putText(frame, "RIGHT CLICKED!", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 100, 255), 2)
    else:
        cv2.putText(frame, f"R-Hold {_right_count}/{config.HOLD_NEEDED}",
                    (10, 90), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 255), 2)

def reset_clicks():
    global _left_count, _left_fired, _right_count, _right_fired
    _left_count = 0;  _left_fired  = False
    _right_count = 0; _right_fired = False


# =============================================================================
#  VOLUME  —  dist(thumb=4, index=8), range [20,250] → 0-100%
# =============================================================================
_vol_bar = 400
_vol_pct = 0

def do_volume(hand_data, frame):
    global _vol_bar, _vol_pct
    if not VOLUME_ENABLED:
        cv2.putText(frame, "VOL: not available", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 100, 255), 2)
        return

    dist     = hand_data.dist(4, 8)
    _vol_pct = np.interp(dist, [20, 250], [0, 100])
    _vol_bar = np.interp(dist, [20, 250], [400, 150])
    _set_volume_pct(_vol_pct)

    tx, ty = hand_data.px(4);  ix, iy = hand_data.px(8)
    cv2.line(frame, (tx, ty), (ix, iy), (0, 200, 255), 3)
    cv2.circle(frame, (tx, ty), 10, (255, 100, 0), cv2.FILLED)
    cv2.circle(frame, (ix, iy), 10, (0,   0, 255), cv2.FILLED)
    cv2.putText(frame, "VOLUME", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 200, 255), 2)
    cv2.rectangle(frame, (50, 150), (82, 400), (0, 200, 255), 2)
    cv2.rectangle(frame, (50, int(_vol_bar)), (82, 400),
                  (0, 200, 255), cv2.FILLED)
    cv2.putText(frame, f'{int(_vol_pct)}%', (30, 430),
                cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 200, 255), 2)
    cv2.putText(frame, f'd={int(dist)}', (90, 430),
                cv2.FONT_HERSHEY_PLAIN, 1, (0, 150, 200), 1)


# =============================================================================
#  BRIGHTNESS  —  dist(thumb=4, pinky=20), range [30,300] → 0-100%
# =============================================================================
_bright_bar = 400
_bright_pct = 50

def do_brightness(hand_data, frame):
    global _bright_bar, _bright_pct
    if not BRIGHTNESS_ENABLED:
        cv2.putText(frame, "BRIGHT: not available", (10, 90),
                    cv2.FONT_HERSHEY_PLAIN, 1.5, (100, 100, 255), 2)
        return

    dist        = hand_data.dist(4, 20)
    _bright_pct = int(np.interp(dist, [30, 300], [0, 100]))
    _bright_bar = np.interp(dist, [30, 300], [400, 150])

    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(int(_bright_pct))
    except Exception:
        pass

    tx, ty  = hand_data.px(4);   px_, py = hand_data.px(20)
    cv2.line(frame, (tx, ty), (px_, py), (180, 100, 255), 3)
    cv2.circle(frame, (tx, ty),  10, (255, 100,   0), cv2.FILLED)
    cv2.circle(frame, (px_, py), 10, (200,   0, 200), cv2.FILLED)
    cv2.putText(frame, "BRIGHTNESS", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (180, 100, 255), 2)
    cv2.rectangle(frame, (100, 150), (132, 400), (180, 100, 255), 2)
    cv2.rectangle(frame, (100, int(_bright_bar)), (132, 400),
                  (180, 100, 255), cv2.FILLED)
    cv2.putText(frame, f'{int(_bright_pct)}%', (90, 430),
                cv2.FONT_HERSHEY_PLAIN, 1.5, (180, 100, 255), 2)
    cv2.putText(frame, f'd={int(dist)}', (140, 430),
                cv2.FONT_HERSHEY_PLAIN, 1, (140, 80, 200), 1)


# =============================================================================
#  PAGE UP / PAGE DOWN
# =============================================================================
class ScrollState:
    def __init__(self):
        self.cooldown = 0

_scroll = ScrollState()

def do_page_up(frame):
    _scroll.cooldown -= 1
    if _scroll.cooldown <= 0:
        pyautogui.press('pageup')
        _scroll.cooldown = config.SCROLL_DELAY
    cv2.putText(frame, "PAGE UP", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (100, 255, 100), 2)
    cv2.arrowedLine(frame, (200, 110), (200, 70),
                    (100, 255, 100), 3, tipLength=0.5)

def do_page_down(frame):
    _scroll.cooldown -= 1
    if _scroll.cooldown <= 0:
        pyautogui.press('pagedown')
        _scroll.cooldown = config.SCROLL_DELAY
    cv2.putText(frame, "PAGE DOWN", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (100, 100, 255), 2)
    cv2.arrowedLine(frame, (200, 70), (200, 110),
                    (100, 100, 255), 3, tipLength=0.5)

def reset_scroll():
    _scroll.cooldown = 0


# =============================================================================
#  WIN + TAB
# =============================================================================
class WinSwitchState:
    def __init__(self):
        self.hold_count = 0
        self.fired      = False

_win_tab_state = WinSwitchState()

def do_win_tab(frame):
    _win_tab_state.hold_count += 1
    prog  = min(_win_tab_state.hold_count / config.WIN_SWITCH_HOLD, 1.0)
    color = (int(255 * prog), 100, 255)
    cv2.putText(frame, "4 FINGERS OPEN", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, color, 2)
    remaining = max(0, config.WIN_SWITCH_HOLD - _win_tab_state.hold_count)
    if remaining > 0:
        cv2.putText(frame, f"Hold {remaining} more...", (10, 118),
                    cv2.FONT_HERSHEY_PLAIN, 1.4, (180, 180, 180), 1)
    if (_win_tab_state.hold_count >= config.WIN_SWITCH_HOLD
            and not _win_tab_state.fired):
        if OS == "Windows":
            pyautogui.hotkey("win", "tab")
        elif OS == "Darwin":
            pyautogui.hotkey("ctrl", "up")
        else:
            pyautogui.hotkey("super", "w")
        _win_tab_state.fired = True
        cv2.putText(frame, "TASK VIEW!", (10, 118),
                    cv2.FONT_HERSHEY_PLAIN, 2, (200, 100, 255), 2)

def reset_win_switch():
    _win_tab_state.hold_count = 0
    _win_tab_state.fired      = False
