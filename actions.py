import cv2, os, platform, subprocess, tempfile
import numpy as np
import pyautogui
import config

OS = platform.system()

# ── Volume ────────────────────────────────────────────────────────────────────
VOLUME_ENABLED = False
VOL_MIN = 0
VOL_MAX = 100
_vol_obj = None

if OS == "Windows":
    try:
        os.environ['COMTYPES_CACHE_DIR'] = tempfile.gettempdir()
        import comtypes
        comtypes.CoInitialize()
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        _dev = AudioUtilities.GetSpeakers()
        _iface = _dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        _vol_obj = cast(_iface, POINTER(IAudioEndpointVolume))
        VOL_MIN, VOL_MAX = _vol_obj.GetVolumeRange()[:2]
        VOLUME_ENABLED = True
        print(f"[Niyanta] Volume OK {VOL_MIN:.0f} to {VOL_MAX:.0f} dB")
    except Exception as e:
        print(f"[Niyanta] Volume FAILED: {e}")

elif OS == "Darwin":
    try:
        subprocess.run(["osascript", "-e", "set volume output volume 50"],
                       capture_output=True, check=True)
        VOLUME_ENABLED = True
        VOL_MIN, VOL_MAX = 0, 100
        print("[Niyanta] Volume OK (macOS)")
    except Exception as e:
        print(f"[Niyanta] Volume FAILED: {e}")

else:
    try:
        subprocess.run(["amixer", "sset", "Master", "50%"],
                       capture_output=True, check=True)
        VOLUME_ENABLED = True
        VOL_MIN, VOL_MAX = 0, 100
        print("[Niyanta] Volume OK (Linux)")
    except Exception as e:
        print(f"[Niyanta] Volume FAILED: {e}")


def _set_vol(pct):
    pct = max(0, min(100, int(pct)))
    if OS == "Windows" and _vol_obj:
        _vol_obj.SetMasterVolumeLevel(
            np.interp(pct, [0, 100], [VOL_MIN, VOL_MAX]), None)
    elif OS == "Darwin":
        subprocess.Popen(["osascript", "-e", f"set volume output volume {pct}"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["amixer", "sset", "Master", f"{pct}%"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── Brightness ────────────────────────────────────────────────────────────────
BRIGHTNESS_ENABLED = False
try:
    import screen_brightness_control as sbc
    if sbc.get_brightness() is not None:
        BRIGHTNESS_ENABLED = True
        print("[Niyanta] Brightness OK")
except Exception as e:
    print(f"[Niyanta] Brightness FAILED: {e}")


# ── Cursor ────────────────────────────────────────────────────────────────────
class _Cur:
    def __init__(self):
        try:   sw, sh = pyautogui.size()
        except: sw, sh = 1920, 1080
        self.x, self.y = sw // 2, sh // 2

cursor = _Cur()

def _move(rx, ry, fw, fh):
    sw, sh = pyautogui.size()
    tx = np.interp(rx, (config.MARGIN, fw - config.MARGIN), (0, sw))
    ty = np.interp(ry, (config.MARGIN, fh - config.MARGIN), (0, sh))
    cursor.x = int(cursor.x + (tx - cursor.x) * config.SMOOTH)
    cursor.y = int(cursor.y + (ty - cursor.y) * config.SMOOTH)
    pyautogui.moveTo(cursor.x, cursor.y)


# ── Move ──────────────────────────────────────────────────────────────────────
def do_move(hd, frame):
    ix, iy = hd.px(8)
    h, w   = frame.shape[:2]
    _move(ix, iy, w, h)
    cv2.putText(frame, "MOVE", (10, 90),
                cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)


# ── Drag ──────────────────────────────────────────────────────────────────────
_drag = False

def do_drag(hd, frame):
    global _drag
    tx, ty = hd.px(4);  ix, iy = hd.px(8)
    cx, cy = (tx+ix)//2, (ty+iy)//2
    h, w   = frame.shape[:2]
    if not _drag:
        pyautogui.mouseDown()
        _drag = True
    _move(cx, cy, w, h)
    cv2.line(frame, (tx,ty),(ix,iy),(0,200,200),3)
    cv2.circle(frame,(cx,cy),20,(0,200,200),cv2.FILLED)
    cv2.putText(frame,"DRAGGING",(10,90),cv2.FONT_HERSHEY_PLAIN,2,(0,200,200),2)

def release_drag():
    global _drag
    if _drag:
        pyautogui.mouseUp()
        _drag = False

def is_dragging(): return _drag


# ── Clicks ────────────────────────────────────────────────────────────────────
_lc = 0; _lf = False
_rc = 0; _rf = False

def do_left_click(hd, frame):
    global _lc, _lf, _rc, _rf
    _rc = 0; _rf = False
    tx,ty = hd.px(4); ix,iy = hd.px(8)
    cx,cy = (tx+ix)//2,(ty+iy)//2
    _lc += 1
    p = min(_lc/config.HOLD_NEEDED, 1.0)
    cv2.line(frame,(tx,ty),(ix,iy),(0,255,255),3)
    cv2.circle(frame,(cx,cy),18,(0,int(255*p),255),cv2.FILLED)
    if _lc >= config.HOLD_NEEDED and not _lf:
        pyautogui.click(); _lf = True
        cv2.putText(frame,"CLICKED!",(10,90),cv2.FONT_HERSHEY_PLAIN,2,(0,255,255),2)
    else:
        cv2.putText(frame,f"Hold {_lc}/{config.HOLD_NEEDED}",(10,90),
                    cv2.FONT_HERSHEY_PLAIN,2,(255,200,0),2)

def do_right_click(hd, frame):
    global _rc, _rf, _lc, _lf
    _lc = 0; _lf = False
    tx,ty = hd.px(4); mx,my = hd.px(12)
    cx,cy = (tx+mx)//2,(ty+my)//2
    _rc += 1
    p = min(_rc/config.HOLD_NEEDED, 1.0)
    cv2.line(frame,(tx,ty),(mx,my),(0,100,255),3)
    cv2.circle(frame,(cx,cy),18,(0,int(255*p),180),cv2.FILLED)
    if _rc >= config.HOLD_NEEDED and not _rf:
        pyautogui.rightClick(); _rf = True
        cv2.putText(frame,"R-CLICKED!",(10,90),cv2.FONT_HERSHEY_PLAIN,2,(0,100,255),2)
    else:
        cv2.putText(frame,f"R-Hold {_rc}/{config.HOLD_NEEDED}",(10,90),
                    cv2.FONT_HERSHEY_PLAIN,2,(100,200,255),2)

def reset_clicks():
    global _lc,_lf,_rc,_rf
    _lc=0;_lf=False;_rc=0;_rf=False


# ── Volume ────────────────────────────────────────────────────────────────────
_vbar = 400; _vpct = 0

def do_volume(hd, frame):
    global _vbar, _vpct
    if not VOLUME_ENABLED:
        cv2.putText(frame,"VOL: not available",(10,90),
                    cv2.FONT_HERSHEY_PLAIN,1.5,(0,100,255),2)
        return
    d = hd.dist(4, 8)
    _vpct = np.interp(d, [20, 250], [0, 100])
    _vbar = np.interp(d, [20, 250], [400, 150])
    _set_vol(_vpct)
    tx,ty = hd.px(4); ix,iy = hd.px(8)
    cv2.line(frame,(tx,ty),(ix,iy),(0,200,255),3)
    cv2.circle(frame,(tx,ty),10,(255,100,0),cv2.FILLED)
    cv2.circle(frame,(ix,iy),10,(0,0,255),cv2.FILLED)
    cv2.putText(frame,"VOLUME",(10,90),cv2.FONT_HERSHEY_PLAIN,2,(0,200,255),2)
    cv2.rectangle(frame,(50,150),(82,400),(0,200,255),2)
    cv2.rectangle(frame,(50,int(_vbar)),(82,400),(0,200,255),cv2.FILLED)
    cv2.putText(frame,f'{int(_vpct)}%',(30,430),cv2.FONT_HERSHEY_PLAIN,1.5,(0,200,255),2)
    cv2.putText(frame,f'd={int(d)}',(90,430),cv2.FONT_HERSHEY_PLAIN,1,(0,150,200),1)


# ── Brightness ────────────────────────────────────────────────────────────────
_bbar = 400; _bpct = 50

def do_brightness(hd, frame):
    global _bbar, _bpct
    if not BRIGHTNESS_ENABLED:
        cv2.putText(frame,"BRIGHT: not available",(10,90),
                    cv2.FONT_HERSHEY_PLAIN,1.5,(100,100,255),2)
        return
    d = hd.dist(4, 20)
    _bpct = int(np.interp(d, [30, 300], [0, 100]))
    _bbar = np.interp(d, [30, 300], [400, 150])
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(int(_bpct))
    except: pass
    tx,ty = hd.px(4); px,py = hd.px(20)
    cv2.line(frame,(tx,ty),(px,py),(180,100,255),3)
    cv2.circle(frame,(tx,ty),10,(255,100,0),cv2.FILLED)
    cv2.circle(frame,(px,py),10,(200,0,200),cv2.FILLED)
    cv2.putText(frame,"BRIGHTNESS",(10,90),cv2.FONT_HERSHEY_PLAIN,2,(180,100,255),2)
    cv2.rectangle(frame,(100,150),(132,400),(180,100,255),2)
    cv2.rectangle(frame,(100,int(_bbar)),(132,400),(180,100,255),cv2.FILLED)
    cv2.putText(frame,f'{int(_bpct)}%',(90,430),cv2.FONT_HERSHEY_PLAIN,1.5,(180,100,255),2)
    cv2.putText(frame,f'd={int(d)}',(140,430),cv2.FONT_HERSHEY_PLAIN,1,(140,80,200),1)


# ── Scroll ────────────────────────────────────────────────────────────────────
_scd = 0

def do_page_up(frame):
    global _scd
    _scd -= 1
    if _scd <= 0:
        pyautogui.press('pageup')
        _scd = config.SCROLL_DELAY
    cv2.putText(frame,"PAGE UP",(10,90),cv2.FONT_HERSHEY_PLAIN,2,(100,255,100),2)
    cv2.arrowedLine(frame,(200,110),(200,70),(100,255,100),3,tipLength=0.5)

def do_page_down(frame):
    global _scd
    _scd -= 1
    if _scd <= 0:
        pyautogui.press('pagedown')
        _scd = config.SCROLL_DELAY
    cv2.putText(frame,"PAGE DOWN",(10,90),cv2.FONT_HERSHEY_PLAIN,2,(100,100,255),2)
    cv2.arrowedLine(frame,(200,70),(200,110),(100,100,255),3,tipLength=0.5)

def reset_scroll():
    global _scd
    _scd = 0


# ── Win Tab ───────────────────────────────────────────────────────────────────
_wh = 0; _wf = False

def do_win_tab(frame):
    global _wh, _wf
    _wh += 1
    p = min(_wh/config.WIN_SWITCH_HOLD, 1.0)
    cv2.putText(frame,"4 FINGERS",(10,90),cv2.FONT_HERSHEY_PLAIN,2,
                (int(255*p),100,255),2)
    r = max(0, config.WIN_SWITCH_HOLD - _wh)
    if r > 0:
        cv2.putText(frame,f"Hold {r} more",(10,118),
                    cv2.FONT_HERSHEY_PLAIN,1.4,(180,180,180),1)
    if _wh >= config.WIN_SWITCH_HOLD and not _wf:
        if OS == "Windows":     pyautogui.hotkey("win","tab")
        elif OS == "Darwin":    pyautogui.hotkey("ctrl","up")
        else:                   pyautogui.hotkey("super","w")
        _wf = True
        cv2.putText(frame,"TASK VIEW!",(10,118),
                    cv2.FONT_HERSHEY_PLAIN,2,(200,100,255),2)

def reset_win_switch():
    global _wh, _wf
    _wh = 0; _wf = False
