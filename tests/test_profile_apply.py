"""Tests for core/profile_apply.py, the pure step that works out what applying a
reading profile does: clamping numbers to the allowed ranges, filling in the
settings a profile leaves out, and resolving the guide mark colour against the
current theme."""

import dataclasses

import pytest

from core.profile_apply import NUMBER_RANGES, ProfilePlan, clamp_value, plan_profile
from core.profiles import PROFILE_KEYS, value_is_valid
from core.settings_store import (
    GUIDE_MARK_LENGTH_PERCENT_RANGE, GUIDE_MARK_THICKNESS_RANGE, HIGHLIGHT_OFFSET_RANGE,
    RESUME_REWIND_WORDS_RANGE, SKIP_WORD_COUNT_RANGE, AppSettings,
)

THEME_COLOUR = "#F2E8DC"


def _current():
    """The settings as they are on a fresh install."""
    settings = AppSettings()
    return {key: getattr(settings, key) for key in PROFILE_KEYS}


def _plan(profile_values, current=None, follows=True, theme=THEME_COLOUR):
    return plan_profile(profile_values, _current() if current is None else current, follows, theme)


# ---- The ranges agree with the real settings ----

def test_every_number_setting_has_a_range():
    number_keys = {key for key in PROFILE_KEYS
                   if isinstance(getattr(AppSettings(), key), int) and not isinstance(getattr(AppSettings(), key), bool)}
    assert number_keys == set(NUMBER_RANGES)

def test_only_profile_keys_have_a_range():
    assert set(NUMBER_RANGES) <= set(PROFILE_KEYS)

def test_the_ranges_are_the_ones_the_settings_window_uses():
    assert NUMBER_RANGES["highlight_offset_px"] == HIGHLIGHT_OFFSET_RANGE
    assert NUMBER_RANGES["guide_mark_thickness_px"] == GUIDE_MARK_THICKNESS_RANGE
    assert NUMBER_RANGES["guide_mark_length_percent"] == GUIDE_MARK_LENGTH_PERCENT_RANGE
    assert NUMBER_RANGES["resume_rewind_words"] == RESUME_REWIND_WORDS_RANGE
    assert NUMBER_RANGES["skip_word_count"] == SKIP_WORD_COUNT_RANGE

def test_every_range_has_a_low_below_its_high():
    for key, (low, high) in NUMBER_RANGES.items():
        assert low < high, key

def test_the_real_defaults_sit_inside_their_ranges():
    for key, (low, high) in NUMBER_RANGES.items():
        assert low <= getattr(AppSettings(), key) <= high, key


# ---- clamp_value ----

@pytest.mark.parametrize("key", sorted(NUMBER_RANGES))
def test_a_number_below_the_range_is_raised_to_the_low_end(key):
    low, _ = NUMBER_RANGES[key]
    assert clamp_value(key, low - 1000) == low

@pytest.mark.parametrize("key", sorted(NUMBER_RANGES))
def test_a_number_above_the_range_is_lowered_to_the_high_end(key):
    _, high = NUMBER_RANGES[key]
    assert clamp_value(key, high + 1000) == high

@pytest.mark.parametrize("key", sorted(NUMBER_RANGES))
def test_the_ends_of_the_range_are_allowed_as_they_are(key):
    low, high = NUMBER_RANGES[key]
    assert clamp_value(key, low) == low
    assert clamp_value(key, high) == high

def test_a_number_inside_the_range_is_left_alone():
    assert clamp_value("skip_word_count", 12) == 12
    assert clamp_value("highlight_offset_px", -2) == -2


# ---- plan_profile: numbers ----

def test_the_plan_clamps_numbers_from_the_profile():
    plan = _plan({"skip_word_count": 999, "highlight_offset_px": -50, "guide_mark_thickness_px": 1,
                  "guide_mark_length_percent": 100, "resume_rewind_words": 0})
    assert plan.values["skip_word_count"] == SKIP_WORD_COUNT_RANGE[1]
    assert plan.values["highlight_offset_px"] == HIGHLIGHT_OFFSET_RANGE[0]
    assert plan.values["guide_mark_thickness_px"] == GUIDE_MARK_THICKNESS_RANGE[0]
    assert plan.values["guide_mark_length_percent"] == GUIDE_MARK_LENGTH_PERCENT_RANGE[1]
    assert plan.values["resume_rewind_words"] == RESUME_REWIND_WORDS_RANGE[0]

def test_the_plan_keeps_numbers_that_are_in_range():
    plan = _plan({"skip_word_count": 25, "resume_rewind_words": 4})
    assert plan.values["skip_word_count"] == 25
    assert plan.values["resume_rewind_words"] == 4


# ---- plan_profile: switches ----

def test_the_plan_takes_switch_values_from_the_profile():
    plan = _plan({"warm_up_enabled": True, "pause_on_skip": True, "length_pacing_enabled": True,
                  "guide_mark_horizontal_enabled": True, "peripheral_context_enabled": True,
                  "resume_rewind_enabled": True})
    for key in ("warm_up_enabled", "pause_on_skip", "length_pacing_enabled",
                "guide_mark_horizontal_enabled", "peripheral_context_enabled", "resume_rewind_enabled"):
        assert plan.values[key] is True, key

def test_a_profile_can_switch_something_off():
    current = {**_current(), "warm_up_enabled": True}
    assert _plan({"warm_up_enabled": False}, current=current).values["warm_up_enabled"] is False


# ---- plan_profile: settings the profile leaves out ----

def test_the_plan_always_holds_every_profile_key():
    assert set(_plan({}).values) == set(PROFILE_KEYS)
    assert set(_plan({"skip_word_count": 25}).values) == set(PROFILE_KEYS)

def test_an_empty_profile_changes_nothing():
    current = {**_current(), "skip_word_count": 7, "warm_up_enabled": True, "guide_mark_color": "#112233"}
    plan = _plan({}, current=current, follows=False)
    assert plan.values == current
    assert plan.guide_mark_follows_theme is False

def test_settings_the_profile_leaves_out_keep_their_current_value():
    current = {**_current(), "skip_word_count": 7, "resume_rewind_words": 2, "pause_on_skip": True}
    plan = _plan({"skip_word_count": 25}, current=current)
    assert plan.values["skip_word_count"] == 25
    assert plan.values["resume_rewind_words"] == 2
    assert plan.values["pause_on_skip"] is True

def test_a_current_value_that_is_out_of_range_is_left_as_it_is_when_the_profile_leaves_it_out():
    # Only what a profile sets is clamped. Anything else is not this module's
    # business to change.
    current = {**_current(), "skip_word_count": 999}
    assert _plan({"warm_up_enabled": True}, current=current).values["skip_word_count"] == 999


# ---- plan_profile: junk in the profile ----

def test_a_value_of_the_wrong_kind_is_ignored_and_the_current_value_stays():
    current = {**_current(), "skip_word_count": 7, "pause_on_skip": True}
    plan = _plan({"skip_word_count": "many", "pause_on_skip": 0}, current=current)
    assert plan.values["skip_word_count"] == 7
    assert plan.values["pause_on_skip"] is True

def test_a_bool_is_not_accepted_as_a_number():
    current = {**_current(), "skip_word_count": 7}
    assert _plan({"skip_word_count": True}, current=current).values["skip_word_count"] == 7

def test_keys_that_are_not_part_of_a_profile_are_ignored():
    plan = _plan({"wpm": 600, "font_size": 28, "window_width": 1200, "skip_word_count": 25})
    assert set(plan.values) == set(PROFILE_KEYS)
    assert plan.values["skip_word_count"] == 25

def test_a_malformed_colour_is_ignored_and_the_current_colour_stays():
    current = {**_current(), "guide_mark_color": "#112233"}
    plan = _plan({"guide_mark_color": "red"}, current=current, follows=False)
    assert plan.values["guide_mark_color"] == "#112233"
    assert plan.guide_mark_follows_theme is False


# ---- plan_profile: the guide mark colour ----

def test_a_colour_that_followed_the_theme_gets_the_themes_colour_and_keeps_following():
    current = {**_current(), "guide_mark_color": "#112233"}
    plan = _plan({"guide_mark_color": None}, current=current, follows=False, theme="#F2E8DC")
    assert plan.values["guide_mark_color"] == "#F2E8DC"
    assert plan.guide_mark_follows_theme is True

def test_the_themes_colour_comes_from_the_caller_so_light_and_dark_differ():
    light = _plan({"guide_mark_color": None}, theme="#3B2E27")
    dark = _plan({"guide_mark_color": None}, theme="#F2E8DC")
    assert light.values["guide_mark_color"] == "#3B2E27"
    assert dark.values["guide_mark_color"] == "#F2E8DC"

def test_a_colour_picked_by_hand_is_applied_and_stops_following():
    plan = _plan({"guide_mark_color": "#AABBCC"}, follows=True)
    assert plan.values["guide_mark_color"] == "#AABBCC"
    assert plan.guide_mark_follows_theme is False

def test_a_hand_picked_colour_that_matches_the_theme_still_stops_following():
    plan = _plan({"guide_mark_color": THEME_COLOUR}, follows=True, theme=THEME_COLOUR)
    assert plan.values["guide_mark_color"] == THEME_COLOUR
    assert plan.guide_mark_follows_theme is False

@pytest.mark.parametrize("follows", [True, False])
def test_a_profile_without_a_colour_keeps_the_current_colour_and_whether_it_follows(follows):
    current = {**_current(), "guide_mark_color": "#112233"}
    plan = _plan({"skip_word_count": 25}, current=current, follows=follows)
    assert plan.values["guide_mark_color"] == "#112233"
    assert plan.guide_mark_follows_theme is follows

def test_the_resolved_colour_is_always_a_valid_colour():
    for profile in ({"guide_mark_color": None}, {"guide_mark_color": "#AABBCC"}, {}):
        assert value_is_valid("guide_mark_color", _plan(profile).values["guide_mark_color"])


# ---- plan_profile: the inputs and the result ----

def test_the_inputs_are_not_changed():
    profile = {"skip_word_count": 999, "guide_mark_color": None}
    current = {**_current(), "guide_mark_color": "#112233"}
    profile_before, current_before = dict(profile), dict(current)
    _plan(profile, current=current, follows=False)
    assert profile == profile_before
    assert current == current_before

def test_the_result_is_a_copy_of_the_current_settings():
    current = _current()
    plan = _plan({}, current=current)
    plan.values["skip_word_count"] = 1
    assert current["skip_word_count"] != 1

def test_a_current_dict_with_extra_keys_is_fine_and_they_are_left_out_of_the_plan():
    current = {**_current(), "window_width": 1000, "default_wpm": 300}
    assert set(_plan({}, current=current).values) == set(PROFILE_KEYS)

def test_a_current_dict_missing_a_key_raises():
    incomplete = _current()
    del incomplete["warm_up_enabled"]
    with pytest.raises(KeyError):
        _plan({}, current=incomplete)

def test_the_plan_cannot_be_changed_after_it_is_made():
    plan = _plan({})
    assert isinstance(plan, ProfilePlan)
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.guide_mark_follows_theme = False