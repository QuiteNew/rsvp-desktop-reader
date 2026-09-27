import pytest
from core.normalizer import can_revert, normalize_transcript, toggle_normalization


# Markers that always count: each item becomes its own paragraph

def test_numbered_with_period():
    assert normalize_transcript("1. Buy milk\n2. Buy eggs") == "Buy milk\n\nBuy eggs"

def test_numbered_with_closing_parenthesis():
    assert normalize_transcript("1) First\n2) Second") == "First\n\nSecond"

def test_numbered_in_parentheses():
    assert normalize_transcript("(1) First\n(2) Second") == "First\n\nSecond"

def test_numbered_in_square_brackets():
    assert normalize_transcript("[1] First\n[2] Second") == "First\n\nSecond"

def test_numbered_with_colon():
    assert normalize_transcript("1: Intro\n2: Body") == "Intro\n\nBody"

def test_multilevel_numbers_with_a_closing_mark():
    assert normalize_transcript("1.3: Methods\n1.4. Results") == "Methods\n\nResults"

def test_dash_bullets():
    assert normalize_transcript("- Apples\n- Pears") == "Apples\n\nPears"

def test_star_bullets():
    assert normalize_transcript("* Apples\n* Pears") == "Apples\n\nPears"

def test_en_dash_bullets():
    assert normalize_transcript("– Apples\n– Pears") == "Apples\n\nPears"

def test_round_bullets():
    assert normalize_transcript("• Apples\n• Pears") == "Apples\n\nPears"

def test_bullet_symbols_in_the_middle_of_a_line_split_it():
    assert normalize_transcript("Fruits: • Apples • Pears") == "Fruits:\n\nApples\n\nPears"

def test_wrapped_list_item_is_joined_back_together():
    text = "1. A long item that\ncontinues here.\n2. Short."
    assert normalize_transcript(text) == "A long item that continues here.\n\nShort."

def test_marker_alone_on_its_line_takes_the_next_line_as_its_text():
    # Common in text copied out of a PDF.
    text = "1.\nFirst item\n2.\nSecond item"
    assert normalize_transcript(text) == "First item\n\nSecond item"

def test_list_right_after_an_intro_line():
    text = "Shopping list\n1. Milk\n2. Eggs"
    assert normalize_transcript(text) == "Shopping list\n\nMilk\n\nEggs"

def test_text_after_a_list_stays_its_own_paragraph():
    text = "- Milk\n- Eggs\n\nThat is all."
    assert normalize_transcript(text) == "Milk\n\nEggs\n\nThat is all."


# Letter, roman and bare decimal markers need at least two lines using them

def test_letter_markers():
    assert normalize_transcript("a) Apples\nb) Pears") == "Apples\n\nPears"

def test_lowercase_roman_markers():
    text = "i. Alpha\nii. Beta\niii. Gamma"
    assert normalize_transcript(text) == "Alpha\n\nBeta\n\nGamma"

def test_uppercase_roman_markers():
    assert normalize_transcript("I. Intro\nII. Body") == "Intro\n\nBody"

def test_bare_decimal_markers():
    assert normalize_transcript("1.1 Scope\n1.2 Terms") == "Scope\n\nTerms"

def test_single_letter_marker_is_left_alone():
    assert normalize_transcript("A. Smith said hello.") == "A. Smith said hello."

def test_initials_are_left_alone():
    assert normalize_transcript("I. M. Pei designed it.") == "I. M. Pei designed it."

def test_single_bare_decimal_is_left_alone():
    assert normalize_transcript("3.14 is roughly pi.") == "3.14 is roughly pi."

def test_each_kind_of_marker_is_counted_separately():
    # Two letter markers don't make a lone decimal count as a marker too.
    text = "a) Apples.\nb) Pears.\n3.14 is roughly pi."
    assert normalize_transcript(text) == "Apples.\n\nPears.\n3.14 is roughly pi."


# Things that look like markers but aren't

def test_four_digit_number_is_not_a_marker():
    assert normalize_transcript("1990. A good year.") == "1990. A good year."

def test_time_of_day_is_not_a_marker():
    assert normalize_transcript("10:30 we met.") == "10:30 we met."

def test_hyphen_inside_a_word_is_left_alone():
    assert normalize_transcript("A well-known fact.") == "A well-known fact."

def test_rows_of_decimal_numbers_are_not_markers():
    # Chart axis labels copied out of a PDF, not section numbers.
    text = "0.50 0.25 axis\n0.75 0.10 axis."
    assert normalize_transcript(text) == "0.50 0.25 axis 0.75 0.10 axis."

def test_sentences_inside_one_line_are_never_split():
    assert normalize_transcript("One. Two. Three. Four.") == "One. Two. Three. Four."


# Headings stay on their own line and are never joined to the next one

def test_part_heading():
    text = "Part 1: Introduction\nThis is text."
    assert normalize_transcript(text) == "Part 1: Introduction\n\nThis is text."

def test_chapter_heading_with_roman_numeral():
    assert normalize_transcript("Chapter IV\nIt was dark.") == "Chapter IV\n\nIt was dark."

def test_heading_is_not_joined_to_a_lowercase_line():
    text = "Section 2.1 Scope\nthe scope is small."
    assert normalize_transcript(text) == "Section 2.1 Scope\n\nthe scope is small."

def test_heading_word_without_a_number_is_ordinary_text():
    assert normalize_transcript("Part of the plan.") == "Part of the plan."


# Lines that are only a number are removed

def test_page_number_between_sentences_is_removed():
    text = "The end of page one.\n12\nThe next page."
    assert normalize_transcript(text) == "The end of page one.\nThe next page."

def test_page_number_in_the_middle_of_a_sentence_is_removed():
    assert normalize_transcript("the quick\n12\nbrown fox") == "the quick brown fox"


# Joining lines that were broken in the middle of a sentence

def test_line_continuing_in_lowercase_is_joined():
    text = "This sentence was\nbroken in the middle."
    assert normalize_transcript(text) == "This sentence was broken in the middle."

def test_line_after_a_comma_is_joined():
    assert normalize_transcript("First part,\nSecond part.") == "First part, Second part."

def test_line_after_a_full_stop_is_not_joined():
    assert normalize_transcript("One sentence.\nAnother one.") == "One sentence.\nAnother one."

def test_title_line_is_not_joined_to_the_text_below():
    text = "Introduction\nThis paper studies X."
    assert normalize_transcript(text) == "Introduction\nThis paper studies X."

def test_line_after_a_colon_is_not_joined():
    text = "Ingredients:\nflour and water."
    assert normalize_transcript(text) == "Ingredients:\nflour and water."

def test_line_starting_with_capital_i_is_not_joined():
    # A known limit: "I" can't be told apart from the start of a new
    # sentence, so this stays split.
    assert normalize_transcript("and then\nI went home.") == "and then\nI went home."

def test_subtitle_style_lines():
    text = "Hello world.\nand then we went\nto the store."
    assert normalize_transcript(text) == "Hello world.\nand then we went to the store."

def test_word_split_with_a_hyphen_is_joined_without_a_space():
    assert normalize_transcript("infor-\nmation overload") == "infor-mation overload"


# Tidying

def test_several_blank_lines_become_one():
    assert normalize_transcript("Para one.\n\n\n\nPara two.") == "Para one.\n\nPara two."

def test_runs_of_spaces_and_tabs_become_one_space():
    assert normalize_transcript("Too   many\t\tspaces.") == "Too many spaces."

def test_windows_line_endings():
    assert normalize_transcript("Line one.\r\nLine two.") == "Line one.\nLine two."

def test_empty_text():
    assert normalize_transcript("") == ""

def test_whitespace_only_text():
    assert normalize_transcript("  \n\n  ") == ""


# Repairing letters damaged by PDF extraction

def test_combined_letters_are_expanded():
    assert normalize_transcript("\ufb01nd the \ufb02ow") == "find the flow"

def test_lost_f_before_i_is_restored():
    assert normalize_transcript("de\ufffdined") == "defined"

def test_lost_f_before_l_is_restored():
    assert normalize_transcript("\ufffdlexibility") == "flexibility"

def test_lost_f_in_the_middle_of_ffi_is_restored():
    assert normalize_transcript("ef\ufffdicient") == "efficient"

def test_replacement_character_anywhere_else_is_left_alone():
    # There's no telling what letter it was, so it stays as it is.
    assert normalize_transcript("caf\ufffd au lait") == "caf\ufffd au lait"


# Timestamps

def test_bracketed_timestamp_is_removed():
    assert normalize_transcript("[00:01:23] Welcome to the show.") == "Welcome to the show."

def test_parenthesized_short_timestamp_is_removed():
    assert normalize_transcript("(1:23) Today we talk.") == "Today we talk."

def test_bare_hour_minute_second_timestamp_is_removed():
    assert normalize_transcript("00:02:45 rapid reading.") == "rapid reading."

def test_bare_time_of_day_is_left_alone():
    assert normalize_transcript("We met at 10:30 today.") == "We met at 10:30 today."

def test_line_holding_only_a_timestamp_does_not_split_a_sentence():
    assert normalize_transcript("the quick\n[00:01:00]\nbrown fox") == "the quick brown fox"

def test_removed_timestamp_does_not_strand_punctuation():
    # A removed timestamp shouldn't leave a lone comma that then gets
    # flashed as its own word while reading.
    assert normalize_transcript("text [00:01:23], more") == "text, more"

def test_parenthesised_timestamp_list_collapses_cleanly():
    text = "See ([00:01:23], (1:23), 00:02:45, the notes)"
    assert normalize_transcript(text) == "See (the notes)"

def test_pasted_subtitle_file_is_cleaned_up():
    text = (
        "1\n00:00:01,000 --> 00:00:04,000\nHello world.\n\n"
        "2\n00:00:04,500 --> 00:00:06,000\nand then we went\nto the store.\n"
    )
    assert normalize_transcript(text) == "Hello world.\n\nand then we went to the store."


# Lists that continue inside a single line

def test_numbered_run_inside_a_line_is_split():
    assert normalize_transcript("Steps: 1. Mix 2. Bake 3. Eat") == "Steps:\n\nMix\n\nBake\n\nEat"

def test_parenthesis_numbered_runs_can_restart_at_one():
    text = "Buy: 1) milk 2) eggs and 1) bread 2) jam"
    assert normalize_transcript(text) == "Buy:\n\nmilk\n\neggs and\n\nbread\n\njam"

def test_lone_number_with_a_period_is_left_alone():
    assert normalize_transcript("Version 2. Then we left.") == "Version 2. Then we left."

def test_numbers_that_do_not_count_up_from_one_are_left_alone():
    assert normalize_transcript("Priority 1. Then 3. later") == "Priority 1. Then 3. later"

def test_page_reference_is_not_taken_as_a_list_marker():
    text = "Tribune, December 16, 1992, p. 1. 2. J. W. Forrester"
    assert normalize_transcript(text) == text

def test_figure_references_are_not_taken_as_list_markers():
    assert normalize_transcript("See Fig. 1. and Fig. 2. for details.") == "See Fig. 1. and Fig. 2. for details."

def test_checkboxes_inside_a_line_split_it():
    assert normalize_transcript("[ ] todo one [x] done two") == "todo one\n\ndone two"

def test_checkboxes_at_the_start_of_lines():
    assert normalize_transcript("[X] Buy milk\n[ ] Buy eggs") == "Buy milk\n\nBuy eggs"

def test_checkbox_with_nothing_after_it_is_removed():
    assert normalize_transcript("the chaotic text block [X].") == "the chaotic text block."

def test_one_line_paste_with_checkboxes_and_empty_numbered_runs():
    # The kind of text that first showed these weren't handled: one
    # long line, checkboxes between sentences, and a run of numbers
    # with nothing after them.
    text = (
        "Frogs jump over mushrooms [X] Cats run past algorithms [X] "
        "Mice navigate labyrinths 1. 2. 3. 1) 2) 3) with words mixed together [X]."
    )
    expected = (
        "Frogs jump over mushrooms\n\n"
        "Cats run past algorithms\n\n"
        "Mice navigate labyrinths\n\n"
        "with words mixed together."
    )
    assert normalize_transcript(text) == expected


# Everything together

def test_messy_paste_with_several_problems_at_once():
    text = (
        "Part 1: Getting started\n"
        "Before you begin, make sure\n"
        "you have everything ready:\n"
        "1. A quiet room\n"
        "2. A transcript that was\n"
        "copied from a PDF\n"
        "3\n"
        "• Coffee • Patience\n"
        "\n"
        "That is all."
    )
    expected = (
        "Part 1: Getting started\n\n"
        "Before you begin, make sure you have everything ready:\n\n"
        "A quiet room\n\n"
        "A transcript that was copied from a PDF\n\n"
        "Coffee\n\n"
        "Patience\n\n"
        "That is all."
    )
    assert normalize_transcript(text) == expected


# Splitting a long wall of prose into paragraphs (opt-in, off by default)

_SENTENCE = "This is a sentence that carries a little weight and length. "  # ~59 chars


def test_splitting_is_off_by_default():
    wall = (_SENTENCE * 12).strip()
    assert normalize_transcript(wall) == wall
    assert normalize_transcript(wall, split_long_paragraphs=False) == wall


def test_a_long_wall_is_split_into_several_paragraphs():
    wall = (_SENTENCE * 12).strip()  # ~700 chars, 12 sentences
    out = normalize_transcript(wall, split_long_paragraphs=True)
    paragraphs = out.split("\n\n")
    assert len(paragraphs) > 1
    # only regrouped: no word is lost, added or reordered
    assert " ".join(paragraphs).split() == wall.split()


def test_splitting_a_wall_twice_changes_nothing_more():
    wall = (_SENTENCE * 12).strip()
    once = normalize_transcript(wall, split_long_paragraphs=True)
    assert normalize_transcript(once, split_long_paragraphs=True) == once


def test_a_short_paragraph_is_left_alone():
    text = "Short one. Short two. Short three. Short four."
    assert normalize_transcript(text, split_long_paragraphs=True) == text


def test_a_long_paragraph_of_two_sentences_is_left_alone():
    text = "A" * 300 + " ends here. " + "B" * 300 + " also ends here."
    assert normalize_transcript(text, split_long_paragraphs=True) == text


def test_a_long_run_on_with_no_sentence_end_is_left_alone():
    text = ("word " * 120).strip()  # ~600 chars, no . ! or ?
    assert normalize_transcript(text, split_long_paragraphs=True) == text


def test_a_quote_can_sit_at_a_sentence_end():
    pad = "Padding sentence to clear the length gate here. " * 8
    text = pad + 'He said "Hello." She left the room.'
    out = normalize_transcript(text, split_long_paragraphs=True)
    assert " ".join(out.split("\n\n")).split() == text.split()
    assert '"Hello."' in out


def test_never_splits_after_an_abbreviation_or_initial():
    part = ("The team at Google Inc. reviewed the U.S. data with Dr. Smith, e.g. the "
            "key trends noted earlier by J. W. Forrester. ")
    wall = (part * 5).strip()
    out = normalize_transcript(wall, split_long_paragraphs=True)
    paragraphs = out.split("\n\n")
    assert len(paragraphs) > 1  # it really did split
    for paragraph in paragraphs:
        ending = paragraph.rstrip().lower()
        for abbr in ("inc.", "u.s.", "dr.", "e.g.", "j.", "w."):
            assert not ending.endswith(abbr)


def test_never_splits_at_a_decimal_or_an_ellipsis():
    part = ("The reading covered pi is 3.14 in the notes and then continued for a "
            "while... eventually reaching a natural stopping point at last here. ")
    wall = (part * 5).strip()
    out = normalize_transcript(wall, split_long_paragraphs=True)
    for paragraph in out.split("\n\n"):
        stripped = paragraph.rstrip()
        assert not stripped.endswith("3.14")
        assert not stripped.endswith("...")


def test_splitting_runs_alongside_the_other_steps():
    # A wall that also carries a timestamp and a trailing numbered list.
    wall = "[00:00:05] " + (_SENTENCE * 10) + "Steps: 1. First 2. Second 3. Third"
    out = normalize_transcript(wall, split_long_paragraphs=True)
    assert "00:00:05" not in out          # timestamp gone
    assert "\n\nFirst\n\nSecond\n\nThird" in out  # list split out
    assert normalize_transcript(out, split_long_paragraphs=True) == out  # stable


# Normalizing twice gives the same result as normalizing once, so the
# button does nothing on text that's already normalized.

@pytest.mark.parametrize("text", [
    "1. Buy milk\n2. Buy eggs",
    "a) Apples\nb) Pears",
    "Fruits: • Apples • Pears",
    "1.\nFirst item\n2.\nSecond item",
    "Part 1: Introduction\nThis is text.",
    "the quick\n12\nbrown fox",
    "Hello world.\nand then we went\nto the store.",
    "infor-\nmation overload",
    "Para one.\n\n\n\nPara two.",
    "Part 1: Getting started\nBefore you begin, make sure\nyou have everything ready:\n1. A quiet room",
    "ef\ufffdicient \ufb02ow",
    # Stripping "12." exposes "0.50" at the start of a line; a second
    # pass must not then treat that as a marker too.
    "12. 0.50 0.25\n13. 0.75 0.10",
    "[00:01:23] Welcome.\n(1:23) Next.",
    "Steps: 1. Mix 2. Bake 3. Eat",
    # A run split inside the first line, then broken lines joined back
    # up, can line up a new run that only a second pass would split.
    "Intro 1. First item that\ncontinues 2. Second 3. Third",
    "Frogs [X] Cats [X] Mice 1. 2. 3. 1) 2) 3) words [X].",
    "text [00:01:23], more",
    "See ([00:01:23], (1:23), 00:02:45, the notes)",
])
def test_normalizing_twice_changes_nothing_more(text):
    once = normalize_transcript(text)
    assert normalize_transcript(once) == once


# can_revert: which icon the button shows

def test_can_revert_when_text_is_still_what_normalizing_produced():
    assert can_revert("Buy milk\n\nBuy eggs", "1. Buy milk\n2. Buy eggs", "Buy milk\n\nBuy eggs")

def test_can_revert_ignores_the_edit_boxs_trailing_newline():
    assert can_revert("Buy milk\n\nBuy eggs\n", "1. Buy milk\n2. Buy eggs", "Buy milk\n\nBuy eggs")

def test_cannot_revert_after_an_edit():
    assert not can_revert("Buy milk\n\nBuy bread", "1. Buy milk\n2. Buy eggs", "Buy milk\n\nBuy eggs")

def test_cannot_revert_with_nothing_saved():
    assert not can_revert("Buy milk", "", "")


# toggle_normalization: what one click does

def test_first_click_normalizes_and_remembers_the_original():
    result = toggle_normalization("1. Buy milk\n2. Buy eggs\n", "", "")
    assert result.text == "Buy milk\n\nBuy eggs"
    assert result.pre_normalize_text == "1. Buy milk\n2. Buy eggs"
    assert result.normalized_text == "Buy milk\n\nBuy eggs"

def test_second_click_reverts_and_forgets_the_original():
    first = toggle_normalization("1. Buy milk\n2. Buy eggs", "", "")
    second = toggle_normalization(first.text + "\n", first.pre_normalize_text, first.normalized_text)
    assert second.text == "1. Buy milk\n2. Buy eggs"
    assert second.pre_normalize_text == ""
    assert second.normalized_text == ""

def test_click_after_an_edit_normalizes_the_edited_text():
    # The old original is no longer offered; the edited text becomes
    # the new original.
    result = toggle_normalization("1. Buy bread", "1. Buy milk", "Buy milk")
    assert result.text == "Buy bread"
    assert result.pre_normalize_text == "1. Buy bread"
    assert result.normalized_text == "Buy bread"

def test_click_on_text_with_nothing_to_normalize_changes_nothing():
    result = toggle_normalization("Already tidy.\n", "", "")
    assert result.text == "Already tidy."
    assert result.pre_normalize_text == ""
    assert result.normalized_text == ""

def test_click_on_empty_text_changes_nothing():
    result = toggle_normalization("\n", "", "")
    assert result.text == ""
    assert result.pre_normalize_text == ""
    assert result.normalized_text == ""