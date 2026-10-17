"""Tests for the two dyslexia-friendly settings in SettingsStore: the font switch
and the letter spacing level.

The gap sizes behind each level are tested in test_letter_spacing.py. This file
only checks that the store keeps the two settings, saves them, and carries them
in export bundles."""

import json

import pytest

from core.letter_spacing import LEVEL_NAMES, MAX_LEVEL
from core.profiles import PROFILE_KEYS
from core.settings_store import LETTER_SPACING_LEVEL_RANGE, AppSettings, SettingsStore


@pytest.fixture
def store(tmp_path):
    return SettingsStore(settings_directory=str(tmp_path))


def _settings_json(directory):
    return json.loads((directory / "settings.json").read_text(encoding="utf-8"))


# ---- Defaults ----

def test_a_fresh_store_has_the_dyslexia_font_off(store):
    assert store.dyslexia_font_enabled is False

def test_a_fresh_store_has_letter_spacing_off(store):
    assert store.letter_spacing_level == 0

def test_a_fresh_store_matches_the_dataclass_defaults(store):
    defaults = AppSettings()
    assert store.dyslexia_font_enabled == defaults.dyslexia_font_enabled
    assert store.letter_spacing_level == defaults.letter_spacing_level


# ---- The range ----

def test_the_range_runs_from_off_to_the_top_level_of_letter_spacing():
    assert LETTER_SPACING_LEVEL_RANGE == (0, MAX_LEVEL)

def test_every_level_in_the_range_has_a_name():
    low, high = LETTER_SPACING_LEVEL_RANGE
    assert len(LEVEL_NAMES) == high - low + 1

def test_the_default_level_is_inside_the_range():
    low, high = LETTER_SPACING_LEVEL_RANGE
    assert low <= AppSettings().letter_spacing_level <= high


# ---- The font switch ----

def test_the_dyslexia_font_can_be_turned_on(store):
    store.set_dyslexia_font_enabled(True)
    assert store.dyslexia_font_enabled is True

def test_the_dyslexia_font_can_be_turned_off_again(store):
    store.set_dyslexia_font_enabled(True)
    store.set_dyslexia_font_enabled(False)
    assert store.dyslexia_font_enabled is False

def test_the_dyslexia_font_switch_does_not_touch_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 40)
    store.set_letter_spacing_level(2)
    store.set_dyslexia_font_enabled(True)
    assert store.default_wpm == 500
    assert store.default_font_size == 40
    assert store.letter_spacing_level == 2

def test_the_dyslexia_font_persists_and_reloads(tmp_path):
    first = SettingsStore(settings_directory=str(tmp_path))
    first.set_dyslexia_font_enabled(True)
    second = SettingsStore(settings_directory=str(tmp_path))
    assert second.dyslexia_font_enabled is True


# ---- Letter spacing ----

@pytest.mark.parametrize("level", range(LETTER_SPACING_LEVEL_RANGE[1] + 1))
def test_every_level_can_be_set(store, level):
    store.set_letter_spacing_level(level)
    assert store.letter_spacing_level == level

def test_letter_spacing_can_be_turned_back_off(store):
    store.set_letter_spacing_level(3)
    store.set_letter_spacing_level(0)
    assert store.letter_spacing_level == 0

def test_letter_spacing_does_not_touch_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 40)
    store.set_dyslexia_font_enabled(True)
    store.set_letter_spacing_level(3)
    assert store.default_wpm == 500
    assert store.default_font_size == 40
    assert store.dyslexia_font_enabled is True

def test_letter_spacing_persists_and_reloads(tmp_path):
    first = SettingsStore(settings_directory=str(tmp_path))
    first.set_letter_spacing_level(2)
    second = SettingsStore(settings_directory=str(tmp_path))
    assert second.letter_spacing_level == 2


# ---- The file on disk ----

def test_both_settings_are_written_to_settings_json(tmp_path):
    store = SettingsStore(settings_directory=str(tmp_path))
    store.set_dyslexia_font_enabled(True)
    store.set_letter_spacing_level(1)
    saved = _settings_json(tmp_path)
    assert saved["dyslexia_font_enabled"] is True
    assert saved["letter_spacing_level"] == 1

def test_an_older_settings_file_without_them_loads_with_the_defaults(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"default_wpm": 450}), encoding="utf-8")
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.default_wpm == 450  # the rest of the file is still read
    assert store.dyslexia_font_enabled is False
    assert store.letter_spacing_level == 0

def test_a_settings_file_that_has_them_is_read(tmp_path):
    (tmp_path / "settings.json").write_text(
        json.dumps({"dyslexia_font_enabled": True, "letter_spacing_level": 3}), encoding="utf-8")
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.dyslexia_font_enabled is True
    assert store.letter_spacing_level == 3


# ---- Export bundles ----

def test_the_export_includes_both_settings(store):
    store.set_dyslexia_font_enabled(True)
    store.set_letter_spacing_level(2)
    exported = store.export_settings()
    assert exported["dyslexia_font_enabled"] is True
    assert exported["letter_spacing_level"] == 2

def test_a_replace_import_carries_both_settings_over(tmp_path):
    source = SettingsStore(settings_directory=str(tmp_path / "source"))
    source.set_dyslexia_font_enabled(True)
    source.set_letter_spacing_level(3)
    target = SettingsStore(settings_directory=str(tmp_path / "target"))
    target.replace_from_bundle(source.export_settings())
    assert target.dyslexia_font_enabled is True
    assert target.letter_spacing_level == 3

def test_a_bundle_from_before_these_settings_still_imports_and_leaves_the_defaults(tmp_path):
    older = SettingsStore(settings_directory=str(tmp_path / "older"))
    bundle = older.export_settings()
    del bundle["dyslexia_font_enabled"]
    del bundle["letter_spacing_level"]
    target = SettingsStore(settings_directory=str(tmp_path / "target"))
    target.set_dyslexia_font_enabled(True)
    target.set_letter_spacing_level(2)
    target.replace_from_bundle(bundle)
    assert target.dyslexia_font_enabled is False
    assert target.letter_spacing_level == 0


# ---- Profiles ----

def test_the_font_switch_is_never_part_of_a_profile():
    # It only takes effect on the next launch, and a profile is meant to apply
    # straight away, so it stays out on purpose.
    assert "dyslexia_font_enabled" not in PROFILE_KEYS