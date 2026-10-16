"""Tests for core/profiles.py, the pure rules behind reading profiles: which
settings a profile holds, what counts as a valid value, and what makes a good
name.

The first group guards the list of keys against the real settings classes, so
renaming a setting in AppSettings or Transcript fails here instead of quietly
leaving a profile that no longer applies to anything."""

import dataclasses

import pytest

from core import profiles
from core.models import Transcript
from core.profiles import (
    CHUNK_MODES, GLOBAL_KEYS, MAX_NAME_LENGTH, PER_TRANSCRIPT_KEYS, PROFILE_KEYS,
    THEME_COLOR_KEYS, Profile, build_values, clean_name, clean_profile_list,
    global_part, name_problem, per_transcript_part, profile_from_dict,
    sanitize_values, value_is_valid,
)
from core.settings_store import AppSettings


def _app_settings_fields():
    return {f.name for f in dataclasses.fields(AppSettings)}


def _transcript_fields():
    return {f.name for f in dataclasses.fields(Transcript)}


def _complete_values():
    """A full, valid set of profile values, built from the real defaults."""
    settings = AppSettings()
    transcript = Transcript(id=1, title="t", space="s")
    return build_values(
        {key: getattr(settings, key) for key in GLOBAL_KEYS},
        {key: getattr(transcript, key) for key in PER_TRANSCRIPT_KEYS},
    )


# ---- The key lists agree with the real settings ----

def test_every_key_is_listed_once():
    assert len(PROFILE_KEYS) == len(set(PROFILE_KEYS))

def test_per_transcript_and_global_keys_do_not_overlap():
    assert not set(PER_TRANSCRIPT_KEYS) & set(GLOBAL_KEYS)

def test_profile_keys_are_the_two_groups_together():
    assert set(PROFILE_KEYS) == set(PER_TRANSCRIPT_KEYS) | set(GLOBAL_KEYS)

def test_global_keys_are_real_app_settings_fields():
    assert set(GLOBAL_KEYS) <= _app_settings_fields()

def test_per_transcript_keys_are_real_transcript_fields():
    assert set(PER_TRANSCRIPT_KEYS) <= _transcript_fields()

def test_every_per_transcript_key_has_an_app_wide_default():
    # Applying a profile also sets what new transcripts start from, which is
    # AppSettings.default_<key> for each of these.
    for key in PER_TRANSCRIPT_KEYS:
        assert f"default_{key}" in _app_settings_fields(), key

def test_theme_colour_keys_are_profile_keys():
    assert set(THEME_COLOR_KEYS) <= set(PROFILE_KEYS)

def test_the_real_defaults_are_all_valid_values():
    # If a default ever changes to a kind of value the profile rules don't
    # accept, this fails instead of the profile silently dropping it.
    settings = AppSettings()
    transcript = Transcript(id=1, title="t", space="s")
    for key in GLOBAL_KEYS:
        assert value_is_valid(key, getattr(settings, key)), key
    for key in PER_TRANSCRIPT_KEYS:
        assert value_is_valid(key, getattr(transcript, key)), key
        assert value_is_valid(key, getattr(settings, f"default_{key}")), key

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
    assert value_is_valid("wpm", 300)
    assert value_is_valid("highlight_offset_px", -2)

def test_a_bool_is_not_a_valid_number():
    assert not value_is_valid("wpm", True)

def test_a_float_or_a_string_is_not_a_valid_number():
    assert not value_is_valid("wpm", 300.0)
    assert not value_is_valid("wpm", "300")

def test_true_and_false_are_valid_for_switches():
    assert value_is_valid("pause_on_skip", True)
    assert value_is_valid("pause_on_skip", False)

def test_a_number_is_not_a_valid_switch_value():
    assert not value_is_valid("pause_on_skip", 1)

def test_hex_colours_are_valid_in_either_case():
    assert value_is_valid("font_color", "#3B2E27")
    assert value_is_valid("font_color", "#3b2e27")

def test_malformed_colours_are_not_valid():
    for bad in ("3B2E27", "#3B2E2", "#3B2E277", "#GGGGGG", "red", "", 123):
        assert not value_is_valid("font_color", bad), bad

def test_none_is_valid_for_theme_colours_only():
    for key in THEME_COLOR_KEYS:
        assert value_is_valid(key, None), key
    assert not value_is_valid("wpm", None)
    assert not value_is_valid("pause_on_skip", None)

def test_chunk_mode_must_be_one_of_the_known_modes():
    for mode in CHUNK_MODES:
        assert value_is_valid("chunk_mode", mode)
    assert not value_is_valid("chunk_mode", "turbo")
    assert not value_is_valid("chunk_mode", None)

def test_an_unknown_key_is_never_valid():
    assert not value_is_valid("window_width", 1000)


# ---- sanitize_values ----

def test_sanitize_keeps_valid_values_unchanged():
    values = _complete_values()
    assert sanitize_values(values) == values

def test_sanitize_drops_unknown_keys():
    cleaned = sanitize_values({"wpm": 300, "window_width": 1000, "made_up": 1})
    assert cleaned == {"wpm": 300}

def test_sanitize_drops_values_of_the_wrong_kind():
    cleaned = sanitize_values({"wpm": "fast", "pause_on_skip": 1, "font_color": "red", "font_size": 40})
    assert cleaned == {"font_size": 40}

def test_sanitize_keeps_none_for_a_theme_colour_but_not_for_anything_else():
    cleaned = sanitize_values({"font_color": None, "wpm": None})
    assert cleaned == {"font_color": None}

def test_sanitize_of_something_that_is_not_a_dict_is_empty():
    for junk in (None, [], "text", 5):
        assert sanitize_values(junk) == {}

def test_sanitize_returns_keys_in_profile_order():
    values = {"skip_word_count": 5, "wpm": 400}
    assert list(sanitize_values(values)) == ["wpm", "skip_word_count"]

def test_sanitize_does_not_change_the_dict_it_was_given():
    values = {"wpm": "fast", "font_size": 40}
    sanitize_values(values)
    assert values == {"wpm": "fast", "font_size": 40}


# ---- build_values ----

def test_build_values_holds_every_profile_key():
    assert set(_complete_values()) == set(PROFILE_KEYS)

def test_build_values_takes_each_key_from_the_right_input():
    values = build_values(
        {key: "global" for key in GLOBAL_KEYS},
        {key: "transcript" for key in PER_TRANSCRIPT_KEYS},
    )
    assert all(values[key] == "global" for key in GLOBAL_KEYS)
    assert all(values[key] == "transcript" for key in PER_TRANSCRIPT_KEYS)

def test_build_values_stores_none_for_colours_that_follow_the_theme():
    settings = AppSettings()
    transcript = Transcript(id=1, title="t", space="s")
    values = build_values(
        {key: getattr(settings, key) for key in GLOBAL_KEYS},
        {key: getattr(transcript, key) for key in PER_TRANSCRIPT_KEYS},
        following_theme=("font_color", "guide_mark_color"),
    )
    assert values["font_color"] is None
    assert values["guide_mark_color"] is None
    assert values["highlight_color"] == transcript.highlight_color  # picked by hand: kept

def test_build_values_rejects_a_following_key_that_is_not_a_colour():
    settings = AppSettings()
    transcript = Transcript(id=1, title="t", space="s")
    with pytest.raises(ValueError):
        build_values(
            {key: getattr(settings, key) for key in GLOBAL_KEYS},
            {key: getattr(transcript, key) for key in PER_TRANSCRIPT_KEYS},
            following_theme=("wpm",),
        )

def test_build_values_raises_when_an_input_is_missing_a_key():
    settings = AppSettings()
    global_values = {key: getattr(settings, key) for key in GLOBAL_KEYS}
    with pytest.raises(KeyError):
        build_values(global_values, {})


# ---- The two parts ----

def test_global_part_and_per_transcript_part_split_the_values_cleanly():
    values = _complete_values()
    assert set(global_part(values)) == set(GLOBAL_KEYS)
    assert set(per_transcript_part(values)) == set(PER_TRANSCRIPT_KEYS)

def test_the_parts_only_include_keys_the_profile_actually_has():
    values = {"wpm": 400, "skip_word_count": 5}
    assert per_transcript_part(values) == {"wpm": 400}
    assert global_part(values) == {"skip_word_count": 5}

def test_the_parts_of_an_empty_profile_are_empty():
    assert global_part({}) == {}
    assert per_transcript_part({}) == {}


# ---- Profile and loading ----

def test_profile_to_dict_gives_a_copy_of_the_values():
    profile = Profile("Fast skim", {"wpm": 600})
    saved = profile.to_dict()
    saved["values"]["wpm"] = 1
    assert profile.values == {"wpm": 600}
    assert saved["name"] == "Fast skim"

def test_profile_from_dict_rebuilds_a_saved_profile():
    profile = profile_from_dict({"name": "  Fast   skim ", "values": {"wpm": 600}})
    assert profile == Profile("Fast skim", {"wpm": 600})

def test_profile_from_dict_drops_bad_entries_inside_the_values():
    profile = profile_from_dict({"name": "A", "values": {"wpm": 600, "font_color": "red"}})
    assert profile.values == {"wpm": 600}

def test_profile_from_dict_rejects_unusable_entries():
    assert profile_from_dict("text") is None
    assert profile_from_dict({"values": {}}) is None
    assert profile_from_dict({"name": "", "values": {}}) is None
    assert profile_from_dict({"name": "x" * (MAX_NAME_LENGTH + 1), "values": {}}) is None
    assert profile_from_dict({"name": "A", "values": "nope"}) is None
    assert profile_from_dict({"name": "A"}) is None

def test_clean_profile_list_keeps_good_profiles_in_order():
    raw = [{"name": "B", "values": {"wpm": 200}}, {"name": "A", "values": {"wpm": 300}}]
    assert clean_profile_list(raw) == raw

def test_clean_profile_list_skips_unusable_entries():
    raw = ["junk", None, {"name": "Good", "values": {"wpm": 300}}, {"name": "", "values": {}}]
    assert clean_profile_list(raw) == [{"name": "Good", "values": {"wpm": 300}}]

def test_clean_profile_list_keeps_the_first_of_two_names_that_differ_only_in_case():
    raw = [{"name": "Fast", "values": {"wpm": 600}}, {"name": "FAST", "values": {"wpm": 100}}]
    assert clean_profile_list(raw) == [{"name": "Fast", "values": {"wpm": 600}}]

def test_clean_profile_list_of_something_that_is_not_a_list_is_empty():
    for junk in (None, {}, "text", 5):
        assert clean_profile_list(junk) == []

def test_clean_profile_list_returns_plain_dicts():
    cleaned = clean_profile_list([{"name": "A", "values": {"wpm": 300}}])
    assert type(cleaned[0]) is dict
    assert type(cleaned[0]["values"]) is dict

def test_profile_error_is_a_value_error():
    assert issubclass(profiles.ProfileError, ValueError)