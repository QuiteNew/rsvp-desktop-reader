import pytest
from core.normalizer import normalize_transcript


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
])
def test_normalizing_twice_changes_nothing_more(text):
    once = normalize_transcript(text)
    assert normalize_transcript(once) == once