"""Tests for the pure Settings search rule in core/settings_search.py: how a
typed query is split into words and when a setting counts as a match."""

from core.settings_search import matches, query_words


def test_blank_query_matches_everything():
    assert matches("", "Speed") is True
    assert matches("   ", "Speed") is True
    assert matches("", "") is True


def test_query_words_are_lowercase_and_split_on_any_whitespace():
    assert query_words("  Guide   MARK\tcolour ") == ["guide", "mark", "colour"]
    assert query_words("") == []
    assert query_words("   ") == []


def test_matching_ignores_case_on_both_sides():
    assert matches("SPEED", "Speed") is True
    assert matches("speed", "SPEED") is True


def test_a_word_can_be_the_start_or_middle_of_a_longer_one():
    assert matches("guid", "Mark colour", keywords="guide marks") is True
    assert matches("ark", "Mark colour") is True


def test_every_word_must_be_found_in_any_order():
    assert matches("colour mark", "Mark colour") is True
    assert matches("mark colour", "Mark colour") is True
    assert matches("mark speed", "Mark colour") is False


def test_words_can_be_found_across_the_name_and_the_keywords():
    assert matches("highlight crosshair", "Show horizontal guide lines", keywords="crosshair highlight") is True
    assert matches("horizontal crosshair", "Show horizontal guide lines", keywords="crosshair") is True


def test_keywords_are_searched_even_when_descriptions_are_off():
    assert matches("crosshair", "Show horizontal guide lines", keywords="crosshair") is True


def test_description_is_ignored_unless_asked_for():
    description = "Starts each session at about half speed."
    assert matches("half", "Ease in", description=description) is False
    assert matches("half", "Ease in", description=description, include_description=False) is False


def test_description_is_searched_when_asked_for():
    description = "Starts each session at about half speed."
    assert matches("half", "Ease in", description=description, include_description=True) is True
    # Name and description together can satisfy a multi-word query.
    assert matches("ease half", "Ease in", description=description, include_description=True) is True


def test_a_word_missing_everywhere_is_no_match_even_with_descriptions_on():
    assert matches("zebra", "Ease in", keywords="warm up", description="Starts slower.", include_description=True) is False


def test_extra_spaces_between_words_do_not_matter():
    assert matches("  mark     colour  ", "Mark colour") is True


def test_a_query_word_cannot_match_across_the_gap_between_fields():
    # The name ends in "mark" and the keywords start with "colour"; a single
    # word "markcolour" must not be found by gluing them together.
    assert matches("markcolour", "Mark", keywords="colour") is False


def test_empty_optional_fields_are_fine():
    assert matches("speed", "Speed", keywords="", description="") is True
    assert matches("speed", "Speed", include_description=True) is True