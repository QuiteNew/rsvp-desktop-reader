"""Central design tokens for the RSVP reader's "cozy fireside" theme.
Every styled component reads its colors and fonts from here, so a
future palette or font change happens in exactly one place.

Theme switching (Light/Dark/System) is resolved ONCE, here, at import
time — before any other module that reads these constants gets loaded.
That's what lets every component file keep importing plain names like
HEARTH_PAPER unchanged; this file alone decides what they equal."""

import os
import ctypes

# ---- Palettes ----

LIGHT_PALETTE = {
    "hearth_paper": "#F6EFE3",
    "cocoa_ink": "#3B2E27",
    "cocoa_ink_light": "#4A3C33",
    "warm_taupe": "#ECE0CF",
    "warm_mocha": "#B7A38A",
    "dusk_blue": "#6E8496",
    "dusk_blue_hover": "#5C7284",
    "ember_glow": "#D98A3D",
    "ember_glow_hover": "#C17A2F",
    "warm_line": "#D6C4AC",
    "text_on_light": "#3B2E27",
    "text_on_dark": "#F6EFE3",
}

DARK_PALETTE = {
    "hearth_paper": "#1D1712",       # soft near-black, warm brown undertone — never blue
    "cocoa_ink": "#F2E8DC",          # was dark text-on-light; now light text-on-dark
    "cocoa_ink_light": "#D9CBB8",
    "warm_taupe": "#2E2419",         # sidebar/header/entry-field panels — a step lighter than base
    "warm_mocha": "#4A3826",         # Spaces/Footer band — the richest, lightest of the dark surfaces
    "dusk_blue": "#7C93A3",
    "dusk_blue_hover": "#6B7F8C",
    "ember_glow": "#A8672E",         # deliberately darker/more burnt than the light theme's Ember Glow
    "ember_glow_hover": "#BF7A3B",   # hover goes LIGHTER here, not darker — the visible direction on dark UIs
    "warm_line": "#7A6248",          # doubles as border color and inactive-space text — needs to read both ways
    "text_on_light": "#F2E8DC",
    "text_on_dark": "#1D1712",
}


def _detect_system_prefers_dark() -> bool:
    """Best-effort read of the OS's own light/dark preference, used only
    when the appearance mode is set to 'system'."""
    try:
        import darkdetect
        return darkdetect.isDark() is True
    except Exception:
        return False


def _resolve_active_palette():
    """Decide once which palette and CTk appearance-mode string to use,
    based on the saved setting. Falls back to Light on any error (e.g.
    a fresh install with no settings file yet), so a theming problem can
    never prevent the app from launching."""
    mode = "light"
    try:
        from core.settings_store import SettingsStore
        mode = SettingsStore().appearance_mode
    except Exception:
        pass

    if mode == "dark":
        is_dark = True
    elif mode == "system":
        is_dark = _detect_system_prefers_dark()
    else:
        is_dark = False

    palette = DARK_PALETTE if is_dark else LIGHT_PALETTE
    ctk_mode = "Dark" if is_dark else "Light"
    return palette, ctk_mode


_active, CTK_APPEARANCE_MODE = _resolve_active_palette()

# ---- Colors ----

HEARTH_PAPER = _active["hearth_paper"]
COCOA_INK = _active["cocoa_ink"]
COCOA_INK_LIGHT = _active["cocoa_ink_light"]
WARM_TAUPE = _active["warm_taupe"]
WARM_MOCHA = _active["warm_mocha"]
DUSK_BLUE = _active["dusk_blue"]
DUSK_BLUE_HOVER = _active["dusk_blue_hover"]
EMBER_GLOW = _active["ember_glow"]
EMBER_GLOW_HOVER = _active["ember_glow_hover"]
WARM_LINE = _active["warm_line"]
TEXT_ON_LIGHT = _active["text_on_light"]
TEXT_ON_DARK = _active["text_on_dark"]

# ---- Fonts ----

FONT_HEADING = "Fredoka SemiBold"
FONT_BODY = "Quicksand Medium"

_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
_FONT_FILES = ["Fredoka-SemiBold.ttf", "Quicksand-Medium.ttf"]

_FR_PRIVATE = 0x10


def register_fonts() -> None:
    if os.name != "nt":
        return
    for filename in _FONT_FILES:
        path = os.path.join(_FONT_DIR, filename)
        if os.path.exists(path):
            ctypes.windll.gdi32.AddFontResourceExW(ctypes.c_wchar_p(path), _FR_PRIVATE, 0)


def unregister_fonts() -> None:
    if os.name != "nt":
        return
    for filename in _FONT_FILES:
        path = os.path.join(_FONT_DIR, filename)
        if os.path.exists(path):
            ctypes.windll.gdi32.RemoveFontResourceExW(ctypes.c_wchar_p(path), _FR_PRIVATE, 0)