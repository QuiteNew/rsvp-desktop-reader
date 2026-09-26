import pytest
from core.punctuation import (
    split_punctuation,
    classify_pacing,
    PACE_NONE,
    PACE_CLAUSE,
    PACE_SENTENCE,
)


# split_punctuation: no punctuation

def test_split_punctuation_word_with_no_marks():
    assert split_punctuation("hello") == ("", "hello", "")

def test_split_punctuation_single_letter_word():
    assert split_punctuation("a") == ("", "a", "")


# split_punctuation: leading and trailing marks

def test_split_punctuation_trailing_period():
    assert split_punctuation("show.") == ("", "show", ".")

def test_split_punctuation_leading_quote():
    assert split_punctuation('"hello') == ('"', "hello", "")

def test_split_punctuation_leading_and_trailing_marks():
    assert split_punctuation('"hello."') == ('"', "hello", '."')

def test_split_punctuation_multiple_marks_each_side():
    assert split_punctuation("...hello!!!") == ("...", "hello", "!!!")


# split_punctuation: punctuation inside a word is left alone

def test_split_punctuation_leaves_internal_hyphen_untouched():
    # Only the runs at the start and end are stripped. A hyphen in the
    # middle of a word is part of the word.
    assert split_punctuation("well-known") == ("", "well-known", "")

def test_split_punctuation_leaves_internal_decimal_point_untouched():
    assert split_punctuation("$5.99") == ("$", "5.99", "")

def test_split_punctuation_leaves_internal_apostrophe_untouched():
    # The apostrophe sits between letters, so the scans from either end
    # never reach it. Only the surrounding quotes are split off.
    assert split_punctuation("\"don't\"") == ('"', "don't", '"')


# split_punctuation: tokens made only of punctuation

def test_split_punctuation_all_punctuation_token_has_empty_core():
    # There are no letters or digits, so the core is empty and the whole
    # token goes into leading, as the module docstring describes.
    assert split_punctuation("--") == ("--", "", "")

def test_split_punctuation_single_mark_lands_in_leading():
    assert split_punctuation(".") == (".", "", "")


# split_punctuation: the empty string

def test_split_punctuation_empty_string_returns_three_empty_strings():
    # tokenize() never produces empty tokens, so this can't happen in the
    # running app. Both scans stop right away on an empty string, so it
    # returns empty pieces instead of raising.
    assert split_punctuation("") == ("", "", "")


# split_punctuation: the pieces rebuild the original token

def test_split_punctuation_reconstructs_original_token_exactly():
    # However the token is split, joining the three pieces back together
    # must always give the original token.
    tokens = ["hello", "show.", '"hello."', "...hello!!!", "well-known",
              "$5.99", "--", ".", ""]
    for token in tokens:
        leading, core, trailing = split_punctuation(token)
        assert leading + core + trailing == token


# classify_pacing: sentence marks

def test_classify_pacing_period_is_sentence():
    assert classify_pacing(".") == PACE_SENTENCE

def test_classify_pacing_exclamation_is_sentence():
    assert classify_pacing("!") == PACE_SENTENCE

def test_classify_pacing_question_mark_is_sentence():
    assert classify_pacing("?") == PACE_SENTENCE


# classify_pacing: clause marks

def test_classify_pacing_comma_is_clause():
    assert classify_pacing(",") == PACE_CLAUSE

def test_classify_pacing_semicolon_is_clause():
    assert classify_pacing(";") == PACE_CLAUSE

def test_classify_pacing_colon_is_clause():
    assert classify_pacing(":") == PACE_CLAUSE


# classify_pacing: marks that don't affect pacing

def test_classify_pacing_empty_string_is_none():
    assert classify_pacing("") == PACE_NONE

def test_classify_pacing_quote_alone_is_none():
    # A quote mark isn't in either set, since not every leading or
    # trailing character should slow playback down.
    assert classify_pacing('"') == PACE_NONE

def test_classify_pacing_hyphen_alone_is_none():
    assert classify_pacing("-") == PACE_NONE


# classify_pacing: combinations of marks

def test_classify_pacing_ellipsis_is_sentence():
    # The check is whether any character matches, not whether the token
    # ends with exactly one mark, so three periods count the same as one.
    assert classify_pacing("...") == PACE_SENTENCE

def test_classify_pacing_interrobang_is_sentence():
    assert classify_pacing("?!") == PACE_SENTENCE

def test_classify_pacing_closing_quote_after_period_is_sentence():
    assert classify_pacing('."') == PACE_SENTENCE

def test_classify_pacing_closing_quote_after_comma_is_clause():
    assert classify_pacing(',"') == PACE_CLAUSE

def test_classify_pacing_sentence_mark_wins_over_clause_mark():
    # If a token has both kinds of mark, sentence pacing wins.
    assert classify_pacing(".,") == PACE_SENTENCE


# classify_pacing: tokens made only of punctuation

def test_classify_pacing_handles_an_all_punctuation_token_via_leading():
    # split_punctuation("...") puts the whole token in leading and leaves
    # trailing empty, since there's no core to split around. Passing
    # leading + trailing together, not just trailing, is what stops a
    # case like this from quietly coming out as PACE_NONE.
    leading, core, trailing = split_punctuation("...")
    assert core == ""
    assert classify_pacing(leading + trailing) == PACE_SENTENCE