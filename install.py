"""
install.py
----------
Run this ONCE before running main.py.
Detects your OS and installs the correct packages automatically.

    python install.py

That's it. No manual pip installs needed.
"""

import sys
import subprocess
import platform
import os

OS = platform.system()   # 'Windows', 'Darwin' (macOS), 'Linux'

print("=" * 55)
print(f"  Hand Gesture Mouse — installer")
print(f"  Detected OS: {OS}")
print(f"  Python:      {sys.version.split()[0]}")
print("=" * 55)

def pip(*packages):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *packages])

# ── Packages that work on ALL platforms ───────────────────────────────────────
print("\n[1/3] Installing common packages (all platforms)...")
pip(
    "opencv-python",
    "mediapipe",
    "numpy",
    "pyautogui",
    "screen-brightness-control",  # cross-platform brightness
    "Pillow",                      # pyautogui dependency
)

# ── Windows-only packages ─────────────────────────────────────────────────────
if OS == "Windows":
    print("\n[2/3] Installing Windows-only packages...")
    pip("pycaw", "comtypes")
    print("      pycaw  installed — system volume control enabled")
    print("      comtypes installed — Windows COM interface enabled")

# ── macOS extras ─────────────────────────────────────────────────────────────
elif OS == "Darwin":
    print("\n[2/3] macOS detected — skipping pycaw (using osascript for volume)")
    print("      NOTE: You must grant Accessibility permission to Terminal/Python")
    print("      System Settings → Privacy & Security → Accessibility → add Terminal")

# ── Linux extras ─────────────────────────────────────────────────────────────
elif OS == "Linux":
    print("\n[2/3] Linux detected — checking system dependencies...")

    # Check for X11 display (needed by pyautogui)
    display = os.environ.get("DISPLAY", "")
    if not display:
        print("  WARNING: $DISPLAY not set.")
        print("  If you are on Wayland run:  export DISPLAY=:0")
        print("  If you are in a TTY, pyautogui mouse control will not work.")

    # Check amixer for volume
    result = subprocess.run(["which", "amixer"], capture_output=True)
    if result.returncode == 0:
        print("  amixer found — system volume control enabled")
    else:
        print("  amixer not found. Install with:")
        print("    sudo apt install alsa-utils   (Ubuntu/Debian)")
        print("    sudo dnf install alsa-utils   (Fedora)")

    # Check brightnessctl for brightness
    result = subprocess.run(["which", "brightnessctl"], capture_output=True)
    if result.returncode != 0:
        print("  brightnessctl not found. Install with:")
        print("    sudo apt install brightnessctl   (Ubuntu/Debian)")

# ── Final check ───────────────────────────────────────────────────────────────
print("\n[3/3] Verifying critical imports...")
errors = []

try:
    import cv2
    print(f"  cv2         OK  (version {cv2.__version__})")
except ImportError:
    errors.append("opencv-python")

try:
    import mediapipe
    print(f"  mediapipe   OK  (version {mediapipe.__version__})")
except ImportError:
    errors.append("mediapipe")

try:
    import pyautogui
    print(f"  pyautogui   OK  (version {pyautogui.__version__})")
except ImportError:
    errors.append("pyautogui")

try:
    import screen_brightness_control as sbc
    print(f"  brightness  OK")
except ImportError:
    print(f"  brightness  WARN — screen-brightness-control not available")

if OS == "Windows":
    try:
        from pycaw.pycaw import AudioUtilities
        print(f"  pycaw       OK  — volume control enabled")
    except ImportError:
        print(f"  pycaw       WARN — volume control disabled")

# Check model file
if os.path.exists("hand_landmarker.task"):
    print(f"  model file  OK  — hand_landmarker.task found")
else:
    print(f"  model file  MISSING — hand_landmarker.task not found!")
    print(f"  Download from:")
    print(f"  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task")
    errors.append("hand_landmarker.task")

print("\n" + "=" * 55)
if errors:
    print(f"  ISSUES FOUND: {', '.join(errors)}")
    print("  Fix the above then run:  python main.py")
else:
    print("  All checks passed!")
    print("  Run the app with:  python main.py")
print("=" * 55)
