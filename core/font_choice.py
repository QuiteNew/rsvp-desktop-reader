"""Which fonts the app uses.

There are two sets. The standard one is Fredoka for headings and Quicksand for
body text. The other is OpenDyslexic, picked with the "Use the OpenDyslexic
font" switch in Settings. This module only holds the names and the file lists,
makes the choice and words the notes that go with the switch. It never touches
a widget or the disk, so it can be tested without a window. gui/theme.py reads
the setting, looks at which font files are really in the folder, asks
choose_fonts() and sets the app's fonts from the answer, once, at startup. That
is why turning the switch on or off takes effect on the next launch."""

from dataclasses import dataclass, replace
from typing import Iterable


@dataclass(frozen=True)
class FontChoice:
    """One set of fonts.

    heading and body are the family names exactly as Tk and Windows know them
    once the files are registered. files are the font files (in assets/fonts)
    that have to be registered for those names to work.

    dyslexia_friendly is True for the OpenDyslexic set. fell_back is True when
    the switch was on but the OpenDyslexic files were not found, so the standard
    fonts were used instead; Settings can use that to explain why the font did
    not change."""
    heading: str
    body: str
    files: tuple[str, ...]
    dyslexia_friendly: bool = False
    fell_back: bool = False


STANDARD_FONTS = FontChoice(
    heading="Fredoka SemiBold",
    body="Quicksand Medium",
    files=("Fredoka-SemiBold.ttf", "Quicksand-Medium.ttf"),
)

# The two OpenDyslexic files register as two separate families, not one family
# with a regular and a bold face: the Regular file is "OpenDyslexic 3" (with a
# space) and the Bold file is "OpenDyslexic3" (without one). The names differ
# by that single space, and Windows will not find a family if it is wrong. Body
# text uses the Regular file and headings the Bold one, the same split as
# Quicksand and Fredoka in the standard set.
DYSLEXIA_FONTS = FontChoice(
    heading="OpenDyslexic3",
    body="OpenDyslexic 3",
    files=("OpenDyslexic3-Regular.ttf", "OpenDyslexic3-Bold.ttf"),
    dyslexia_friendly=True,
)


def choose_fonts(dyslexia_font_enabled, present_files: Iterable[str]) -> FontChoice:
    """The fonts to use, from the saved switch and the names of the files found
    in the fonts folder.

    Only a real True turns the OpenDyslexic set on. A damaged settings file
    holding something else (a string, a number, nothing) leaves the standard
    fonts in place rather than guessing.

    When the switch is on but either OpenDyslexic file is missing, the standard
    fonts are returned with fell_back set. Without that, every label in the app
    would be drawn in whatever font Windows picks as a stand-in. File names are
    compared without regard to case, since Windows does the same."""
    if dyslexia_font_enabled is not True:
        return STANDARD_FONTS
    present = {name.casefold() for name in present_files}
    if all(name.casefold() in present for name in DYSLEXIA_FONTS.files):
        return DYSLEXIA_FONTS
    return replace(STANDARD_FONTS, fell_back=True)


def bold_family(family: str) -> str:
    """The family to draw bold text in, when the plain text is drawn in `family`.

    Nearly every family is its own bold: ask for bold in the same family and the
    system picks the bold face, or fakes one. OpenDyslexic is the exception. Its
    Regular file is the family "OpenDyslexic 3" and its Bold file is a different
    family, "OpenDyslexic3" (see the note on DYSLEXIA_FONTS), so asking for bold
    in the regular one would get a faked bold instead of the face the font ships
    with. Names are compared without regard to case, as Windows does."""
    if family.casefold() == DYSLEXIA_FONTS.body.casefold():
        return DYSLEXIA_FONTS.heading
    return family


# ---- Notes shown under the Settings switch ----

RESTART_NOTE = (
    "Takes effect the next time you launch the app, and isn't saved in "
    "reading profiles."
)

# Only Windows lets the app load its own font files (see gui/theme.py). Anywhere
# else the family has to be installed on the system, or Tk draws the text in a
# stand-in font and the switch seems to do nothing.
NOT_LOADED_NOTE = (
    "On macOS and Linux the app can't load this font itself. Install "
    "OpenDyslexic on your system first (the files are in the app's "
    "assets/fonts folder), or the text will be drawn in a stand-in font."
)

FELL_BACK_NOTE = (
    "The OpenDyslexic font files weren't found in the app's fonts folder, so "
    "the standard fonts are in use for now."
)


def font_switch_notes(app_loads_fonts: bool, fell_back: bool) -> tuple[str, ...]:
    """The grey notes to show under the font switch, top to bottom.

    app_loads_fonts says whether the app registers its own font files on this
    system (True on Windows only). fell_back is FontChoice.fell_back for the
    fonts in use this run, True when the switch was on but the OpenDyslexic
    files were missing. The restart note is always there, since the choice is
    only read at startup."""
    notes = [RESTART_NOTE]
    if not app_loads_fonts:
        notes.append(NOT_LOADED_NOTE)
    if fell_back:
        notes.append(FELL_BACK_NOTE)
    return tuple(notes)