import pytest
from core.orp import get_orp_index, get_orp_index_for_length, split_at_orp, ORPWord


# get_orp_index: exact boundary tests
# Synthetic "a" * n words guarantee each length is exactly what it claims
# to be. The boundaries are the whole behavior of this function, so using
# made-up words removes any risk of a miscounted real word giving a wrong
# expected value.

def test_orp_index_length_0_returns_0():
    assert get_orp_index("") == 0

def test_orp_index_length_1_returns_0():
    assert get_orp_index("a") == 0

def test_orp_index_length_2_returns_1():
    assert get_orp_index("aa") == 1

def test_orp_index_length_5_returns_1():
    assert get_orp_index("a" * 5) == 1

def test_orp_index_length_6_returns_2():
    # One letter past the first band boundary, from 5 to 6
    assert get_orp_index("a" * 6) == 2

def test_orp_index_length_9_returns_2():
    assert get_orp_index("a" * 9) == 2

def test_orp_index_length_10_returns_3():
    # One letter past the second band boundary, from 9 to 10
    assert get_orp_index("a" * 10) == 3

def test_orp_index_length_13_returns_3():
    assert get_orp_index("a" * 13) == 3

def test_orp_index_length_14_returns_4():
    # One letter past the third band boundary, from 13 to 14
    assert get_orp_index("a" * 14) == 4

def test_orp_index_very_long_word_still_returns_4():
    # The top band has no ceiling, so every word of 14 letters or more
    # lands on the same final index.
    assert get_orp_index("a" * 50) == 4


# get_orp_index_for_length: the same thresholds, applied to a length
# instead of a word. It exists so effective_pacing_length() in
# core/timing.py can band a padded length without duplicating these
# boundaries. The tests mirror the get_orp_index() ones above.

def test_orp_index_for_length_0_returns_0():
    assert get_orp_index_for_length(0) == 0

def test_orp_index_for_length_1_returns_0():
    assert get_orp_index_for_length(1) == 0

def test_orp_index_for_length_5_returns_1():
    assert get_orp_index_for_length(5) == 1

def test_orp_index_for_length_6_returns_2():
    assert get_orp_index_for_length(6) == 2

def test_orp_index_for_length_9_returns_2():
    assert get_orp_index_for_length(9) == 2

def test_orp_index_for_length_10_returns_3():
    assert get_orp_index_for_length(10) == 3

def test_orp_index_for_length_13_returns_3():
    assert get_orp_index_for_length(13) == 3

def test_orp_index_for_length_14_returns_4():
    assert get_orp_index_for_length(14) == 4

def test_orp_index_for_length_beyond_14_still_returns_4():
    assert get_orp_index_for_length(50) == 4

def test_orp_index_for_length_accepts_a_padded_length_beyond_any_real_word():
    # This is how effective_pacing_length() in core/timing.py uses it,
    # with a length larger than the word's own len() once hyphen bonuses
    # are added.
    assert get_orp_index_for_length(15) == 4


def test_get_orp_index_still_agrees_with_get_orp_index_for_length():
    # get_orp_index() is a thin wrapper around
    # get_orp_index_for_length(len(word)), so the two must always agree.
    words = ["", "a", "to", "about", "friendship", "understanding", "a" * 30]
    for word in words:
        assert get_orp_index(word) == get_orp_index_for_length(len(word))


# split_at_orp: before, focus and after on real words

def test_split_single_letter_word():
    assert split_at_orp("I") == ORPWord(before="", focus="I", after="")

def test_split_two_letter_word():
    assert split_at_orp("to") == ORPWord(before="t", focus="o", after="")

def test_split_five_letter_word():
    assert split_at_orp("about") == ORPWord(before="a", focus="b", after="out")

def test_split_word_with_trailing_punctuation():
    # tokenize() keeps punctuation attached to its word on purpose, and
    # split_at_orp treats it like any other character.
    assert split_at_orp("show.") == ORPWord(before="s", focus="h", after="ow.")

def test_split_reconstructs_original_word_exactly():
    # This must hold for every word, whatever its length or band. Joining
    # the three pieces back together always gives the original word, with
    # nothing dropped and nothing duplicated.
    words = ["I", "to", "about", "friendship", "understanding", "a" * 30]
    for word in words:
        result = split_at_orp(word)
        assert result.before + result.focus + result.after == word


# The empty string case

def test_split_at_orp_raises_clear_error_on_empty_string():
    """tokenize() never produces empty tokens, so this can't happen in the
    running app. Without this check, split_at_orp("") would fail with a
    confusing IndexError from indexing an empty string, so it raises a
    clear ValueError instead."""
    with pytest.raises(ValueError):
        split_at_orp("")