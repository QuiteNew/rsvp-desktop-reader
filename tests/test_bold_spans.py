"""Tests for core/bold_spans.py: turning bold stretches into Tk "line.column"
places, and finding the lines an edit touched.

Which letters are bold is tested in test_bold_starts.py. This file only checks
that the same stretches come out as Tk places, including after an emoji, which
Tk 8.6 counts as two columns and Tk 9 as one, and that the changed block of
lines is found correctly."""

import random

import pytest

from core.bold_spans import changed_lines, tk_spans
from core.bold_starts import bold_ranges

EMOJI = "\U0001F600"


def _tk_units(line: str, astral_width: int) -> list[str]:
    """A line the way a Tk text widget counts it: one unit per column. A
    character outside the Basic Multilingual Plane takes astral_width units, the
    first holding the character and the rest a placeholder. Slicing this by Tk
    columns and joining gives what Tk would hand back for that range."""
    units = []
    for char in line:
        units.append(char)
        if ord(char) > 0xFFFF:
            units.extend("\0" * (astral_width - 1))
    return units


def _bold_pieces(text: str, astral_width: int) -> list[str]:
    """The text of each stretch tk_spans() names, cut out the way Tk would."""
    lines = text.split("\n")
    return ["".join(_tk_units(lines[line - 1], astral_width)[start:end])
            for line, start, end in tk_spans(text, astral_width)]


# ---- tk_spans: the basics ----

def test_it_gives_the_line_and_the_columns_of_each_bold_stretch():
    assert tk_spans("reading is fun") == [(1, 0, 4), (1, 8, 9), (1, 11, 13)]

def test_an_empty_text_has_no_spans():
    assert tk_spans("") == []

def test_a_text_with_nothing_to_bold_has_no_spans():
    assert tk_spans("1234 ... 5678\n\n12:30") == []

def test_each_part_of_a_hyphenated_word_gets_its_own_span():
    assert tk_spans("well-known") == [(1, 0, 2), (1, 5, 8)]

def test_lines_are_numbered_from_one():
    assert tk_spans("alpha\nbravo\ncharlie") == [(1, 0, 3), (2, 0, 3), (3, 0, 3)]

def test_blank_lines_have_no_spans_but_still_count():
    assert tk_spans("alpha\n\n\nbravo") == [(1, 0, 3), (4, 0, 3)]

def test_a_trailing_newline_adds_nothing():
    assert tk_spans("alpha\n") == tk_spans("alpha")

def test_the_first_line_can_be_numbered_from_somewhere_else():
    assert tk_spans("alpha\nbravo", first_line=5) == [(5, 0, 3), (6, 0, 3)]

def test_a_piece_cut_from_a_longer_text_matches_the_same_lines_of_the_whole():
    whole = "one\ntwo words here\nthree\nfour and five"
    lines = whole.split("\n")
    piece = "\n".join(lines[1:3])
    inside_whole = [span for span in tk_spans(whole) if span[0] in (2, 3)]
    assert tk_spans(piece, first_line=2) == inside_whole

def test_only_a_newline_ends_a_line_not_the_other_separators():
    # Python's splitlines() would cut at these, Tk does not, so the columns must
    # keep counting along the same line.
    for separator in (chr(0x2028), chr(0x2029), chr(0x0B), chr(0x0C), chr(0x85), "\r"):
        spans = tk_spans(f"alpha{separator}bravo")
        assert {line for line, _, _ in spans} == {1}, repr(separator)

def test_a_carriage_return_is_just_a_character_on_the_line():
    assert tk_spans("alpha\r\nbravo") == [(1, 0, 3), (2, 0, 3)]

def test_the_spans_are_the_same_stretches_bold_ranges_finds():
    text = "Hello, world! It's a well-known fact that state-of-the-art tools\n\u041a\u0438\u0440\u0438\u043b\u0438\u0446\u0430 \u0438 \u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac \u0442\u043e\u0436\u0435.\n\nmp3 3rd H2O"
    lines = text.split("\n")
    from_spans = [lines[line - 1][start:end] for line, start, end in tk_spans(text)]
    assert from_spans == [text[start:end] for start, end in bold_ranges(text)]

def test_the_result_is_a_list_of_plain_int_triples():
    spans = tk_spans("alpha bravo")
    assert isinstance(spans, list)
    assert all(isinstance(span, tuple) and len(span) == 3 and all(type(n) is int for n in span) for span in spans)


# ---- tk_spans: characters outside the Basic Multilingual Plane ----

@pytest.mark.parametrize("astral_width, expected", [(1, (2, 5)), (2, (3, 6))])
def test_a_word_after_an_emoji_is_shifted_by_what_tk_counts_the_emoji_as(astral_width, expected):
    assert tk_spans(f"{EMOJI} hello", astral_width) == [(1, *expected)]

@pytest.mark.parametrize("astral_width, expected", [(1, (8, 11)), (2, (9, 12))])
def test_an_emoji_in_the_middle_of_a_line_shifts_the_words_after_it(astral_width, expected):
    # "world" starts at Python position 8 (after "hello", a space, the emoji and
    # another space). Tk 8.6 counts the emoji as two columns, so it starts at 9.
    spans = tk_spans(f"hello {EMOJI} world", astral_width)
    assert spans[-1] == (1, *expected)

def test_two_emoji_shift_a_word_by_two_extra_columns_on_tk_8_6():
    spans_plain = tk_spans(f"{EMOJI}{EMOJI} hello", 1)
    spans_tk86 = tk_spans(f"{EMOJI}{EMOJI} hello", 2)
    assert spans_tk86[0][1] - spans_plain[0][1] == 2

def test_a_word_before_an_emoji_is_not_shifted():
    assert tk_spans(f"hello {EMOJI}", 2) == tk_spans(f"hello {EMOJI}", 1) == [(1, 0, 3)]

def test_an_emoji_on_one_line_does_not_shift_the_next_line():
    spans = tk_spans(f"{EMOJI} one\nhello", 2)
    assert spans[-1] == (2, 0, 3)

def test_an_emoji_does_not_change_the_end_of_a_stretch_inside_one_word_run():
    # The emoji ends the first word, so "hello" and "world" are both cut on
    # their own letters whichever way the emoji is counted.
    for width in (1, 2):
        assert _bold_pieces(f"hello{EMOJI}world", width) == ["hel", "wor"]

@pytest.mark.parametrize("astral_width", [1, 2])
def test_cut_out_the_way_tk_counts_the_spans_are_the_bold_letters(astral_width):
    text = f"{EMOJI} hello, {EMOJI}{EMOJI} wonderful {EMOJI} world\n{EMOJI}x reading"
    lines = text.split("\n")
    expected = [lines[line - 1][start:end] for line, start, end in tk_spans(text, 1)]
    assert _bold_pieces(text, astral_width) == expected

@pytest.mark.parametrize("astral_width", [1, 2])
def test_a_span_never_cuts_an_emoji_in_half(astral_width):
    text = f"{EMOJI}alpha{EMOJI}bravo {EMOJI} charlie{EMOJI}"
    for piece in _bold_pieces(text, astral_width):
        assert "\0" not in piece
        assert EMOJI not in piece

@pytest.mark.parametrize("astral_width", [1, 2])
def test_random_text_with_emoji_comes_out_on_the_right_letters(astral_width):
    rng = random.Random(7)
    alphabet = ["a", "b", "e", "r", "Z", "\u0436", "\u03b1", " ", " ", "-", "'", "1", ".", "\n", EMOJI, "\u0301"]
    for _ in range(300):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
        lines = text.split("\n")
        expected = [lines[line - 1][start:end] for line, start, end in tk_spans(text, 1)]
        assert _bold_pieces(text, astral_width) == expected, repr(text)

def test_width_one_changes_nothing_for_a_text_with_emoji():
    text = f"{EMOJI} hello {EMOJI} world"
    assert tk_spans(text, 1) == tk_spans(text)

def test_the_columns_stay_python_positions_when_there_is_no_emoji_at_any_width():
    text = "reading is fun\nwell-known"
    assert tk_spans(text, 2) == tk_spans(text, 1)


# ---- changed_lines ----

def test_nothing_changed_gives_an_empty_block_at_the_end():
    assert changed_lines(["a", "b", "c"], ["a", "b", "c"]) == (3, 3)

def test_two_empty_texts_have_nothing_changed():
    assert changed_lines([], []) == (0, 0)

def test_an_edit_in_the_middle_gives_just_that_line():
    assert changed_lines(["a", "b", "c"], ["a", "X", "c"]) == (1, 2)

def test_an_edit_on_the_first_line():
    assert changed_lines(["a", "b", "c"], ["X", "b", "c"]) == (0, 1)

def test_an_edit_on_the_last_line():
    assert changed_lines(["a", "b", "c"], ["a", "b", "X"]) == (2, 3)

def test_lines_added_in_the_middle_are_the_block():
    assert changed_lines(["a", "c"], ["a", "x", "y", "c"]) == (1, 3)

def test_lines_added_at_the_end_are_the_block():
    assert changed_lines(["a"], ["a", "b", "c"]) == (1, 3)

def test_lines_added_at_the_start_are_the_block():
    assert changed_lines(["c"], ["a", "b", "c"]) == (0, 2)

def test_lines_removed_from_the_middle_leave_an_empty_block_where_they_were():
    assert changed_lines(["a", "x", "y", "c"], ["a", "c"]) == (1, 1)

def test_lines_removed_from_the_end_leave_an_empty_block_at_the_end():
    assert changed_lines(["a", "b", "c"], ["a"]) == (1, 1)

def test_two_lines_joined_into_one_give_the_joined_line():
    assert changed_lines(["a", "b", "c"], ["ab", "c"]) == (0, 1)

def test_one_line_split_into_two_gives_both_lines():
    assert changed_lines(["ab", "c"], ["a", "b", "c"]) == (0, 2)

def test_everything_replaced_gives_everything():
    assert changed_lines(["a", "b"], ["x", "y", "z"]) == (0, 3)

def test_a_text_cleared_gives_an_empty_block():
    assert changed_lines(["a", "b"], []) == (0, 0)

def test_a_text_filled_from_nothing_gives_every_line():
    assert changed_lines([], ["a", "b"]) == (0, 2)

def test_two_edits_far_apart_give_one_block_covering_both():
    old = ["a", "b", "c", "d", "e"]
    new = ["X", "b", "c", "d", "Y"]
    assert changed_lines(old, new) == (0, 5)

def test_repeated_lines_do_not_confuse_it():
    assert changed_lines(["a", "a", "a"], ["a", "a", "a", "a"]) == (3, 4)
    assert changed_lines(["a", "a", "a", "a"], ["a", "a", "a"]) == (3, 3)
    assert changed_lines(["a", "b", "a"], ["a", "b", "b", "a"]) == (2, 3)

def test_blank_lines_are_lines_like_any_other():
    assert changed_lines(["a", "", "b"], ["a", "", "", "b"]) == (2, 3)

def test_it_does_not_change_the_lists_it_is_given():
    old, new = ["a", "b", "c"], ["a", "X", "c"]
    changed_lines(old, new)
    assert old == ["a", "b", "c"] and new == ["a", "X", "c"]

def test_after_any_single_edit_the_lines_outside_the_block_are_the_old_ones():
    rng = random.Random(11)
    pool = ["a", "b", "c", "", "same", "same", "word word"]
    for _ in range(2000):
        old = [rng.choice(pool) for _ in range(rng.randint(0, 12))]
        cut_from = rng.randint(0, len(old))
        cut_to = rng.randint(cut_from, len(old))
        inserted = [rng.choice(pool) for _ in range(rng.randint(0, 5))]
        new = old[:cut_from] + inserted + old[cut_to:]
        first, end = changed_lines(old, new)
        assert 0 <= first <= end <= len(new)
        # Nothing before the block changed, and what follows it is the old tail.
        assert new[:first] == old[:first]
        tail = len(new) - end
        assert new[end:] == old[len(old) - tail:]
        assert len(old) - tail >= first
        # The block is no bigger than what was put in.
        assert first >= cut_from
        # An inserted line that equals its neighbour can make the block slide by
        # a line, so only its size is bounded, not its exact place.
        assert end - first <= len(inserted)

def test_a_block_found_this_way_is_enough_to_rebuild_the_new_text_from_the_old():
    rng = random.Random(3)
    pool = ["a", "b", "", "same", "word word", "x"]
    for _ in range(2000):
        old = [rng.choice(pool) for _ in range(rng.randint(0, 10))]
        new = [rng.choice(pool) for _ in range(rng.randint(0, 10))]
        first, end = changed_lines(old, new)
        tail = len(new) - end
        assert old[:first] + new[first:end] + old[len(old) - tail:] == new