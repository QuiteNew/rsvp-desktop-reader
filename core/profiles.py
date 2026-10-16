"""Reading profiles: named snapshots of the settings that decide how the
reader feels, so something like "Fast skim" and "Careful read" can be
switched between in one go.

This is the pure part. It knows which settings a profile holds, what a valid
value for each one looks like, and what makes a good profile name. It has no
GUI in it and no store. core/settings_store.py keeps the saved profiles and
imports the rules from here, and the code that applies a profile to the
running app builds on the split helpers at the bottom.

A profile holds two kinds of setting. Some exist twice, once on every
Transcript and once as an app-wide default that new transcripts start from
(WPM, the reading colours, font size and chunking). The others exist once,
app wide (the guide marks, the pacing options, skip behaviour). Applying a
profile touches both kinds, which is why they are listed separately below.

Left out on purpose: window and layout sizes, the data directory, the
Light/Dark/System mode, and settings that are about editing or the scrubber
rather than how the reader reads. Because the list is short and named here,
a profile saved by one version still loads in another. A key that is missing
from a saved profile simply means "leave that setting alone"."""

import re
from dataclasses import dataclass, field

MAX_NAME_LENGTH = 30

# Settings that exist on every Transcript and also as an app-wide default,
# stored in AppSettings as "default_<key>", which new transcripts start from.
PER_TRANSCRIPT_KEYS = (
    "wpm",
    "font_color",
    "highlight_color",
    "background_color",
    "font_size",
    "chunking_enabled",
    "chunk_size",
    "chunk_mode",
    "chunk_char_target",
)

# Settings that exist once, app wide, under the same name in AppSettings.
GLOBAL_KEYS = (
    "highlight_offset_px",
    "guide_mark_horizontal_enabled",
    "guide_mark_thickness_px",
    "guide_mark_length_percent",
    "guide_mark_color",
    "length_pacing_enabled",
    "warm_up_enabled",
    "resume_rewind_enabled",
    "resume_rewind_words",
    "peripheral_context_enabled",
    "skip_word_count",
    "pause_on_skip",
)

PROFILE_KEYS = PER_TRANSCRIPT_KEYS + GLOBAL_KEYS

# Colours that can follow the Light/Dark theme. A profile stores None for one
# of these when it was still following the theme at the moment the profile was
# saved, and a "#RRGGBB" value only for a colour that was picked by hand.
# Without that, applying a profile would freeze the colours against the
# theme. See the "follows the theme" flags on Transcript and AppSettings.
THEME_COLOR_KEYS = ("font_color", "highlight_color", "background_color", "guide_mark_color")

CHUNK_MODES = ("fixed", "adaptive")

_KINDS = {
    "wpm": "int",
    "font_color": "color",
    "highlight_color": "color",
    "background_color": "color",
    "font_size": "int",
    "chunking_enabled": "bool",
    "chunk_size": "int",
    "chunk_mode": "chunk_mode",
    "chunk_char_target": "int",
    "highlight_offset_px": "int",
    "guide_mark_horizontal_enabled": "bool",
    "guide_mark_thickness_px": "int",
    "guide_mark_length_percent": "int",
    "guide_mark_color": "color",
    "length_pacing_enabled": "bool",
    "warm_up_enabled": "bool",
    "resume_rewind_enabled": "bool",
    "resume_rewind_words": "int",
    "peripheral_context_enabled": "bool",
    "skip_word_count": "int",
    "pause_on_skip": "bool",
}

_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")


class ProfileError(ValueError):
    """Raised by SettingsStore's profile methods when a name is not allowed or
    the profile asked for doesn't exist. The message is written to be shown to
    the user as it is."""


@dataclass
class Profile:
    """One saved profile: a name and the settings it holds, keyed by the
    names in PROFILE_KEYS. A key can be missing (leave that setting alone),
    and a colour key can be None (follow the theme)."""
    name: str
    values: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """The plain form that is saved in settings.json and exported."""
        return {"name": self.name, "values": dict(self.values)}


# ---- Names ----

def clean_name(name) -> str:
    """Trim the name and squeeze any run of spaces, tabs or line breaks down
    to a single space. Anything that isn't text comes back as an empty
    string, which name_problem() then rejects."""
    if not isinstance(name, str):
        return ""
    return " ".join(name.split())


def name_problem(name, existing_names, own_name=None) -> str | None:
    """Why this name can't be used, as a short message for the user, or None
    when it is fine. Names are compared without regard to case, so "fast
    skim" clashes with "Fast skim".

    existing_names is every profile name already saved. When a profile is
    being renamed, pass its current name as own_name, so that keeping the
    name or only changing its capitals is not reported as a clash with
    itself."""
    cleaned = clean_name(name)
    if not cleaned:
        return "Give the profile a name."
    if len(cleaned) > MAX_NAME_LENGTH:
        return f"Use {MAX_NAME_LENGTH} characters or fewer."
    if not cleaned.isprintable():
        return "That name has a character that can't be shown."

    own = clean_name(own_name).casefold() if own_name is not None else None
    for existing in existing_names:
        folded = clean_name(existing).casefold()
        if folded == cleaned.casefold() and folded != own:
            return f'There is already a profile called "{existing}".'
    return None


# ---- Values ----

def value_is_valid(key: str, value) -> bool:
    """Whether value is something a profile may hold for this key. This checks
    the kind of value only (a whole number, a true/false, a "#RRGGBB" colour,
    one of the chunk modes). It does not check ranges: those live with the
    settings in core/settings_store.py, and are applied when a profile is
    applied."""
    kind = _KINDS.get(key)
    if kind is None:
        return False
    if key in THEME_COLOR_KEYS and value is None:
        return True
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "int":
        # bool is a kind of int in Python, and True must not pass as 1.
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "color":
        return isinstance(value, str) and _HEX_COLOR.fullmatch(value) is not None
    if kind == "chunk_mode":
        return value in CHUNK_MODES
    return False


def sanitize_values(values) -> dict:
    """Keep only the entries of values that are a known key with a valid
    value, in the order of PROFILE_KEYS. Anything else is dropped without a
    fuss, so a hand-edited or damaged settings.json can't put junk into the
    reader. Not a dict at all gives an empty dict."""
    if not isinstance(values, dict):
        return {}
    return {key: values[key] for key in PROFILE_KEYS if key in values and value_is_valid(key, values[key])}


def build_values(global_values, per_transcript_values, following_theme=()) -> dict:
    """Take a snapshot of the current settings as a profile's values.

    global_values holds the app-wide settings, keyed by GLOBAL_KEYS.
    per_transcript_values holds the per-transcript ones, keyed by
    PER_TRANSCRIPT_KEYS, read from the open transcript, or from the
    app-wide defaults when nothing is open. following_theme names the colour
    keys that are still following the theme, which are stored as None.

    Every key has to be present in the inputs. A missing one raises
    KeyError, since that would mean the caller and this module disagree about
    what a profile holds."""
    values = {}
    for key in PER_TRANSCRIPT_KEYS:
        values[key] = per_transcript_values[key]
    for key in GLOBAL_KEYS:
        values[key] = global_values[key]
    for key in following_theme:
        if key not in THEME_COLOR_KEYS:
            raise ValueError(f"{key!r} is not a colour that can follow the theme")
        values[key] = None
    return values


def global_part(values: dict) -> dict:
    """The app-wide settings in a profile's values."""
    return {key: values[key] for key in GLOBAL_KEYS if key in values}


def per_transcript_part(values: dict) -> dict:
    """The settings in a profile's values that apply to a transcript and to the
    defaults new transcripts start from."""
    return {key: values[key] for key in PER_TRANSCRIPT_KEYS if key in values}


# ---- Loading saved profiles ----

def profile_from_dict(raw) -> Profile | None:
    """Rebuild one profile from its saved form, or None when it can't be
    used: not a dict, no usable name, or values that aren't a dict. Invalid
    entries inside the values are dropped, see sanitize_values()."""
    if not isinstance(raw, dict):
        return None
    name = clean_name(raw.get("name"))
    if not name or len(name) > MAX_NAME_LENGTH or not name.isprintable():
        return None
    if not isinstance(raw.get("values"), dict):
        return None
    return Profile(name, sanitize_values(raw["values"]))


def clean_profile_list(raw) -> list[dict]:
    """Turn whatever was saved under "profiles" into a clean list of plain
    dicts. Unusable entries are skipped, and when two share a name (ignoring
    case) the first one is kept. Anything that isn't a list gives an empty
    list. Loading never fails because of a bad profile, which matters because
    a failed settings load falls back to the defaults for everything."""
    if not isinstance(raw, list):
        return []
    cleaned = []
    seen = set()
    for item in raw:
        profile = profile_from_dict(item)
        if profile is None or profile.name.casefold() in seen:
            continue
        seen.add(profile.name.casefold())
        cleaned.append(profile.to_dict())
    return cleaned