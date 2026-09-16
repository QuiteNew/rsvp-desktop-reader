from core.tokenizer import tokenize


def test_splits_simple_sentence_into_words():
    text = "Welcome to the show"
    assert tokenize(text) == ["Welcome", "to", "the", "show"]


def test_splits_on_multiple_spaces():
    text = "Hello    there     friend"
    assert tokenize(text) == ["Hello", "there", "friend"]


def test_splits_on_newlines_and_tabs():
    text = "Hello\nthere\tfriend"
    assert tokenize(text) == ["Hello", "there", "friend"]


def test_keeps_punctuation_attached_to_words():
    text = "Welcome to the show. Today we're talking about RSVP."
    assert tokenize(text) == ["Welcome", "to", "the", "show.", "Today", "we're", "talking", "about", "RSVP."]


def test_strips_leading_and_trailing_whitespace():
    text = "   Hello there friend   "
    assert tokenize(text) == ["Hello", "there", "friend"]


def test_single_word_returns_single_item_list():
    assert tokenize("Hello") == ["Hello"]


def test_empty_string_returns_empty_list():
    assert tokenize("") == []


def test_whitespace_only_string_returns_empty_list():
    assert tokenize("     ") == []