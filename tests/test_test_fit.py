"""Tests for core/text_fit.py, which cuts a line of text down to the room it
has. The measure function is made up here (one unit per character, or a wider
unit for some letters), so nothing needs a window or a font."""

import pytest

from core.text_fit import ELLIPSIS, fit_text


def one_per_character(text: str) -> int:
    return len(text)


def wide_capitals(text: str) -> int:
    """Capital letters take three units and everything else one, like a font
    where the letters are not all the same width."""
    return sum(3 if character.isupper() else 1 for character in text)


def test_text_that_fits_is_returned_as_it_is():
    assert fit_text("Short title", 20, one_per_character) == "Short title"


def test_text_that_exactly_fits_is_not_cut():
    assert fit_text("Exactly ten", 11, one_per_character) == "Exactly ten"


def test_text_one_unit_too_wide_is_cut_with_an_ellipsis():
    assert fit_text("Exactly ten!", 11, one_per_character) == "Exactly te" + ELLIPSIS


def test_the_cut_text_with_its_ellipsis_never_passes_the_room():
    text = "A transcript with a much longer name than the room allows"
    for room in range(1, len(text)):
        shown = fit_text(text, room, one_per_character)
        assert one_per_character(shown) <= max(room, 1), room


def test_the_longest_start_that_fits_is_kept():
    text = "abcdefghijklmnop"
    shown = fit_text(text, 8, one_per_character)
    assert shown == "abcdefg" + ELLIPSIS
    assert one_per_character(text[:8] + ELLIPSIS) > 8


def test_spaces_left_at_the_cut_are_dropped():
    assert fit_text("one two three", 8, one_per_character) == "one two" + ELLIPSIS
    assert fit_text("one two three", 5, one_per_character) == "one" + ELLIPSIS


def test_a_font_with_uneven_widths_is_measured_not_counted():
    # Three capitals take 9, "de" takes 2 and the ellipsis 1: exactly 12. One
    # more letter would make 13, so "ABCde" is the longest start that fits.
    assert fit_text("ABCdefGHIjkl", 12, wide_capitals) == "ABCde" + ELLIPSIS
    assert wide_capitals("ABCde" + ELLIPSIS) <= 12 < wide_capitals("ABCdef" + ELLIPSIS)


@pytest.mark.parametrize("room", [0, 1, -5])
def test_when_not_even_the_ellipsis_fits_the_ellipsis_alone_is_returned(room):
    assert fit_text("A long title", room, one_per_character) == ELLIPSIS


def test_empty_text_stays_empty():
    assert fit_text("", 10, one_per_character) == ""


def test_text_made_only_of_spaces_still_ends_in_the_ellipsis_alone():
    assert fit_text(" " * 30, 5, one_per_character) == ELLIPSIS


def test_another_ellipsis_can_be_given():
    assert fit_text("abcdefghij", 6, one_per_character, ellipsis="...") == "abc..."