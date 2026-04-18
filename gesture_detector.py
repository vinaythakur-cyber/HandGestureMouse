# =============================================================================
#  gesture_detector.py
#  ─────────────────────────────────────────────────────────────────────────────
#  Reads finger states + pinch distances from HandData and decides
#  WHICH gesture the user is making right now.
#
#  Returns a simple string so main.py can ask:
#      gesture = gesture_detector.detect(hand_data)
#      if gesture == "DRAG": ...
#
#  ┌─────────────────┬─────────────────────────────────────────────────────┐
#  │ Priority        │ Gesture         → Trigger Condition                 │
#  ├─────────────────┼─────────────────────────────────────────────────────┤
#  │  1 (highest)    │ VOLUME          → pinch + middle UP                 │
#  │  2              │ RIGHT_CLICK     → thumb+middle tight, others DOWN   │
#  │  3              │ WIN_TAB         → 4 fingers UP, thumb DOWN/folded   │
#  │  4              │ BRIGHTNESS      → all 5 open (spread = brighter)    │
#  │  5              │ PAGE_UP         → fist + thumb pointing UP  👍      │
#  │  6              │ PAGE_DOWN       → fist + thumb pointing DOWN 👎     │
#  │  7              │ MOVE            → index UP + open pinch             │
#  │  8              │ DRAG            → tight pinch + ring UP             │
#  │  9              │ LEFT_CLICK      → tight pinch + ring DOWN           │
#  │ 10 (lowest)     │ NEUTRAL         → nothing matched                   │
#  └─────────────────┴─────────────────────────────────────────────────────┘
# =============================================================================

import config

# ── Gesture name constants ─────────────────────────────────────────────────────
VOLUME      = "VOLUME"
RIGHT_CLICK = "RIGHT_CLICK"
WIN_TAB     = "WIN_TAB"
BRIGHTNESS  = "BRIGHTNESS"
PAGE_UP     = "PAGE_UP"
PAGE_DOWN   = "PAGE_DOWN"
MOVE        = "MOVE"
DRAG        = "DRAG"
LEFT_CLICK  = "LEFT_CLICK"
NEUTRAL     = "NEUTRAL"


def detect(hand_data):
    fingers = hand_data.fingers_up()
    thumb, index, middle, ring, pinky = fingers

    idx_pinch = hand_data.dist(4, 8)    # thumb ↔ index
    mid_pinch = hand_data.dist(4, 12)   # thumb ↔ middle
    tb_pinky  = hand_data.dist(4, 20)   # thumb ↔ pinky  ← NEW

    is_fist = (not index and not middle and not ring and not pinky)
    t_dir   = hand_data.thumb_direction() if is_fist else 'neutral'

    # ── 1. WIN + TAB — all 5 fingers open ──────────────────
    # MUST be checked BEFORE volume because middle is also UP here
    if thumb and index and middle and ring and pinky:
        return WIN_TAB

    # ── 2. BRIGHTNESS — thumb + pinky only, rest folded ────
    # Your condition was correct — problem was wrong distance used
    if thumb and not index and not middle and not ring and pinky:
        return BRIGHTNESS

    # ── 3. VOLUME — pinch + middle UP ──────────────────────
    # Now safe — WIN_TAB and BRIGHTNESS already handled above
    if middle and idx_pinch < config.VOL_PINCH_MAX:
        return VOLUME

    # ── 4. RIGHT CLICK ──────────────────────────────────────
    if mid_pinch < config.PINCH_TIGHT and not index and not ring and not pinky:
        return RIGHT_CLICK

    # ── 5. PAGE UP  👍 ──────────────────────────────────────
    if is_fist and t_dir == 'up':
        return PAGE_UP

    # ── 6. PAGE DOWN  👎 ────────────────────────────────────
    if is_fist and t_dir == 'down':
        return PAGE_DOWN

    # ── 7. MOVE CURSOR ──────────────────────────────────────
    if index and idx_pinch > config.PINCH_OPEN and not middle:
        return MOVE

    # ── 8. DRAG ─────────────────────────────────────────────
    if idx_pinch < config.PINCH_TIGHT and ring and not middle:
        return DRAG

    # ── 9. LEFT CLICK ───────────────────────────────────────
    if idx_pinch < config.PINCH_TIGHT and not middle and not ring:
        return LEFT_CLICK

    return NEUTRAL
