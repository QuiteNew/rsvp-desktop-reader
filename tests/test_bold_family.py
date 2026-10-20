"""Tests for bold_family() in core/font_choice.py: which font family the bold
word starts in the edit box are drawn in.

The rest of core/font_choice.py is tested in test_font_choice.py."""

import pytest

from core.font_choice import DYSLEXIA_FONTS, STANDARD_FONTS, bold_family


def test_the_regular_opendyslexic_family_is_bolded_in_the_family_of_its_bold_file():
    # The two files register as two families that differ by one space, see the
    # note on DYSLEXIA_FONTS. Bold in the regular one would be a faked bold.
    assert bold_family("OpenDyslexic 3") == "OpenDyslexic3"

def test_it_uses_the_names_in_the_font_set_not_its_own_copy_of_them():
    assert bold_family(DYSLEXIA_FONTS.body) == DYSLEXIA_FONTS.heading

def test_the_two_opendyslexic_names_are_the_ones_it_was_written_for():
    # If these ever change, the rule above needs another look.
    assert DYSLEXIA_FONTS.body == "OpenDyslexic 3"
    assert DYSLEXIA_FONTS.heading == "OpenDyslexic3"

def test_the_bold_family_is_left_as_it_is():
    assert bold_family(DYSLEXIA_FONTS.heading) == DYSLEXIA_FONTS.heading

@pytest.mark.parametrize("family", ["OpenDyslexic 3", "opendyslexic 3", "OPENDYSLEXIC 3", "OpenDyslexic 3".swapcase()])
def test_the_family_name_is_matched_without_regard_to_case(family):
    assert bold_family(family) == "OpenDyslexic3"

@pytest.mark.parametrize("family", ["Roboto", STANDARD_FONTS.body, STANDARD_FONTS.heading, "Segoe UI", "Arial"])
def test_every_other_family_is_its_own_bold(family):
    assert bold_family(family) == family

def test_a_family_that_only_looks_like_opendyslexic_is_left_alone():
    for family in ("OpenDyslexic", "OpenDyslexic 3 Mono", "OpenDyslexic  3", " OpenDyslexic 3", "OpenDyslexic 3 "):
        assert bold_family(family) == family

def test_an_empty_name_comes_back_empty():
    assert bold_family("") == ""

def test_it_always_returns_a_string():
    for family in ("Roboto", "OpenDyslexic 3", ""):
        assert isinstance(bold_family(family), str)