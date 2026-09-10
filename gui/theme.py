"""Central design tokens for the RSVP reader's "cozy fireside" theme.
Every styled component reads its colors and fonts from here, so a
future palette or font change happens in exactly one place."""

import os
import ctypes

# ---- Colors ----

HEARTH_PAPER = "#F6EFE3"     # base background — light surfaces
COCOA_INK = "#3B2E27"        # dark chrome — sidebar, dark surfaces
COCOA_INK_LIGHT = "#4A3C33"  # one step lighter than Cocoa Ink — rows/cards on dark surfaces
WARM_TAUPE = "#ECE0CF"       # card/panel surfaces on the light side
DUSK_BLUE = "#6E8496"        # muted accent — used sparingly, never a dominant color
EMBER_GLOW = "#D98A3D"       # warm accent — "+" buttons, highlights, active states
WARM_LINE = "#D6C4AC"        # borders and hairline dividers

TEXT_ON_LIGHT = COCOA_INK    # body text sitting on Hearth Paper / Warm Taupe
TEXT_ON_DARK = HEARTH_PAPER  # body text sitting on Cocoa Ink

# ---- Fonts ----
# These are the family names Windows should report after registering
# the bundled .ttf files below. Google Fonts exports are usually named
# exactly this way, but it can vary — the verification step in chat
# confirms this, and these two constants are the only place to correct
# it if it doesn't match.

FONT_HEADING = "Fredoka SemiBold"  # the flashing word display, section headings
FONT_BODY = "Quicksand Medium"     # everyday UI chrome — labels, buttons, lists

_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
_FONT_FILES = ["Fredoka-SemiBold.ttf", "Quicksand-Medium.ttf"]

_FR_PRIVATE = 0x10


def register_fonts() -> None:
    """Load the bundled font files for this process only — no system-wide
    install, no admin rights needed, nothing left behind for other
    applications on this machine. Windows-only, since AddFontResourceExW
    is a Windows GDI call; silently does nothing on other platforms, or
    for a file that isn't there yet, rather than crashing the app."""
    if os.name != "nt":
        return
    for filename in _FONT_FILES:
        path = os.path.join(_FONT_DIR, filename)
        if os.path.exists(path):
            ctypes.windll.gdi32.AddFontResourceExW(ctypes.c_wchar_p(path), _FR_PRIVATE, 0)


def unregister_fonts() -> None:
    """Mirror of register_fonts(), called on app close. Not strictly
    required — private fonts release automatically when the process
    exits — but tidy to do explicitly rather than rely on that."""
    if os.name != "nt":
        return
    for filename in _FONT_FILES:
        path = os.path.join(_FONT_DIR, filename)
        if os.path.exists(path):
            ctypes.windll.gdi32.RemoveFontResourceExW(ctypes.c_wchar_p(path), _FR_PRIVATE, 0)