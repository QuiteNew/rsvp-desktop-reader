"""Changing the reading speed from the keyboard. The Up and Down arrow keys make
the open transcript WPM_KEY_STEP words per minute faster or slower, within the
range Settings allows (WPM_RANGE in core/settings_store.py). The windows that
bind the keys are gui/app.py and gui/components/detached_window.py."""

from core.settings_store import WPM_RANGE

WPM_KEY_STEP = 10


def step_wpm(wpm: int, direction: int) -> int:
    """The speed one step faster (direction 1) or slower (direction -1) than
    wpm. It always lands on a multiple of WPM_KEY_STEP, the same values the
    footer's slider stops at, so a speed like 305 (a default typed in Settings)
    goes to 310 or 300 rather than 315 or 295. It never leaves WPM_RANGE, so at
    either end of the range the speed stays as it is."""
    if direction > 0:
        stepped = (wpm // WPM_KEY_STEP + 1) * WPM_KEY_STEP
    else:
        stepped = ((wpm - 1) // WPM_KEY_STEP) * WPM_KEY_STEP
    low, high = WPM_RANGE
    return max(low, min(high, stepped))
