# =============================================================================
#  config.py
#  ─────────────────────────────────────────────────────────────────────────────
#  ALL tunable settings live here.
#  If something feels wrong (cursor too fast, click too sensitive, etc.)
#  just change the value here — you never need to touch any other file.
# =============================================================================

import os
import sys

# ── MediaPipe model path (auto-detects .exe vs normal Python) ─────────────────
if getattr(sys, 'frozen', False):          # running as PyInstaller .exe
    BASE_DIR = sys._MEIPASS
else:                                       # running as normal .py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "hand_landmarker.task")

# ── Camera ────────────────────────────────────────────────────────────────────
CAMERA_INDEX  = 0      # 0 = default webcam, try 1 if it doesn't open
FRAME_WIDTH   = 640
FRAME_HEIGHT  = 480
CAMERA_FPS    = 30

# ── Cursor movement ───────────────────────────────────────────────────────────
# MARGIN : pixels from edge of camera frame to ignore.
#          Bigger = smaller active zone = less hand movement needed.
MARGIN        = 150

# SMOOTH : how quickly cursor follows finger. 0.1 = slow, 1.0 = instant.
SMOOTH        = 0.7

# ── Click & Drag ──────────────────────────────────────────────────────────────
# HOLD_NEEDED : consecutive frames pinch must be held before click fires.
HOLD_NEEDED   = 4

# Pinch distance thresholds (pixels on the camera frame)
PINCH_TIGHT   = 35    # below = pinch "closed"  (click / drag trigger)
PINCH_OPEN    = 65    # above = pinch "open"    (move trigger)

# ── Window switching ──────────────────────────────────────────────────────────
# Frames open-palm must be held before window-switch fires.
WIN_SWITCH_HOLD = 8

# ── Volume ────────────────────────────────────────────────────────────────────
VOL_PINCH_MAX = 180   # max pinch distance that counts as volume mode

# ── Brightness (dinosaur / spread hand gesture) ───────────────────────────────
# Average distance from thumb tip to the 4 finger tips.
# When hand is fully open and spread → high distance → high brightness.
# When fingers close toward thumb  → low  distance → low  brightness.
BRIGHT_MIN_DIST = 30    # px — fingers fully closed toward thumb = 0 % brightness
BRIGHT_MAX_DIST = 250   # px — fingers fully spread from thumb   = 100 % brightness

# ── Page scroll (page-up / page-down thumb gestures) ─────────────────────────
# How many frames to wait between each scroll tick.
# Higher = slower scrolling.  Lower = faster scrolling.
SCROLL_INTERVAL = 2     # scroll fires once every 6 frames  (~5 ticks/sec at 30fps)
SCROLL_AMOUNT   = 8     # pyautogui scroll units per tick

# ── Thumb direction thresholds for fist gestures ──────────────────────────────
# Thumb is "UP"   when thumb tip y  <  wrist y  −  THUMB_DIR_THRESH
# Thumb is "DOWN" when thumb tip y  >  wrist y  +  THUMB_DIR_THRESH
# Increase if false triggers happen; decrease if gesture isn't detected.
THUMB_DIR_THRESH = 30   # pixels

# ── MediaPipe detection confidence ───────────────────────────────────────────
DETECT_CONF   = 0.6
TRACK_CONF    = 0.6
