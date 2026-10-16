"""Tests for the reading-profile storage in SettingsStore: adding, updating,
renaming and deleting profiles, how they are saved to settings.json, and how
they travel in export bundles.

The rules about names and values live in core/profiles.py and are tested in
test_profiles.py. This file only checks that the store applies them and keeps
the results safe on disk."""

import json

import pytest

from core import data_bundle
from core.profiles import MAX_NAME_LENGTH, PROFILE_KEYS, ProfileError
from core.settings_store import AppSettings, SettingsStore
from core.transcript_store import TranscriptStore


@pytest.fixture
def store(tmp_path):
    return SettingsStore(settings_directory=str(tmp_path))


def _fast():
    return {"skip_word_count": 25, "warm_up_enabled": True, "length_pacing_enabled": True}


def _careful():
    return {"skip_word_count": 5, "pause_on_skip": True, "resume_rewind_words": 4}


def _full_values():
    """Every key a profile can hold, taken from the real defaults."""
    settings = AppSettings()
    return {key: getattr(settings, key) for key in PROFILE_KEYS}


def _settings_json(directory):
    return json.loads((directory / "settings.json").read_text(encoding="utf-8"))


# ---- A fresh store ----

def test_a_fresh_store_has_no_profiles(store):
    assert store.profiles == []

def test_a_fresh_app_settings_has_no_profiles():
    assert AppSettings().profiles == []

def test_two_app_settings_do_not_share_one_profile_list():
    first, second = AppSettings(), AppSettings()
    first.profiles.append({"name": "A", "values": {}})
    assert second.profiles == []


# ---- add_profile ----

def test_add_profile_saves_it_and_returns_it(store):
    profile = store.add_profile("Fast skim", _fast())
    assert profile.name == "Fast skim"
    assert profile.values == _fast()
    assert store.profiles == [profile]

def test_add_profile_tidies_the_name(store):
    profile = store.add_profile("  Fast   skim ", _fast())
    assert profile.name == "Fast skim"

def test_profiles_keep_the_order_they_were_added_in(store):
    store.add_profile("B", _fast())
    store.add_profile("A", _careful())
    assert [p.name for p in store.profiles] == ["B", "A"]

def test_add_profile_drops_values_a_profile_cannot_hold(store):
    profile = store.add_profile("Odd", {"skip_word_count": 12, "window_width": 1000, "guide_mark_color": "red"})
    assert profile.values == {"skip_word_count": 12}

def test_add_profile_drops_settings_that_belong_to_a_transcript(store):
    profile = store.add_profile("Odd", {"skip_word_count": 12, "wpm": 600, "font_size": 28})
    assert profile.values == {"skip_word_count": 12}

def test_add_profile_rejects_an_empty_name(store):
    with pytest.raises(ProfileError):
        store.add_profile("   ", _fast())
    assert store.profiles == []

def test_add_profile_rejects_a_name_that_is_too_long(store):
    with pytest.raises(ProfileError):
        store.add_profile("x" * (MAX_NAME_LENGTH + 1), _fast())
    assert store.profiles == []

def test_add_profile_rejects_a_duplicate_name_whatever_its_case(store):
    store.add_profile("Fast skim", _fast())
    with pytest.raises(ProfileError) as caught:
        store.add_profile("FAST SKIM", _careful())
    assert "Fast skim" in str(caught.value)
    assert [p.name for p in store.profiles] == ["Fast skim"]
    assert store.profiles[0].values == _fast()

def test_add_profile_stores_none_for_a_colour_that_follows_the_theme(store):
    profile = store.add_profile("Themed", {"guide_mark_color": None, "skip_word_count": 12})
    assert profile.values == {"guide_mark_color": None, "skip_word_count": 12}


# ---- get_profile and the copies the store hands out ----

def test_get_profile_finds_a_profile_by_name(store):
    store.add_profile("Fast skim", _fast())
    assert store.get_profile("Fast skim").values == _fast()

def test_get_profile_ignores_case_and_extra_spaces(store):
    store.add_profile("Fast skim", _fast())
    assert store.get_profile("  fast   SKIM ").name == "Fast skim"

def test_get_profile_returns_none_for_an_unknown_name(store):
    assert store.get_profile("Nope") is None
    assert store.get_profile("") is None
    assert store.get_profile(None) is None

def test_changing_a_returned_profile_does_not_change_the_store(store):
    store.add_profile("Fast skim", _fast())
    store.get_profile("Fast skim").values["skip_word_count"] = 1
    store.profiles[0].values["skip_word_count"] = 2
    assert store.get_profile("Fast skim").values["skip_word_count"] == 25

def test_changing_the_values_given_to_add_profile_does_not_change_the_store(store):
    values = _fast()
    store.add_profile("Fast skim", values)
    values["skip_word_count"] = 1
    assert store.get_profile("Fast skim").values["skip_word_count"] == 25


# ---- update_profile ----

def test_update_profile_replaces_the_values_and_keeps_name_and_place(store):
    store.add_profile("Fast skim", _fast())
    store.add_profile("Careful read", _careful())
    updated = store.update_profile("fast skim", {"skip_word_count": 30})
    assert updated.name == "Fast skim"
    assert [p.name for p in store.profiles] == ["Fast skim", "Careful read"]
    assert store.get_profile("Fast skim").values == {"skip_word_count": 30}

def test_update_profile_leaves_other_profiles_alone(store):
    store.add_profile("Fast skim", _fast())
    store.add_profile("Careful read", _careful())
    store.update_profile("Fast skim", {"skip_word_count": 30})
    assert store.get_profile("Careful read").values == _careful()

def test_update_profile_drops_values_a_profile_cannot_hold(store):
    store.add_profile("Fast skim", _fast())
    store.update_profile("Fast skim", {"skip_word_count": "many", "resume_rewind_words": 6})
    assert store.get_profile("Fast skim").values == {"resume_rewind_words": 6}

def test_update_profile_of_an_unknown_name_raises(store):
    with pytest.raises(ProfileError):
        store.update_profile("Nope", _fast())


# ---- rename_profile ----

def test_rename_profile_changes_the_name_and_keeps_values_and_place(store):
    store.add_profile("Fast skim", _fast())
    store.add_profile("Careful read", _careful())
    renamed = store.rename_profile("Fast skim", "Speed run")
    assert renamed.name == "Speed run"
    assert [p.name for p in store.profiles] == ["Speed run", "Careful read"]
    assert store.get_profile("Speed run").values == _fast()
    assert store.get_profile("Fast skim") is None

def test_rename_profile_may_change_only_the_capitals(store):
    store.add_profile("Fast skim", _fast())
    store.rename_profile("Fast skim", "FAST SKIM")
    assert [p.name for p in store.profiles] == ["FAST SKIM"]

def test_rename_profile_to_its_own_name_is_allowed(store):
    store.add_profile("Fast skim", _fast())
    store.rename_profile("Fast skim", "Fast skim")
    assert [p.name for p in store.profiles] == ["Fast skim"]

def test_rename_profile_onto_another_profiles_name_raises_and_changes_nothing(store):
    store.add_profile("Fast skim", _fast())
    store.add_profile("Careful read", _careful())
    with pytest.raises(ProfileError):
        store.rename_profile("Fast skim", "careful READ")
    assert [p.name for p in store.profiles] == ["Fast skim", "Careful read"]

def test_rename_profile_to_a_bad_name_raises_and_changes_nothing(store):
    store.add_profile("Fast skim", _fast())
    with pytest.raises(ProfileError):
        store.rename_profile("Fast skim", "")
    assert [p.name for p in store.profiles] == ["Fast skim"]

def test_rename_profile_of_an_unknown_name_raises(store):
    with pytest.raises(ProfileError):
        store.rename_profile("Nope", "Something")


# ---- delete_profile ----

def test_delete_profile_removes_only_that_profile(store):
    store.add_profile("Fast skim", _fast())
    store.add_profile("Careful read", _careful())
    store.delete_profile("fast skim")
    assert [p.name for p in store.profiles] == ["Careful read"]

def test_a_deleted_name_can_be_used_again(store):
    store.add_profile("Fast skim", _fast())
    store.delete_profile("Fast skim")
    store.add_profile("Fast skim", _careful())
    assert store.get_profile("Fast skim").values == _careful()

def test_delete_profile_of_an_unknown_name_raises(store):
    with pytest.raises(ProfileError):
        store.delete_profile("Nope")

def test_the_error_for_an_unknown_profile_names_it(store):
    with pytest.raises(ProfileError) as caught:
        store.delete_profile("Nope")
    assert "Nope" in str(caught.value)


# ---- Profile changes leave the other settings alone ----

def test_profile_changes_do_not_touch_other_settings(store):
    store.set_window_size(1200, 800)
    store.set_defaults(450, "#112233", "#445566", "#778899", 50)
    before = {key: getattr(store, key) for key in ("window_width", "window_height", "default_wpm",
                                                   "default_font_color", "default_font_size")}
    store.add_profile("Fast skim", _fast())
    store.update_profile("Fast skim", _careful())
    store.rename_profile("Fast skim", "Careful read")
    store.delete_profile("Careful read")
    after = {key: getattr(store, key) for key in before}
    assert after == before

def test_saving_a_profile_does_not_change_the_live_app_wide_settings(store):
    # Saving only records values. Putting them to use is a separate step.
    before = {key: getattr(store, key) for key in PROFILE_KEYS}
    store.add_profile("Fast skim", _fast())
    store.update_profile("Fast skim", _careful())
    assert {key: getattr(store, key) for key in PROFILE_KEYS} == before

def test_saving_other_settings_does_not_touch_profiles(store):
    store.add_profile("Fast skim", _fast())
    store.set_window_size(1200, 800)
    store.set_defaults(450, "#112233", "#445566", "#778899", 50)
    assert store.get_profile("Fast skim").values == _fast()


# ---- Saving and loading ----

def test_profiles_are_written_to_settings_json(store, tmp_path):
    store.add_profile("Fast skim", _fast())
    saved = _settings_json(tmp_path)
    assert saved["profiles"] == [{"name": "Fast skim", "values": _fast()}]

def test_every_kind_of_change_is_saved_straight_away(store, tmp_path):
    store.add_profile("Fast skim", _fast())
    store.add_profile("Careful read", _careful())
    store.update_profile("Fast skim", {"skip_word_count": 30})
    store.rename_profile("Careful read", "Slow")
    store.delete_profile("Fast skim")
    assert _settings_json(tmp_path)["profiles"] == [{"name": "Slow", "values": _careful()}]

def test_profiles_survive_a_restart(tmp_path):
    first = SettingsStore(settings_directory=str(tmp_path))
    first.add_profile("Fast skim", _fast())
    first.add_profile("Themed", {"guide_mark_color": None, "skip_word_count": 12})
    again = SettingsStore(settings_directory=str(tmp_path))
    assert [p.name for p in again.profiles] == ["Fast skim", "Themed"]
    assert again.get_profile("Fast skim").values == _fast()
    assert again.get_profile("Themed").values == {"guide_mark_color": None, "skip_word_count": 12}

def test_a_complete_profile_survives_a_restart_unchanged(tmp_path):
    first = SettingsStore(settings_directory=str(tmp_path))
    first.add_profile("Everything", _full_values())
    again = SettingsStore(settings_directory=str(tmp_path))
    assert again.get_profile("Everything").values == _full_values()

def test_a_settings_file_from_before_profiles_existed_loads_with_none(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"default_wpm": 450}), encoding="utf-8")
    loaded = SettingsStore(settings_directory=str(tmp_path))
    assert loaded.profiles == []
    assert loaded.default_wpm == 450


# ---- Damaged profiles in settings.json ----

def _write_settings(directory, **fields):
    (directory / "settings.json").write_text(json.dumps(fields), encoding="utf-8")

def test_a_bad_profile_entry_is_skipped_and_the_rest_still_load(tmp_path):
    _write_settings(tmp_path, default_wpm=450, profiles=[
        "junk",
        {"name": "Good", "values": {"skip_word_count": 12}},
        {"name": "", "values": {}},
        {"name": "No values"},
    ])
    loaded = SettingsStore(settings_directory=str(tmp_path))
    assert [p.name for p in loaded.profiles] == ["Good"]

def test_a_damaged_profile_does_not_reset_the_other_settings(tmp_path):
    # A failed load falls back to the defaults for everything, so a bad
    # profile must never be able to cause one.
    _write_settings(tmp_path, default_wpm=450, window_width=1234, profiles="not even a list")
    loaded = SettingsStore(settings_directory=str(tmp_path))
    assert loaded.default_wpm == 450
    assert loaded.window_width == 1234
    assert loaded.profiles == []

def test_invalid_values_inside_a_saved_profile_are_dropped_on_load(tmp_path):
    _write_settings(tmp_path, profiles=[
        {"name": "Mixed", "values": {"skip_word_count": 12, "guide_mark_color": "red",
                                     "made_up": 1, "pause_on_skip": 1}},
    ])
    loaded = SettingsStore(settings_directory=str(tmp_path))
    assert loaded.get_profile("Mixed").values == {"skip_word_count": 12}

def test_a_profile_saved_by_the_first_draft_loses_its_transcript_settings_on_load(tmp_path):
    _write_settings(tmp_path, profiles=[
        {"name": "Old", "values": {"wpm": 600, "font_size": 28, "skip_word_count": 25}},
    ])
    loaded = SettingsStore(settings_directory=str(tmp_path))
    assert loaded.get_profile("Old").values == {"skip_word_count": 25}

def test_names_that_differ_only_in_case_keep_the_first_on_load(tmp_path):
    _write_settings(tmp_path, profiles=[
        {"name": "Fast", "values": {"skip_word_count": 40}},
        {"name": "FAST", "values": {"skip_word_count": 10}},
    ])
    loaded = SettingsStore(settings_directory=str(tmp_path))
    assert [p.name for p in loaded.profiles] == ["Fast"]
    assert loaded.get_profile("fast").values == {"skip_word_count": 40}


# ---- Export and import bundles ----

@pytest.fixture
def stores(tmp_path):
    """A source and a destination pair of stores, in separate folders."""
    def make(label):
        return (TranscriptStore(data_directory=str(tmp_path / f"{label}_data")),
                SettingsStore(settings_directory=str(tmp_path / f"{label}_settings")))
    return make("src"), make("dst")


def _bundle_through_json(transcripts, settings):
    """Build a bundle and send it through real JSON text, the way the app
    does when it writes and reads an export file."""
    return data_bundle.parse_bundle(json.dumps(data_bundle.build_bundle(transcripts, settings)))


def test_export_settings_includes_the_profiles(store):
    store.add_profile("Fast skim", _fast())
    assert store.export_settings()["profiles"] == [{"name": "Fast skim", "values": _fast()}]

def test_the_exported_profiles_are_a_copy(store):
    store.add_profile("Fast skim", _fast())
    exported = store.export_settings()
    exported["profiles"][0]["values"]["skip_word_count"] = 1
    assert store.get_profile("Fast skim").values["skip_word_count"] == 25

def test_a_replace_import_brings_the_profiles_across(stores):
    (src_ts, src_ss), (dst_ts, dst_ss) = stores
    src_ss.add_profile("Fast skim", _fast())
    src_ss.add_profile("Themed", {"guide_mark_color": None})
    data_bundle.apply_bundle_replace(_bundle_through_json(src_ts, src_ss), dst_ts, dst_ss)
    assert [p.name for p in dst_ss.profiles] == ["Fast skim", "Themed"]
    assert dst_ss.get_profile("Themed").values == {"guide_mark_color": None}

def test_a_replace_import_overwrites_the_profiles_already_there(stores):
    (src_ts, src_ss), (dst_ts, dst_ss) = stores
    src_ss.add_profile("From the backup", _fast())
    dst_ss.add_profile("Already here", _careful())
    data_bundle.apply_bundle_replace(_bundle_through_json(src_ts, src_ss), dst_ts, dst_ss)
    assert [p.name for p in dst_ss.profiles] == ["From the backup"]

def test_a_replace_import_of_a_bundle_with_no_profiles_clears_them(stores):
    # The bundle does say "profiles": [], so replacing means replacing.
    (src_ts, src_ss), (dst_ts, dst_ss) = stores
    dst_ss.add_profile("Already here", _careful())
    data_bundle.apply_bundle_replace(_bundle_through_json(src_ts, src_ss), dst_ts, dst_ss)
    assert dst_ss.profiles == []

def test_a_bundle_from_before_profiles_existed_keeps_the_profiles_already_there(stores):
    (src_ts, src_ss), (dst_ts, dst_ss) = stores
    dst_ss.add_profile("Already here", _careful())
    bundle = _bundle_through_json(src_ts, src_ss)
    del bundle["settings"]["profiles"]
    data_bundle.apply_bundle_replace(bundle, dst_ts, dst_ss)
    assert [p.name for p in dst_ss.profiles] == ["Already here"]

def test_an_old_bundle_still_replaces_the_other_settings(stores):
    (src_ts, src_ss), (dst_ts, dst_ss) = stores
    src_ss.set_defaults(450, "#112233", "#445566", "#778899", 50)
    dst_ss.add_profile("Already here", _careful())
    bundle = _bundle_through_json(src_ts, src_ss)
    del bundle["settings"]["profiles"]
    data_bundle.apply_bundle_replace(bundle, dst_ts, dst_ss)
    assert dst_ss.default_wpm == 450

def test_a_damaged_profile_in_a_bundle_is_cleaned_on_import(stores):
    (src_ts, src_ss), (dst_ts, dst_ss) = stores
    bundle = _bundle_through_json(src_ts, src_ss)
    bundle["settings"]["profiles"] = [
        {"name": "Good", "values": {"skip_word_count": 12, "guide_mark_color": "red"}},
        "junk",
    ]
    data_bundle.apply_bundle_replace(bundle, dst_ts, dst_ss)
    assert [p.name for p in dst_ss.profiles] == ["Good"]
    assert dst_ss.get_profile("Good").values == {"skip_word_count": 12}

def test_imported_profiles_are_saved_to_disk(stores, tmp_path):
    (src_ts, src_ss), (dst_ts, dst_ss) = stores
    src_ss.add_profile("Fast skim", _fast())
    data_bundle.apply_bundle_replace(_bundle_through_json(src_ts, src_ss), dst_ts, dst_ss)
    again = SettingsStore(settings_directory=str(tmp_path / "dst_settings"))
    assert [p.name for p in again.profiles] == ["Fast skim"]

def test_an_expand_import_leaves_the_profiles_alone(stores):
    (src_ts, src_ss), (dst_ts, dst_ss) = stores
    src_ss.add_profile("From the backup", _fast())
    dst_ss.add_profile("Already here", _careful())
    data_bundle.apply_bundle_expand(_bundle_through_json(src_ts, src_ss), dst_ts)
    assert [p.name for p in dst_ss.profiles] == ["Already here"]