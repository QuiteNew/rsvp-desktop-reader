"""Tests for the bold word starts setting in SettingsStore: the one switch that
remembers whether the edit box shows the start of every word in bold.

Which letters get bold is tested in test_bold_starts.py. This file only checks
that the store keeps the switch, saves it, carries it in export bundles, and
keeps it out of reading profiles."""

import json

import pytest

from core.profiles import PROFILE_KEYS, value_is_valid
from core.settings_store import AppSettings, SettingsStore


@pytest.fixture
def store(tmp_path):
    return SettingsStore(settings_directory=str(tmp_path))


def _settings_json(directory):
    return json.loads((directory / "settings.json").read_text(encoding="utf-8"))


# ---- Defaults ----

def test_a_fresh_store_has_bold_starts_off(store):
    assert store.bold_starts_enabled is False

def test_a_fresh_store_matches_the_dataclass_default(store):
    assert store.bold_starts_enabled == AppSettings().bold_starts_enabled


# ---- The switch ----

def test_bold_starts_can_be_turned_on(store):
    store.set_bold_starts_enabled(True)
    assert store.bold_starts_enabled is True

def test_bold_starts_can_be_turned_off_again(store):
    store.set_bold_starts_enabled(True)
    store.set_bold_starts_enabled(False)
    assert store.bold_starts_enabled is False

def test_the_switch_does_not_touch_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 40)
    store.set_dyslexia_font_enabled(True)
    store.set_letter_spacing_level(2)
    store.set_bold_starts_enabled(True)
    assert store.default_wpm == 500
    assert store.default_font_size == 40
    assert store.dyslexia_font_enabled is True
    assert store.letter_spacing_level == 2

def test_other_settings_do_not_touch_the_switch(store):
    store.set_bold_starts_enabled(True)
    store.set_defaults(500, "#111111", "#222222", "#333333", 40)
    store.set_dyslexia_font_enabled(True)
    store.set_letter_spacing_level(2)
    assert store.bold_starts_enabled is True

def test_being_on_persists_and_reloads(tmp_path):
    first = SettingsStore(settings_directory=str(tmp_path))
    first.set_bold_starts_enabled(True)
    second = SettingsStore(settings_directory=str(tmp_path))
    assert second.bold_starts_enabled is True

def test_being_turned_off_again_persists_too(tmp_path):
    first = SettingsStore(settings_directory=str(tmp_path))
    first.set_bold_starts_enabled(True)
    first.set_bold_starts_enabled(False)
    second = SettingsStore(settings_directory=str(tmp_path))
    assert second.bold_starts_enabled is False


# ---- The file on disk ----

def test_the_switch_is_written_to_settings_json(tmp_path):
    store = SettingsStore(settings_directory=str(tmp_path))
    store.set_bold_starts_enabled(True)
    assert _settings_json(tmp_path)["bold_starts_enabled"] is True

def test_an_older_settings_file_without_it_loads_with_it_off(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"default_wpm": 450}), encoding="utf-8")
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.default_wpm == 450  # the rest of the file is still read
    assert store.bold_starts_enabled is False

def test_a_settings_file_that_has_it_on_is_read(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"bold_starts_enabled": True}), encoding="utf-8")
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.bold_starts_enabled is True

@pytest.mark.parametrize("damaged", ["yes", "true", "false", 1, 0, None, [], {}])
def test_only_a_real_true_turns_it_on(tmp_path, damaged):
    # A hand-edited or damaged file must not switch the look on by accident
    # ("false" written as text is still a non-empty string), and the rest of
    # the file is still read.
    (tmp_path / "settings.json").write_text(
        json.dumps({"default_wpm": 450, "bold_starts_enabled": damaged}), encoding="utf-8")
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.bold_starts_enabled is False
    assert store.default_wpm == 450


# ---- Export bundles ----

def test_the_export_includes_the_switch_even_when_it_is_off(store):
    assert store.export_settings()["bold_starts_enabled"] is False

def test_the_export_includes_the_switch_when_it_is_on(store):
    store.set_bold_starts_enabled(True)
    assert store.export_settings()["bold_starts_enabled"] is True

def test_a_replace_import_carries_the_switch_over(tmp_path):
    source = SettingsStore(settings_directory=str(tmp_path / "source"))
    source.set_bold_starts_enabled(True)
    target = SettingsStore(settings_directory=str(tmp_path / "target"))
    target.replace_from_bundle(source.export_settings())
    assert target.bold_starts_enabled is True

def test_a_bundle_from_before_the_switch_still_imports_and_leaves_it_off(tmp_path):
    older = SettingsStore(settings_directory=str(tmp_path / "older"))
    bundle = older.export_settings()
    del bundle["bold_starts_enabled"]
    target = SettingsStore(settings_directory=str(tmp_path / "target"))
    target.set_bold_starts_enabled(True)
    target.replace_from_bundle(bundle)
    assert target.bold_starts_enabled is False


# ---- Profiles ----

def test_the_switch_is_never_part_of_a_profile():
    # It is a look for the edit box, not a reading setting, and applying a
    # profile should not change what the draft looks like, so it stays out on
    # purpose.
    assert "bold_starts_enabled" not in PROFILE_KEYS
    assert not value_is_valid("bold_starts_enabled", True)

def test_a_profile_cannot_hold_the_switch_even_when_asked_to(store):
    profile = store.add_profile("Plain", {"bold_starts_enabled": True, "default_wpm": 300})
    assert profile.values == {"default_wpm": 300}