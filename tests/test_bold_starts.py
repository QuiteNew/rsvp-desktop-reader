"""Tests for core/bold_starts.py, the pure part of the edit box's bold word
starts: which letters at the front of each word get bold.

Most cases go through show(), which puts [ ] around each bold stretch so the
expected answer reads like the result on screen: "[we]ll-[kno]wn". The
characters that are invisible or easy to mangle (dashes, soft hyphens, combining
marks, curly apostrophes, emoji) are written as escapes."""

import pytest

import core.bold_starts as bold_starts
from core.bold_starts import (
    MAX_BOLD_LETTERS, MAX_NUDGE, bold_ranges, fixation_length,
)

SOFT_HYPHEN = "\u00ad"
ZERO_WIDTH_SPACE = "\u200b"
ACUTE = "\u0301"
CURLY_APOSTROPHE = "\u2019"
EMOJI = "\U0001F600"


def show(text):
    """The text with [ ] around every bold stretch."""
    pieces = []
    last = 0
    for start, end in bold_ranges(text):
        pieces.append(text[last:start])
        pieces.append("[" + text[start:end] + "]")
        last = end
    pieces.append(text[last:])
    return "".join(pieces)


# ---- How much of a word is bold ----

@pytest.mark.parametrize("letters, bold", [
    (1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (6, 3),
    (7, 4), (10, 4), (11, 5), (14, 5), (15, 6), (30, 6),
])
def test_fixation_length_table(letters, bold):
    assert fixation_length(letters) == bold

def test_a_word_of_two_letters_or_more_is_never_bold_all_the_way():
    for letters in range(2, 80):
        assert 1 <= fixation_length(letters) < letters

def test_the_bold_part_never_shrinks_as_the_word_grows_and_stops_at_the_cap():
    lengths = [fixation_length(n) for n in range(1, 80)]
    assert lengths == sorted(lengths)
    assert max(lengths) == MAX_BOLD_LETTERS


# ---- Ordinary words ----

@pytest.mark.parametrize("word, expected", [
    ("a", "[a]"),
    ("I", "[I]"),
    ("of", "[o]f"),
    ("the", "[th]e"),
    ("that", "[th]at"),
    ("about", "[abo]ut"),
    ("people", "[peo]ple"),
    ("NASA", "[NA]SA"),
    ("iPhone", "[iPh]one"),
])
def test_short_and_middling_words(word, expected):
    assert show(word) == expected

def test_a_sentence_gets_a_bold_start_on_every_word():
    assert show("The quick brown fox.") == "[Th]e [qui]ck [bro]wn [fo]x."


# ---- Long words ----

@pytest.mark.parametrize("word, expected", [
    ("reading", "[read]ing"),
    ("JavaScript", "[Java]Script"),
    ("internationalization", "[intern]ationalization"),
    ("pneumonoultramicroscopicsilicovolcanoconiosis", "[pneumo]noultramicroscopicsilicovolcanoconiosis"),
])
def test_long_words_stay_light_and_cut_between_a_vowel_and_a_consonant(word, expected):
    assert show(word) == expected

def test_a_very_long_word_is_never_far_from_the_cap():
    word = "a" + "bc" * 40
    (start, end), = bold_ranges(word)
    assert start == 0
    assert MAX_BOLD_LETTERS - MAX_NUDGE <= end <= MAX_BOLD_LETTERS + MAX_NUDGE


# ---- Where a long word is cut ----

def test_a_cut_in_a_consonant_cluster_moves_to_the_vowel_before_it():
    assert show("journey") == "[jou]rney"

def test_a_cut_between_two_vowels_moves_to_the_consonant_before_them():
    assert show("audience") == "[aud]ience"

def test_y_counts_as_a_vowel():
    assert show("rhythms") == "[rhy]thms"

def test_when_both_directions_are_equally_good_the_lighter_cut_wins():
    # Cutting after c or after u would both be clean for "because". The shorter
    # bold part is taken.
    assert show("because") == "[bec]ause"

def test_a_word_with_no_clean_cut_keeps_its_normal_length():
    assert show("brrrrrrr") == "[brrr]rrrr"

def test_short_words_are_not_nudged():
    assert show("boat") == "[bo]at"
    assert show("chair") == "[cha]ir"

def test_a_cut_is_never_made_right_before_a_cyrillic_sign():
    # Cutting after the fourth letter would leave the hard sign on its own at
    # the front of the light part.
    assert show("\u043c\u0430\u043c\u0430\u044a\u043c\u0430\u043c") == "[\u043c\u0430\u043c]\u0430\u044a\u043c\u0430\u043c"

def test_the_cyrillic_short_i_is_a_consonant():
    # If it were taken for the vowel "i", the cut would stay at four letters.
    word = "\u043a\u043a\u043a\u043a\u0439\u0438\u0438\u0438"
    assert show(word) == "[\u043a\u043a\u043a\u043a\u0439]\u0438\u0438\u0438"

def test_a_cut_moves_two_letters_but_not_three():
    # The only clean cut is two letters before the usual one here...
    assert show("babbbbbb") == "[ba]bbbbbb"
    # ...and three letters before it here, which is too far to go.
    assert show("abbbbbbb") == "[abbb]bbbb"

def test_a_wide_nudge_cannot_run_off_the_end_of_the_word(monkeypatch):
    # Nobody should be able to retune the nudge into an IndexError.
    monkeypatch.setattr(bold_starts, "MAX_NUDGE", 10)
    assert show("brrrrrrr") == "[brrr]rrrr"

def test_capital_letters_follow_the_same_rules():
    assert show("AUDIENCE") == "[AUD]IENCE"
    assert show("\u041c\u0410\u041c\u0410\u042a\u041c\u0410\u041c") == "[\u041c\u0410\u041c]\u0410\u042a\u041c\u0410\u041c"


# ---- Hyphens, dashes and the like: every part is its own word ----

def test_a_hyphenated_word_is_bold_at_the_start_of_each_part():
    assert show("well-known") == "[we]ll-[kno]wn"
    assert show("state-of-the-art") == "[sta]te-[o]f-[th]e-[ar]t"
    assert show("mother-in-law") == "[mot]her-[i]n-[la]w"

@pytest.mark.parametrize("separator", [
    "-", "\u2010", "\u2011", "\u2013", "\u2014", "/", "_", ".", ",", ":", ";", "(", ")",
])
def test_every_kind_of_separator_ends_a_word(separator):
    assert show("word" + separator + "word") == "[wo]rd" + separator + "[wo]rd"

def test_a_zero_width_space_ends_a_word():
    assert show("foo" + ZERO_WIDTH_SPACE + "bar") == "[fo]o" + ZERO_WIDTH_SPACE + "[ba]r"


# ---- Apostrophes ----

@pytest.mark.parametrize("word, expected", [
    ("don't", "[do]n't"),
    ("don" + CURLY_APOSTROPHE + "t", "[do]n" + CURLY_APOSTROPHE + "t"),
    ("O'Brien", "[O'Br]ien"),
    ("I'm", "[I]'m"),
    ("\u043c\u02bc\u044f\u0441\u043e", "[\u043c\u02bc\u044f]\u0441\u043e"),
])
def test_an_apostrophe_between_letters_stays_in_the_word(word, expected):
    assert show(word) == expected

def test_an_apostrophe_at_either_end_is_just_punctuation():
    assert show("dogs'") == "[do]gs'"
    assert show("'tis") == "'[ti]s"
    assert show("rock 'n' roll") == "[ro]ck '[n]' [ro]ll"

def test_a_lone_apostrophe_does_nothing():
    assert bold_ranges("'") == []
    assert bold_ranges("'' ' ''") == []

def test_an_apostrophe_at_the_very_start_does_not_borrow_the_last_character():
    # The word starts at position 1, and the text ends in a digit.
    assert show("'tis 5") == "'[ti]s 5"


# ---- Soft hyphens and joiners ----

def test_a_soft_hyphen_is_not_counted_and_never_changes_the_answer():
    plain = "reading"
    with_soft_hyphens = SOFT_HYPHEN.join(plain)
    assert show(with_soft_hyphens) == "[r\u00ade\u00ada\u00add]\u00adi\u00adn\u00adg"
    assert show(with_soft_hyphens).replace(SOFT_HYPHEN, "") == show(plain)

def test_a_soft_hyphen_in_the_middle_of_a_long_word_is_ignored_for_the_count():
    assert show("inter" + SOFT_HYPHEN + "national").replace(SOFT_HYPHEN, "") == show("international")

def test_a_soft_hyphen_at_the_end_of_a_word_is_left_out_of_the_bold_part():
    assert show("exam" + SOFT_HYPHEN) == "[ex]am" + SOFT_HYPHEN

@pytest.mark.parametrize("glue", ["\u200c", "\u200d", "\u2060"])
def test_joiners_stay_inside_a_word(glue):
    assert show("rea" + glue + "ding") == "[rea" + glue + "d]ing"


# ---- Combining marks ----

def test_a_combining_accent_stays_with_its_letter():
    assert show("cafe" + ACUTE) == "[ca]fe" + ACUTE
    assert show("ca" + ACUTE + "fe") == "[ca" + ACUTE + "]fe"

def test_a_single_accented_letter_is_bold_with_its_accent():
    assert show("e" + ACUTE) == "[e" + ACUTE + "]"

def test_a_combining_mark_with_no_letter_before_it_is_ignored():
    assert bold_ranges(" " + ACUTE + " ") == []
    assert bold_ranges("1" + ACUTE) == []


# ---- Alphabets ----

def test_cyrillic_words_get_bold_starts():
    assert show("\u041f\u0440\u0438\u0432\u0435\u0442") == "[\u041f\u0440\u0438]\u0432\u0435\u0442"
    assert show("\u043a\u044a\u0449\u0430") == "[\u043a\u044a]\u0449\u0430"

def test_greek_words_get_bold_starts():
    assert show("\u039a\u03b1\u03bb\u03b7\u03bc\u03ad\u03c1\u03b1") == "[\u039a\u03b1\u03bb\u03b7]\u03bc\u03ad\u03c1\u03b1"

def test_the_greek_question_mark_is_not_a_letter():
    assert show("\u03c4\u03b9\u037e") == "[\u03c4]\u03b9\u037e"

@pytest.mark.parametrize("text", [
    "\u4f60\u597d\u4e16\u754c",          # Chinese
    "\u3053\u3093\u306b\u3061\u306f",    # Japanese
    "\u0645\u0631\u062d\u0628\u0627",    # Arabic
    "\u05e9\u05dc\u05d5\u05dd",          # Hebrew
    "\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35",  # Thai
])
def test_scripts_we_do_not_handle_are_left_alone(text):
    assert bold_ranges(text) == []

def test_a_latin_word_next_to_another_script_is_still_bold():
    assert show("hello\u4f60\u597d") == "[hel]lo\u4f60\u597d"


# ---- Digits ----

@pytest.mark.parametrize("text", [
    "2024", "3.14", "3rd", "2nd", "H2O", "mp3", "x86", "version2", "1990's", "m\u00b2",
])
def test_numbers_and_words_with_a_digit_against_them_are_left_alone(text):
    assert bold_ranges(text) == []

def test_a_word_next_to_a_number_with_a_gap_or_a_hyphen_is_still_bold():
    assert show("COVID-19") == "[COV]ID-19"
    assert show("3-D") == "3-[D]"
    assert show("5 apples") == "5 [app]les"


# ---- Web and email addresses ----

def test_a_web_address_is_left_alone():
    assert show("see https://example.com/long-path now") == "[se]e https://example.com/long-path [no]w"
    assert show("www.example.org is") == "www.example.org [i]s"
    assert show("go (https://x.org/a) now") == "[g]o (https://x.org/a) [no]w"

def test_an_email_address_is_left_alone():
    assert show("mail bob@example.com please") == "[ma]il bob@example.com [ple]ase"
    assert show("alice.smith+tag@mail.example.co.uk") == "alice.smith+tag@mail.example.co.uk"


# ---- Blank and odd text ----

@pytest.mark.parametrize("text", ["", " ", "   \n\t  ", "!!! ... ???", "-- -- --", "12 34 56"])
def test_text_without_words_has_no_bold(text):
    assert bold_ranges(text) == []


# ---- Offsets ----

def test_the_ranges_count_characters_not_bytes():
    text = "hello " + EMOJI + " world"
    assert bold_ranges(text) == [(0, 3), (8, 11)]
    assert show(text) == "[hel]lo " + EMOJI + " [wor]ld"

def test_a_word_never_runs_across_a_line_break():
    assert show("ab\ncd") == "[a]b\n[c]d"
    assert show("ab\r\ncd") == "[a]b\r\n[c]d"

def test_a_whole_text_gives_the_same_ranges_as_its_lines_one_by_one():
    text = (
        "The well-known state-of-the-art audience\n"
        "don't read https://example.com/a-b now\n"
        "\n"
        "\u041f\u0440\u0438\u0432\u0435\u0442 \u043a\u044a\u0449\u0430 caf" + "e" + ACUTE + " 3rd\n"
        "inter" + SOFT_HYPHEN + "national 1990's"
    )
    by_line = []
    offset = 0
    for line in text.split("\n"):
        by_line += [(start + offset, end + offset) for start, end in bold_ranges(line)]
        offset += len(line) + 1
    assert bold_ranges(text) == by_line


# ---- The shape of the answer ----

MESSY = (
    "Hello, world! It's a well-known fact (see https://example.com/x) that "
    "internationalization costs 3 times more than don't-care attitudes; "
    "e.g. rock 'n' roll, state_of_the_art, O'Brien\u2014and \u041f\u0440\u0438\u0432\u0435\u0442 "
    "caf" + "e" + ACUTE + " " + EMOJI + " inter" + SOFT_HYPHEN + "national 1990's H2O."
)

def test_ranges_are_sorted_and_never_overlap():
    ranges = bold_ranges(MESSY)
    assert ranges
    previous_end = 0
    for start, end in ranges:
        assert previous_end <= start < end <= len(MESSY)
        previous_end = end

def test_every_range_starts_on_a_letter():
    for start, _ in bold_ranges(MESSY):
        assert MESSY[start].isalpha()

def test_the_same_text_always_gives_the_same_answer():
    assert bold_ranges(MESSY) == bold_ranges(MESSY)