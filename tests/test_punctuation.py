import pytest
from core.punctuation import (
    split_punctuation,
    classify_pacing,
    PACE_NONE,
    PACE_CLAUSE,
    PACE_SENTENCE,
)


# ---- split_punctuation: no punctuation ----

def test_split_punctuation_word_with_no_marks():
    assert split_punctuation("hello") == ("", "hello", "")

def test_split_punctuation_single_letter_word():
    assert split_punctuation("a") == ("", "a", "")


# ---- split_punctuation: leading and/or trailing marks ----

def test_split_punctuation_trailing_period():
    assert split_punctuation("show.") == ("", "show", ".")

def test_split_punctuation_leading_quote():
    assert split_punctuation('"hello') == ('"', "hello", "")

def test_split_punctuation_leading_and_trailing_marks():
    assert split_punctuation('"hello."') == ('"', "hello", '."')

def test_split_punctuation_multiple_marks_each_side():
    assert split_punctuation("...hello!!!") == ("...", "hello", "!!!")


# ---- split_punctuation: internal punctuation is left alone ----

def test_split_punctuation_leaves_internal_hyphen_untouched():
    # Only leading/trailing runs are stripped -- a hyphen in the middle
    # of a word is part of the word, not something to peel off.
    assert split_punctuation("well-known") == ("", "well-known", "")

def test_split_punctuation_leaves_internal_decimal_point_untouched():
    assert split_punctuation("$5.99") == ("$", "5.99", "")

def test_split_punctuation_leaves_internal_apostrophe_untouched():
    # The apostrophe sits between two alnum runs, so neither end-inward
    # scan ever reaches it -- only the surrounding quotes do.
    assert split_punctuation("\"don't\"") == ('"', "don't", '"')


# ---- split_punctuation: entirely punctuation ----

def test_split_punctuation_all_punctuation_token_has_empty_core():
    # No alnum character anywhere in the token -- core comes out empty
    # and the whole thing lands in leading, per the module's docstring.
    assert split_punctuation("--") == ("--", "", "")

def test_split_punctuation_single_mark_lands_in_leading():
    assert split_punctuation(".") == (".", "", "")


# ---- split_punctuation: the empty-string edge case ----

def test_split_punctuation_empty_string_returns_three_empty_strings():
    # tokenize() never produces empty tokens, so this never triggers in
    # the running app -- but both boundary scans stop immediately when
    # start == end == 0, so it degrades safely rather than raising.
    assert split_punctuation("") == ("", "", "")


# ---- split_punctuation: reconstructs the original token exactly ----

def test_split_punctuation_reconstructs_original_token_exactly():
    # A structural guarantee that must hold regardless of how the token
    # is split: the three pieces, concatenated back together, always
    # recover the original token exactly.
    tokens = ["hello", "show.", '"hello."', "...hello!!!", "well-known",
              "$5.99", "--", ".", ""]
    for token in tokens:
        leading, core, trailing = split_punctuation(token)
        assert leading + core + trailing == token


# ---- classify_pacing: sentence marks ----

def test_classify_pacing_period_is_sentence():
    assert classify_pacing(".") == PACE_SENTENCE

def test_classify_pacing_exclamation_is_sentence():
    assert classify_pacing("!") == PACE_SENTENCE

def test_classify_pacing_question_mark_is_sentence():
    assert classify_pacing("?") == PACE_SENTENCE


# ---- classify_pacing: clause marks ----

def test_classify_pacing_comma_is_clause():
    assert classify_pacing(",") == PACE_CLAUSE

def test_classify_pacing_semicolon_is_clause():
    assert classify_pacing(";") == PACE_CLAUSE

def test_classify_pacing_colon_is_clause():
    assert classify_pacing(":") == PACE_CLAUSE


# ---- classify_pacing: no pacing marks ----

def test_classify_pacing_empty_string_is_none():
    assert classify_pacing("") == PACE_NONE

def test_classify_pacing_quote_alone_is_none():
    # A quote mark isn't in either set -- not every leading/trailing
    # character should slow playback down.
    assert classify_pacing('"') == PACE_NONE

def test_classify_pacing_hyphen_alone_is_none():
    assert classify_pacing("-") == PACE_NONE


# ---- classify_pacing: combinations of marks ----

def test_classify_pacing_ellipsis_is_sentence():
    # "does any character match", not "does it end with exactly one
    # mark" -- three periods classify the same as one.
    assert classify_pacing("...") == PACE_SENTENCE

def test_classify_pacing_interrobang_is_sentence():
    assert classify_pacing("?!") == PACE_SENTENCE

def test_classify_pacing_closing_quote_after_period_is_sentence():
    assert classify_pacing('."') == PACE_SENTENCE

def test_classify_pacing_closing_quote_after_comma_is_clause():
    assert classify_pacing(',"') == PACE_CLAUSE

def test_classify_pacing_sentence_mark_wins_over_clause_mark():
    # Documented tie-break: if a token improbably carries both kinds of
    # mark, sentence pacing wins.
    assert classify_pacing(".,") == PACE_SENTENCE


# ---- classify_pacing: the all-punctuation-token case ----

def test_classify_pacing_handles_an_all_punctuation_token_via_leading():
    # split_punctuation("...") puts the whole token in `leading` with an
    # empty `trailing` (nothing to split an alnum core around -- see
    # test_split_punctuation_all_punctuation_token_has_empty_core).
    # Passing leading + trailing combined, not just trailing, is what
    # keeps a case like this from silently coming out as PACE_NONE.
    leading, core, trailing = split_punctuation("...")
    assert core == ""
    assert classify_pacing(leading + trailing) == PACE_SENTENCE