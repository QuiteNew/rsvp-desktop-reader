"""Tests for core/font_choice.py: which fonts the app uses.

The choice is made once at startup from the saved "Dyslexia-friendly font"
switch and from the font files found in the fonts folder. These tests only deal
with the names and the decision. How gui/theme.py reads the setting and applies
the answer is in test_theme_fonts.py."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from core.font_choice import DYSLEXIA_FONTS, STANDARD_FONTS, FontChoice, choose_fonts

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

EVERY_FONT_FILE = STANDARD_FONTS.files + DYSLEXIA_FONTS.files


# ---- The two sets ----

def test_the_standard_fonts_are_fredoka_and_quicksand():
    # These are the names the app has always used, written down so a change to
    # them is a deliberate one.
    assert STANDARD_FONTS.heading == "Fredoka SemiBold"
    assert STANDARD_FONTS.body == "Quicksand Medium"

def test_the_dyslexia_fonts_use_the_names_the_two_files_register_under():
    # The Regular file registers as "OpenDyslexic 3" (with a space) and the Bold
    # file as "OpenDyslexic3" (without one). Checked against the real files in
    # the font probe on Windows. Get the space wrong and Windows quietly
    # substitutes another font.
    assert DYSLEXIA_FONTS.body == "OpenDyslexic 3"
    assert DYSLEXIA_FONTS.heading == "OpenDyslexic3"

def test_the_dyslexia_body_font_goes_with_the_regular_file_and_the_heading_with_the_bold_one():
    assert DYSLEXIA_FONTS.files == ("OpenDyslexic3-Regular.ttf", "OpenDyslexic3-Bold.ttf")

def test_the_standard_set_is_not_marked_dyslexia_friendly():
    assert STANDARD_FONTS.dyslexia_friendly is False
    assert STANDARD_FONTS.fell_back is False

def test_the_dyslexia_set_is_marked_dyslexia_friendly():
    assert DYSLEXIA_FONTS.dyslexia_friendly is True
    assert DYSLEXIA_FONTS.fell_back is False

def test_the_two_sets_share_no_family_name_and_no_file():
    standard_names = {STANDARD_FONTS.heading, STANDARD_FONTS.body}
    dyslexia_names = {DYSLEXIA_FONTS.heading, DYSLEXIA_FONTS.body}
    assert not standard_names & dyslexia_names
    assert not set(STANDARD_FONTS.files) & set(DYSLEXIA_FONTS.files)

def test_a_set_uses_a_different_family_for_headings_and_body_text():
    assert STANDARD_FONTS.heading != STANDARD_FONTS.body
    assert DYSLEXIA_FONTS.heading != DYSLEXIA_FONTS.body

def test_a_font_choice_cannot_be_changed_after_it_is_made():
    with pytest.raises(FrozenInstanceError):
        STANDARD_FONTS.body = "Something else"

@pytest.mark.parametrize("filename", EVERY_FONT_FILE)
def test_every_font_file_the_choices_name_is_in_the_fonts_folder(filename):
    assert (FONT_DIR / filename).is_file()


# ---- Switch off ----

def test_with_the_switch_off_the_standard_fonts_are_used():
    assert choose_fonts(False, EVERY_FONT_FILE) is STANDARD_FONTS

def test_with_the_switch_off_it_does_not_matter_which_files_are_there():
    assert choose_fonts(False, []) is STANDARD_FONTS

@pytest.mark.parametrize("damaged", [None, 0, 1, "yes", "true", "True", [], {}, ["x"]])
def test_only_a_real_true_turns_the_dyslexia_fonts_on(damaged):
    # A damaged settings file can leave anything in the field. None of it counts
    # as "on", and none of it counts as a fallback either: the switch was
    # never really on.
    chosen = choose_fonts(damaged, EVERY_FONT_FILE)
    assert chosen is STANDARD_FONTS
    assert chosen.fell_back is False


# ---- Switch on ----

def test_with_the_switch_on_and_the_files_present_the_dyslexia_fonts_are_used():
    assert choose_fonts(True, EVERY_FONT_FILE) is DYSLEXIA_FONTS

def test_it_is_enough_for_the_two_opendyslexic_files_to_be_there():
    assert choose_fonts(True, DYSLEXIA_FONTS.files) is DYSLEXIA_FONTS

def test_other_files_in_the_folder_do_not_get_in_the_way():
    assert choose_fonts(True, [*DYSLEXIA_FONTS.files, "notes.txt", "LICENSE.md"]) is DYSLEXIA_FONTS

@pytest.mark.parametrize("missing", DYSLEXIA_FONTS.files)
def test_with_one_opendyslexic_file_missing_it_falls_back_to_the_standard_fonts(missing):
    present = [name for name in EVERY_FONT_FILE if name != missing]
    chosen = choose_fonts(True, present)
    assert chosen.heading == STANDARD_FONTS.heading
    assert chosen.body == STANDARD_FONTS.body
    assert chosen.files == STANDARD_FONTS.files
    assert chosen.dyslexia_friendly is False
    assert chosen.fell_back is True

def test_with_an_empty_fonts_folder_it_falls_back_to_the_standard_fonts():
    chosen = choose_fonts(True, [])
    assert chosen.body == STANDARD_FONTS.body
    assert chosen.fell_back is True

def test_falling_back_does_not_change_the_standard_set_itself():
    choose_fonts(True, [])
    assert STANDARD_FONTS.fell_back is False
    assert choose_fonts(False, []).fell_back is False

def test_the_files_are_matched_without_regard_to_case():
    # Windows treats the names the same either way, so the check does too.
    shouting = [name.upper() for name in DYSLEXIA_FONTS.files]
    assert choose_fonts(True, shouting) is DYSLEXIA_FONTS

def test_the_file_names_can_come_from_any_iterable():
    assert choose_fonts(True, iter(DYSLEXIA_FONTS.files)) is DYSLEXIA_FONTS
    assert choose_fonts(True, set(DYSLEXIA_FONTS.files)) is DYSLEXIA_FONTS
    assert choose_fonts(True, tuple(DYSLEXIA_FONTS.files)) is DYSLEXIA_FONTS

def test_a_name_that_only_contains_the_file_name_does_not_count():
    # A file called "OpenDyslexic3-Regular.ttf.bak" is not the font.
    almost = [name + ".bak" for name in DYSLEXIA_FONTS.files]
    assert choose_fonts(True, almost).fell_back is True

def test_choose_fonts_always_returns_a_font_choice():
    for enabled in (True, False, None):
        for present in ([], EVERY_FONT_FILE):
            assert isinstance(choose_fonts(enabled, present), FontChoice)