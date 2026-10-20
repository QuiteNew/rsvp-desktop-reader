"""Tests for core/bold_spans.py: turning bold stretches into Tk "line.column"
places, and leaving very long lines plain.

Which letters are bold is tested in test_bold_starts.py. This file only checks
that the same stretches come out as Tk places, including after an emoji, which
Tk 8.6 counts as two columns and Tk 9 as one, and that lines over the limit are
skipped."""

import random

import pytest

from core.bold_spans import MAX_BOLD_LINE, has_long_line, tk_spans
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


# ---- very long lines are left plain ----

def test_there_is_no_limit_unless_one_is_given():
    line = "word " * 5000
    assert len(tk_spans(line)) == 5000

def test_a_line_over_the_limit_has_no_spans():
    assert tk_spans("hello world", max_line=10) == []

def test_a_line_exactly_at_the_limit_is_still_bolded():
    assert tk_spans("hello world", max_line=11) == [(1, 0, 3), (1, 6, 9)]

def test_one_character_over_the_limit_is_left_plain():
    assert tk_spans("hello world", max_line=10) == []
    assert tk_spans("hello worl", max_line=10) == [(1, 0, 3), (1, 6, 8)]

def test_only_the_long_lines_are_skipped():
    text = "hello world\n" + "x" * 50 + "\nreading speed"
    assert tk_spans(text, max_line=20) == [(1, 0, 3), (1, 6, 9), (3, 0, 4), (3, 8, 11)]

def test_the_lines_after_a_skipped_one_keep_their_numbers():
    text = "aaa bbb\n" + "word " * 30 + "\nccc ddd"
    assert [line for line, _, _ in tk_spans(text, max_line=40)] == [1, 1, 3, 3]

def test_a_skipped_line_does_not_change_the_other_lines_spans():
    short = "reading speed\ninteresting words"
    mixed = "reading speed\n" + "word " * 40 + "\ninteresting words"
    plain = tk_spans(short)
    kept = tk_spans(mixed, max_line=100)
    assert [s for s in kept if s[0] == 1] == [s for s in plain if s[0] == 1]
    assert [(3,) + s[1:] for s in kept if s[0] == 3] == [(3,) + s[1:] for s in plain if s[0] == 2]

def test_the_limit_applies_to_a_piece_cut_from_a_longer_text_too():
    assert tk_spans("short one\n" + "w" * 30, first_line=7, max_line=20) == [(7, 0, 3), (7, 6, 8)]

def test_blank_lines_are_never_over_the_limit():
    assert tk_spans("\n\n", max_line=0) == []

def test_the_limit_counts_characters_not_columns():
    # An emoji is one character here, however many columns Tk gives it.
    line = EMOJI * 5 + " reading"
    assert tk_spans(line, astral_width=2, max_line=len(line)) != []
    assert tk_spans(line, astral_width=2, max_line=len(line) - 1) == []

def test_the_default_limit_is_the_one_the_widget_uses():
    assert MAX_BOLD_LINE == 4000

def test_has_long_line_is_true_when_any_line_is_over_the_limit():
    assert has_long_line("short\n" + "x" * 11, max_line=10)
    assert has_long_line("x" * 11 + "\nshort", max_line=10)

def test_has_long_line_is_false_at_the_limit_and_below():
    assert not has_long_line("x" * 10, max_line=10)
    assert not has_long_line("a\nbb\nccc", max_line=10)

def test_has_long_line_on_an_empty_text():
    assert not has_long_line("")

def test_has_long_line_uses_the_default_limit():
    assert not has_long_line("x" * MAX_BOLD_LINE)
    assert has_long_line("x" * (MAX_BOLD_LINE + 1))

def test_has_long_line_agrees_with_which_lines_tk_spans_skips():
    # A line with letters in it loses its spans exactly when it is over the
    # limit, and has_long_line says so when any line does.
    for text in ("hello world", "hello world\n" + "word " * 20, "", "a" * 25, "ab cd\n\n" + "x " * 30):
        for limit in (0, 5, 11, 50):
            with_limit = {line for line, _, _ in tk_spans(text, max_line=limit)}
            without = {line for line, _, _ in tk_spans(text)}
            lengths = {n: len(line) for n, line in enumerate(text.split("\n"), 1)}
            for number in without:
                assert (number not in with_limit) == (lengths[number] > limit), (text, limit, number)
            assert has_long_line(text, limit) == any(length > limit for length in lengths.values())