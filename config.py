# =============================================================================
#  config.py  —  ALL tunable settings in one place
# =============================================================================

import os
import sys

# ── Model path (works both as .py and as PyInstaller .exe) ───────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "hand_landmarker.task")

# ── Camera ────────────────────────────────────────────────────────────────────
CAMERA_INDEX  = 0
FRAME_WIDTH   = 640
FRAME_HEIGHT  = 480
CAMERA_FPS    = 30

# ── Cursor ────────────────────────────────────────────────────────────────────
MARGIN        = 150    # px border inside frame — smaller = less hand movement needed
SMOOTH        = 0.7    # 0.1 = very slow, 1.0 = instant (no smoothing)

# ── Click & Drag ──────────────────────────────────────────────────────────────
HOLD_NEEDED   = 4      # frames pinch must be held before click fires
PINCH_TIGHT   = 35     # px — below this = pinch closed (click/drag)
PINCH_OPEN    = 65     # px — above this = pinch open   (move mode)

# ── Scroll (Page Up / Page Down) ─────────────────────────────────────────────
# How many frames to wait between scroll keypresses when gesture is held.
# Lower = faster scrolling. 8 = comfortable at 25-30 FPS.
SCROLL_DELAY  = 8

# ── Thumb direction (for 👍 / 👎 fist gestures) ───────────────────────────────
# Pixel distance thumb tip must be ABOVE or BELOW wrist to count as up/down.
# Increase if accidental triggers happen. Decrease if gesture is hard to detect.
THUMB_DIR_THRESH = 40  # pixels

# ── Volume ────────────────────────────────────────────────────────────────────
VOL_PINCH_MAX = 180    # max pinch distance that still counts as volume gesture

# ── Window switching ──────────────────────────────────────────────────────────
WIN_SWITCH_HOLD = 8    # frames open palm must be held before hotkey fires

# ── Swipe (kept for compatibility — not in main gesture set currently) ────────
SWIPE_WINDOW      = 10
SWIPE_THRESH      = 80
SWIPE_SPEED       = 8
SWIPE_COOLDOWN    = 20
SWIPE_LABEL_FRAMES= 30

# ── MediaPipe confidence ─────────────────────────────────────────────────────
DETECT_CONF   = 0.6
TRACK_CONF    = 0.6
