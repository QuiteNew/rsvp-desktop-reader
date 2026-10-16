"""Tests for core/profiles.py, the pure rules behind reading profiles: which
settings a profile holds, what counts as a valid value, and what makes a good
name.

The first group guards the list of keys against the real settings classes, so
renaming a setting in AppSettings fails here instead of quietly leaving a
profile that no longer applies to anything. It also guards the line the feature
draws: a profile holds app-wide settings only, never anything that belongs to a
transcript or to the Defaults for new transcripts."""

import dataclasses

import pytest

from core import profiles
from core.models import Transcript
from core.profiles import (
    MAX_NAME_LENGTH, PROFILE_KEYS, THEME_COLOR_KEYS, Profile, build_values,
    clean_name, clean_profile_list, name_problem, profile_from_dict,
    sanitize_values, value_is_valid,
)
from core.settings_store import AppSettings


def _app_settings_fields():
    return {f.name for f in dataclasses.fields(AppSettings)}


def _transcript_fields():
    return {f.name for f in dataclasses.fields(Transcript)}


def _real_settings():
    """The app-wide settings as they are on a fresh install."""
    settings = AppSettings()
    return {key: getattr(settings, key) for key in PROFILE_KEYS}


# ---- The key list agrees with the real settings ----

def test_every_key_is_listed_once():
    assert len(PROFILE_KEYS) == len(set(PROFILE_KEYS))

def test_every_key_is_a_real_app_settings_field():
    assert set(PROFILE_KEYS) <= _app_settings_fields()

def test_theme_colour_keys_are_profile_keys():
    assert set(THEME_COLOR_KEYS) <= set(PROFILE_KEYS)

def test_the_real_defaults_are_all_valid_values():
    # If a default ever changes to a kind of value the profile rules don't
    # accept, this fails instead of the profile silently dropping it.
    for key, value in _real_settings().items():
        assert value_is_valid(key, value), key

def test_a_profile_never_holds_anything_that_belongs_to_a_transcript():
    assert not set(PROFILE_KEYS) & _transcript_fields()

def test_a_profile_never_holds_a_default_for_new_transcripts():
    assert not [key for key in PROFILE_KEYS if key.startswith("default_")]

def test_speed_look_and_chunking_are_not_part_of_a_profile():
    for key in ("wpm", "font_color", "highlight_color", "background_color", "font_size",
                "chunking_enabled", "chunk_size", "chunk_mode", "chunk_char_target"):
        assert key not in PROFILE_KEYS, key

def test_layout_theme_and_storage_settings_are_not_part_of_a_profile():
    for key in ("window_width", "window_height", "sidebar_width", "bottom_band_height",
                "freeform_resize_enabled", "data_directory", "appearance_mode",
                "split_long_paragraphs_enabled", "font_size_step", "scrub_pause_enabled"):
        assert key not in PROFILE_KEYS, key


# ---- Names ----

def test_clean_name_trims_and_squeezes_whitespace():
    assert clean_name("  Fast   skim \t") == "Fast skim"

def test_clean_name_of_something_that_is_not_text_is_empty():
    assert clean_name(None) == ""
    assert clean_name(42) == ""

def test_a_normal_name_has_no_problem():
    assert name_problem("Fast skim", []) is None

def test_an_empty_or_blank_name_is_rejected():
    assert name_problem("", []) is not None
    assert name_problem("   ", []) is not None

def test_a_name_at_the_length_limit_is_allowed_and_one_over_is_not():
    assert name_problem("x" * MAX_NAME_LENGTH, []) is None
    assert name_problem("x" * (MAX_NAME_LENGTH + 1), []) is not None

def test_length_is_measured_after_cleaning_the_name():
    padded = "  " + "x" * MAX_NAME_LENGTH + "  "
    assert name_problem(padded, []) is None

def test_a_name_with_an_unprintable_character_is_rejected():
    assert name_problem("Fast\x00skim", []) is not None

def test_a_duplicate_name_is_rejected_whatever_its_case():
    assert name_problem("fast skim", ["Fast skim"]) is not None
    assert name_problem("FAST  SKIM", ["Fast skim"]) is not None

def test_the_duplicate_message_names_the_existing_profile():
    assert "Fast skim" in name_problem("fast skim", ["Fast skim"])

def test_a_different_name_is_fine_next_to_existing_ones():
    assert name_problem("Careful read", ["Fast skim"]) is None

def test_a_profile_may_keep_its_own_name_when_renamed():
    assert name_problem("Fast skim", ["Fast skim"], own_name="Fast skim") is None

def test_a_profile_may_change_only_the_capitals_of_its_own_name():
    assert name_problem("FAST SKIM", ["Fast skim"], own_name="Fast skim") is None

def test_renaming_onto_another_profiles_name_is_still_rejected():
    assert name_problem("Careful read", ["Fast skim", "Careful read"], own_name="Fast skim") is not None


# ---- value_is_valid ----

def test_whole_numbers_are_valid_for_number_settings():
    assert value_is_valid("skip_word_count", 10)
    assert value_is_valid("highlight_offset_px", -2)

def test_a_bool_is_not_a_valid_number():
    assert not value_is_valid("skip_word_count", True)

def test_a_float_or_a_string_is_not_a_valid_number():
    assert not value_is_valid("skip_word_count", 10.0)
    assert not value_is_valid("skip_word_count", "10")

def test_true_and_false_are_valid_for_switches():
    assert value_is_valid("pause_on_skip", True)
    assert value_is_valid("pause_on_skip", False)

def test_a_number_is_not_a_valid_switch_value():
    assert not value_is_valid("pause_on_skip", 1)

def test_hex_colours_are_valid_in_either_case():
    assert value_is_valid("guide_mark_color", "#3B2E27")
    assert value_is_valid("guide_mark_color", "#3b2e27")

def test_malformed_colours_are_not_valid():
    for bad in ("3B2E27", "#3B2E2", "#3B2E277", "#GGGGGG", "red", "", 123):
        assert not value_is_valid("guide_mark_color", bad), bad

def test_none_is_valid_for_theme_colours_only():
    for key in THEME_COLOR_KEYS:
        assert value_is_valid(key, None), key
    assert not value_is_valid("skip_word_count", None)
    assert not value_is_valid("pause_on_skip", None)

def test_an_unknown_key_is_never_valid():
    assert not value_is_valid("window_width", 1000)
    assert not value_is_valid("wpm", 300)


# ---- sanitize_values ----

def test_sanitize_keeps_valid_values_unchanged():
    values = _real_settings()
    assert sanitize_values(values) == values

def test_sanitize_drops_unknown_keys():
    cleaned = sanitize_values({"skip_word_count": 10, "window_width": 1000, "made_up": 1, "wpm": 300})
    assert cleaned == {"skip_word_count": 10}

def test_sanitize_drops_values_of_the_wrong_kind():
    cleaned = sanitize_values({"skip_word_count": "many", "pause_on_skip": 1,
                               "guide_mark_color": "red", "resume_rewind_words": 4})
    assert cleaned == {"resume_rewind_words": 4}

def test_sanitize_keeps_none_for_a_theme_colour_but_not_for_anything_else():
    cleaned = sanitize_values({"guide_mark_color": None, "skip_word_count": None})
    assert cleaned == {"guide_mark_color": None}

def test_sanitize_of_something_that_is_not_a_dict_is_empty():
    for junk in (None, [], "text", 5):
        assert sanitize_values(junk) == {}

def test_sanitize_returns_keys_in_profile_order():
    values = {"pause_on_skip": True, "highlight_offset_px": 1}
    assert list(sanitize_values(values)) == ["highlight_offset_px", "pause_on_skip"]

def test_sanitize_does_not_change_the_dict_it_was_given():
    values = {"skip_word_count": "many", "resume_rewind_words": 4}
    sanitize_values(values)
    assert values == {"skip_word_count": "many", "resume_rewind_words": 4}


# ---- build_values ----

def test_build_values_holds_every_profile_key():
    assert set(build_values(_real_settings())) == set(PROFILE_KEYS)

def test_build_values_takes_each_value_from_the_input():
    given = {key: index for index, key in enumerate(PROFILE_KEYS)}
    assert build_values(given) == given

def test_build_values_ignores_keys_that_are_not_part_of_a_profile():
    # A whole settings dict can be passed in without filtering it first.
    given = {**_real_settings(), "window_width": 1234, "default_wpm": 999}
    assert set(build_values(given)) == set(PROFILE_KEYS)

def test_build_values_stores_none_for_a_colour_that_follows_the_theme():
    values = build_values(_real_settings(), following_theme=("guide_mark_color",))
    assert values["guide_mark_color"] is None

def test_build_values_keeps_a_colour_that_was_picked_by_hand():
    settings = {**_real_settings(), "guide_mark_color": "#112233"}
    assert build_values(settings)["guide_mark_color"] == "#112233"

def test_build_values_rejects_a_following_key_that_is_not_a_colour():
    with pytest.raises(ValueError):
        build_values(_real_settings(), following_theme=("skip_word_count",))

def test_build_values_raises_when_an_input_is_missing_a_key():
    incomplete = _real_settings()
    del incomplete["skip_word_count"]
    with pytest.raises(KeyError):
        build_values(incomplete)


# ---- Profile and loading ----

def test_profile_to_dict_gives_a_copy_of_the_values():
    profile = Profile("Fast skim", {"skip_word_count": 25})
    saved = profile.to_dict()
    saved["values"]["skip_word_count"] = 1
    assert profile.values == {"skip_word_count": 25}
    assert saved["name"] == "Fast skim"

def test_profile_from_dict_rebuilds_a_saved_profile():
    profile = profile_from_dict({"name": "  Fast   skim ", "values": {"skip_word_count": 25}})
    assert profile == Profile("Fast skim", {"skip_word_count": 25})

def test_profile_from_dict_drops_bad_entries_inside_the_values():
    profile = profile_from_dict({"name": "A", "values": {"skip_word_count": 25, "guide_mark_color": "red"}})
    assert profile.values == {"skip_word_count": 25}

def test_profile_from_dict_rejects_unusable_entries():
    assert profile_from_dict("text") is None
    assert profile_from_dict({"values": {}}) is None
    assert profile_from_dict({"name": "", "values": {}}) is None
    assert profile_from_dict({"name": "x" * (MAX_NAME_LENGTH + 1), "values": {}}) is None
    assert profile_from_dict({"name": "A", "values": "nope"}) is None
    assert profile_from_dict({"name": "A"}) is None

def test_clean_profile_list_keeps_good_profiles_in_order():
    raw = [{"name": "B", "values": {"skip_word_count": 20}}, {"name": "A", "values": {"skip_word_count": 30}}]
    assert clean_profile_list(raw) == raw

def test_clean_profile_list_skips_unusable_entries():
    raw = ["junk", None, {"name": "Good", "values": {"skip_word_count": 30}}, {"name": "", "values": {}}]
    assert clean_profile_list(raw) == [{"name": "Good", "values": {"skip_word_count": 30}}]

def test_clean_profile_list_keeps_the_first_of_two_names_that_differ_only_in_case():
    raw = [{"name": "Fast", "values": {"skip_word_count": 40}}, {"name": "FAST", "values": {"skip_word_count": 10}}]
    assert clean_profile_list(raw) == [{"name": "Fast", "values": {"skip_word_count": 40}}]

def test_clean_profile_list_of_something_that_is_not_a_list_is_empty():
    for junk in (None, {}, "text", 5):
        assert clean_profile_list(junk) == []

def test_clean_profile_list_returns_plain_dicts():
    cleaned = clean_profile_list([{"name": "A", "values": {"skip_word_count": 30}}])
    assert type(cleaned[0]) is dict
    assert type(cleaned[0]["values"]) is dict

def test_clean_profile_list_drops_settings_that_used_to_be_allowed():
    # Profiles saved by the first draft of this feature could hold speed, font
    # size and so on. They are ignored now, and the rest of the profile loads.
    raw = [{"name": "Old", "values": {"wpm": 600, "font_size": 28, "skip_word_count": 25}}]
    assert clean_profile_list(raw) == [{"name": "Old", "values": {"skip_word_count": 25}}]

def test_profile_error_is_a_value_error():
    assert issubclass(profiles.ProfileError, ValueError)