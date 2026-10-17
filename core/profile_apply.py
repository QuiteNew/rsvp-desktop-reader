"""Working out what applying a reading profile actually does.

This is the pure step between a saved profile and the app. It takes the values
a profile holds plus the settings as they are right now, and hands back the
complete set of values the app should end up with. The GUI then writes those
through the usual SettingsStore setters and canvas calls, so nothing here
touches a store or a widget.

Three things are sorted out on the way:

- Numbers are clamped to the same ranges the Settings window enforces. The
  window's sliders and steppers are the only place those ranges are checked,
  so a profile from a hand-edited settings.json, an import, or a version with
  different limits could otherwise push a value the window would never allow.
- A setting the profile doesn't hold is filled in from the current settings,
  which is how "leave that setting alone" works. It also means the grouped
  setters (skip behaviour, resume rewind) always get both of their values. That
  is also what keeps a profile saved before a setting joined the list working:
  the newer settings are simply missing from it, so they stay as they are.
- The guide mark colour is resolved against the current theme. A profile that
  stored None was following the theme when it was saved, so it gets the
  theme's colour now and keeps following. A colour picked by hand is applied as
  it is and stops following."""

from dataclasses import dataclass

from core.profiles import PROFILE_KEYS, sanitize_values
from core.settings_store import (
    FONT_SIZE_RANGE, FONT_SIZE_STEP_RANGE, GUIDE_MARK_LENGTH_PERCENT_RANGE,
    GUIDE_MARK_THICKNESS_RANGE, HIGHLIGHT_OFFSET_RANGE, RESUME_REWIND_WORDS_RANGE,
    SKIP_WORD_COUNT_RANGE, WPM_RANGE,
)

# The allowed (low, high) for every profile setting that is a number. These are
# the very constants the Settings window uses for its controls.
NUMBER_RANGES = {
    "highlight_offset_px": HIGHLIGHT_OFFSET_RANGE,
    "guide_mark_thickness_px": GUIDE_MARK_THICKNESS_RANGE,
    "guide_mark_length_percent": GUIDE_MARK_LENGTH_PERCENT_RANGE,
    "resume_rewind_words": RESUME_REWIND_WORDS_RANGE,
    "skip_word_count": SKIP_WORD_COUNT_RANGE,
    "default_wpm": WPM_RANGE,
    "default_font_size": FONT_SIZE_RANGE,
    "font_size_step": FONT_SIZE_STEP_RANGE,
}


@dataclass(frozen=True)
class ProfilePlan:
    """What the app should hold after a profile is applied.

    values has every key in PROFILE_KEYS, already clamped, with the guide mark
    colour already resolved to a "#RRGGBB" string. guide_mark_follows_theme says
    whether that colour should keep tracking the Light/Dark theme."""
    values: dict
    guide_mark_follows_theme: bool


def clamp_value(key: str, value: int) -> int:
    """Pull a number into the allowed range for its setting."""
    low, high = NUMBER_RANGES[key]
    return max(low, min(high, value))


def plan_profile(profile_values, current_values, current_guide_follows_theme, theme_guide_mark_color) -> ProfilePlan:
    """Work out the result of applying a profile.

    profile_values is what the profile holds. Anything in it that isn't a known
    key with a valid value is ignored, the same as when profiles are loaded.
    current_values must have every key in PROFILE_KEYS (a missing one raises
    KeyError, since that means the caller and this module disagree about what a
    profile holds), and it is what fills in the settings the profile leaves out.
    current_guide_follows_theme is whether the guide mark colour is following
    the theme right now. theme_guide_mark_color is the colour the current
    Light/Dark theme gives the guide marks.

    Neither input is changed."""
    values = {key: current_values[key] for key in PROFILE_KEYS}
    follows_theme = bool(current_guide_follows_theme)

    for key, value in sanitize_values(profile_values).items():
        if key == "guide_mark_color":
            if value is None:
                values[key] = theme_guide_mark_color
                follows_theme = True
            else:
                values[key] = value
                follows_theme = False
        elif key in NUMBER_RANGES:
            values[key] = clamp_value(key, value)
        else:
            values[key] = value

    return ProfilePlan(values, follows_theme)