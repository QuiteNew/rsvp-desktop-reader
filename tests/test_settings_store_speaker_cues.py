"""Tests for the Speaker cues settings in SettingsStore: the on/off switch,
the sound choice and the chime style.

How speakers are found is tested in test_speakers.py. This file only checks
that the store keeps the three settings, saves them, reads a damaged file
safely, carries them in export bundles, and keeps them out of reading
profiles."""

import json

import pytest

from core.chime import CHIME_STYLES
from core.profiles import PROFILE_KEYS, value_is_valid
from core.settings_store import SPEAKER_CUE_SOUNDS, AppSettings, SettingsStore


@pytest.fixture
def store(tmp_path):
    return SettingsStore(settings_directory=str(tmp_path))


def _settings_json(directory):
    return json.loads((directory / "settings.json").read_text(encoding="utf-8"))


def _write_settings(directory, data):
    (directory / "settings.json").write_text(json.dumps(data), encoding="utf-8")


# ---- Defaults ----

def test_a_fresh_store_has_speaker_cues_off_and_no_sound(store):
    assert store.speaker_cues_enabled is False
    assert store.speaker_cue_sound == "off"

def test_the_defaults_match_the_dataclass(store):
    assert store.speaker_cues_enabled == AppSettings().speaker_cues_enabled
    assert store.speaker_cue_sound == AppSettings().speaker_cue_sound

def test_the_default_sound_is_the_first_choice():
    assert AppSettings().speaker_cue_sound == SPEAKER_CUE_SOUNDS[0] == "off"

def test_the_sound_choices():
    assert SPEAKER_CUE_SOUNDS == ("off", "change", "per_speaker")


# ---- The switch ----

def test_speaker_cues_can_be_turned_on_and_off_again(store):
    store.set_speaker_cues_enabled(True)
    assert store.speaker_cues_enabled is True
    store.set_speaker_cues_enabled(False)
    assert store.speaker_cues_enabled is False

@pytest.mark.parametrize("enabled", [True, False])
def test_the_switch_persists_and_reloads(tmp_path, enabled):
    first = SettingsStore(settings_directory=str(tmp_path))
    first.set_speaker_cues_enabled(not enabled)
    first.set_speaker_cues_enabled(enabled)
    second = SettingsStore(settings_directory=str(tmp_path))
    assert second.speaker_cues_enabled is enabled


# ---- The sound ----

@pytest.mark.parametrize("sound", SPEAKER_CUE_SOUNDS)
def test_every_sound_choice_can_be_set(store, sound):
    store.set_speaker_cue_sound(sound)
    assert store.speaker_cue_sound == sound

@pytest.mark.parametrize("sound", SPEAKER_CUE_SOUNDS)
def test_the_sound_persists_and_reloads(tmp_path, sound):
    first = SettingsStore(settings_directory=str(tmp_path))
    first.set_speaker_cue_sound(sound)
    second = SettingsStore(settings_directory=str(tmp_path))
    assert second.speaker_cue_sound == sound


# ---- The style ----

def test_a_fresh_store_has_the_bell_style(store):
    assert store.speaker_cue_style == "bell"
    assert AppSettings().speaker_cue_style == CHIME_STYLES[0] == "bell"

@pytest.mark.parametrize("style", CHIME_STYLES)
def test_every_style_can_be_set(store, style):
    store.set_speaker_cue_style(style)
    assert store.speaker_cue_style == style

@pytest.mark.parametrize("style", CHIME_STYLES)
def test_the_style_persists_and_reloads(tmp_path, style):
    first = SettingsStore(settings_directory=str(tmp_path))
    first.set_speaker_cue_style(style)
    second = SettingsStore(settings_directory=str(tmp_path))
    assert second.speaker_cue_style == style

def test_the_style_is_written_to_settings_json(tmp_path):
    store = SettingsStore(settings_directory=str(tmp_path))
    store.set_speaker_cue_style("glass")
    assert _settings_json(tmp_path)["speaker_cue_style"] == "glass"

@pytest.mark.parametrize("damaged", ["trumpet", "Bell", "", " soft", 1, True, None, ["wood"], {}])
def test_an_unknown_style_reads_as_bell(tmp_path, damaged):
    _write_settings(tmp_path, {"default_wpm": 450, "speaker_cue_style": damaged})
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.speaker_cue_style == "bell"
    assert store.default_wpm == 450

def test_the_style_does_not_touch_the_other_two(store):
    store.set_speaker_cues_enabled(True)
    store.set_speaker_cue_sound("per_speaker")
    store.set_speaker_cue_style("wood")
    assert (store.speaker_cues_enabled, store.speaker_cue_sound) == (True, "per_speaker")
    store.set_speaker_cue_sound("change")
    store.set_speaker_cues_enabled(False)
    assert store.speaker_cue_style == "wood"


# ---- Independence ----

def test_the_two_settings_do_not_touch_each_other(store):
    store.set_speaker_cue_sound("per_speaker")
    store.set_speaker_cues_enabled(True)
    assert store.speaker_cue_sound == "per_speaker"
    store.set_speaker_cues_enabled(False)
    assert store.speaker_cue_sound == "per_speaker"
    store.set_speaker_cue_sound("change")
    assert store.speaker_cues_enabled is False

def test_they_do_not_touch_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 40)
    store.set_bold_starts_enabled(True)
    store.set_speaker_cues_enabled(True)
    store.set_speaker_cue_sound("change")
    assert store.default_wpm == 500
    assert store.default_font_size == 40
    assert store.bold_starts_enabled is True

def test_other_settings_do_not_touch_them(store):
    store.set_speaker_cues_enabled(True)
    store.set_speaker_cue_sound("change")
    store.set_defaults(500, "#111111", "#222222", "#333333", 40)
    store.set_bold_starts_enabled(True)
    assert store.speaker_cues_enabled is True
    assert store.speaker_cue_sound == "change"


# ---- The file on disk ----

def test_both_are_written_to_settings_json(tmp_path):
    store = SettingsStore(settings_directory=str(tmp_path))
    store.set_speaker_cues_enabled(True)
    store.set_speaker_cue_sound("per_speaker")
    saved = _settings_json(tmp_path)
    assert saved["speaker_cues_enabled"] is True
    assert saved["speaker_cue_sound"] == "per_speaker"

def test_an_older_settings_file_without_them_loads_with_the_defaults(tmp_path):
    _write_settings(tmp_path, {"default_wpm": 450})
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.default_wpm == 450  # the rest of the file is still read
    assert store.speaker_cues_enabled is False
    assert store.speaker_cue_sound == "off"
    assert store.speaker_cue_style == "bell"

def test_a_settings_file_that_has_them_is_read(tmp_path):
    _write_settings(tmp_path, {"speaker_cues_enabled": True, "speaker_cue_sound": "change"})
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.speaker_cues_enabled is True
    assert store.speaker_cue_sound == "change"

@pytest.mark.parametrize("damaged", ["yes", "true", "false", 1, 0, None, [], {}])
def test_only_a_real_true_turns_cues_on(tmp_path, damaged):
    # A hand-edited or damaged file must not switch cues on by accident
    # ("false" written as text is still a non-empty string), and the rest of
    # the file is still read.
    _write_settings(tmp_path, {"default_wpm": 450, "speaker_cues_enabled": damaged})
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.speaker_cues_enabled is False
    assert store.default_wpm == 450

@pytest.mark.parametrize("damaged", ["loud", "Change", "", " off", 1, True, None, ["change"], {}])
def test_an_unknown_sound_reads_as_no_sound(tmp_path, damaged):
    _write_settings(tmp_path, {"default_wpm": 450, "speaker_cue_sound": damaged})
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.speaker_cue_sound == "off"
    assert store.default_wpm == 450


# ---- Export bundles ----

def test_the_export_includes_them_with_their_defaults(store):
    exported = store.export_settings()
    assert exported["speaker_cues_enabled"] is False
    assert exported["speaker_cue_sound"] == "off"
    assert exported["speaker_cue_style"] == "bell"

def test_a_replace_import_carries_them_over(tmp_path):
    source = SettingsStore(settings_directory=str(tmp_path / "source"))
    source.set_speaker_cues_enabled(True)
    source.set_speaker_cue_sound("per_speaker")
    source.set_speaker_cue_style("soft")
    target = SettingsStore(settings_directory=str(tmp_path / "target"))
    target.replace_from_bundle(source.export_settings())
    assert target.speaker_cues_enabled is True
    assert target.speaker_cue_sound == "per_speaker"
    assert target.speaker_cue_style == "soft"

def test_a_bundle_from_before_speaker_cues_still_imports_with_the_defaults(tmp_path):
    older = SettingsStore(settings_directory=str(tmp_path / "older"))
    bundle = older.export_settings()
    del bundle["speaker_cues_enabled"]
    del bundle["speaker_cue_sound"]
    del bundle["speaker_cue_style"]
    target = SettingsStore(settings_directory=str(tmp_path / "target"))
    target.set_speaker_cues_enabled(True)
    target.set_speaker_cue_sound("change")
    target.set_speaker_cue_style("wood")
    target.replace_from_bundle(bundle)
    assert target.speaker_cues_enabled is False
    assert target.speaker_cue_sound == "off"
    assert target.speaker_cue_style == "bell"


# ---- Profiles ----

@pytest.mark.parametrize("key, value", [
    ("speaker_cues_enabled", True), ("speaker_cue_sound", "change"), ("speaker_cue_style", "glass"),
])
def test_they_are_never_part_of_a_profile(key, value):
    # Speaker cues have their own window, like chunking, so applying a
    # profile leaves them alone.
    assert key not in PROFILE_KEYS
    assert not value_is_valid(key, value)

def test_a_profile_cannot_hold_them_even_when_asked_to(store):
    profile = store.add_profile("Plain", {
        "speaker_cues_enabled": True, "speaker_cue_sound": "change", "speaker_cue_style": "glass",
        "default_wpm": 300,
    })
    assert profile.values == {"default_wpm": 300}