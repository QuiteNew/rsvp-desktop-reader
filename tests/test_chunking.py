"""Tests for the chunking (multi-word flash) feature.

Step 1 covers only the data layer: the new Transcript and AppSettings
fields, their defaults, that they persist, and that save files written
before the feature load with the right defaults. The grouping and reader
behavior are tested as later steps add them. See
claude/chunking-v1-design.md."""

import json

import core.storage as storage
from core.models import Transcript
from core.settings_store import AppSettings, SettingsStore, CHUNK_SIZE_RANGE


# Model and settings defaults

def test_new_transcript_defaults_to_chunking_off_size_two():
    t = Transcript(id=1, title="Doc", space="General")
    assert t.chunking_enabled is False
    assert t.chunk_size == 2


def test_app_settings_chunking_defaults():
    s = AppSettings()
    assert s.default_chunking_enabled is False
    assert s.default_chunk_size == 2


def test_chunk_size_range_is_two_to_five():
    assert CHUNK_SIZE_RANGE == (2, 5)


# Transcript chunking fields survive a save/load round-trip

def test_transcript_chunking_fields_round_trip(tmp_path):
    directory = str(tmp_path)
    t = Transcript(id=1, title="Doc", space="General", chunking_enabled=True, chunk_size=4)
    storage.save_state(directory, ["General"], 0, [t], next_id=2)
    loaded = storage.load_state(directory)
    assert loaded is not None
    restored = loaded["transcripts"][0]
    assert restored.chunking_enabled is True
    assert restored.chunk_size == 4


# A data.json whose transcripts predate chunking loads with the defaults

def test_old_transcript_without_chunking_keys_loads_defaults():
    # A transcript dict as an older version would have written it: all the
    # fields the model had then, but no chunking_enabled / chunk_size.
    old_transcript = {
        "id": 1, "title": "Doc", "space": "General", "raw_text": "hello world",
        "wpm": 300, "position": 0,
        "font_color": "#FFFFFF", "highlight_color": "#E74C3C", "background_color": "#1E1E1E",
        "font_size": 32, "is_paused": False, "draft_text": "", "is_stopped": False,
        "font_color_is_default": True, "highlight_color_is_default": True,
        "background_color_is_default": True,
        "times_read": 0, "total_words_read": 0, "total_time_spent_seconds": 0,
        "pre_normalize_text": "", "normalized_text": "",
        "bookmarks": [],
    }
    data = {"next_id": 2, "current_space_index": 0, "spaces": ["General"],
            "transcripts": [old_transcript]}
    parsed = storage.parse_data(data)
    assert parsed is not None
    t = parsed["transcripts"][0]
    assert t.chunking_enabled is False
    assert t.chunk_size == 2


# Settings: the setter persists, and old files load defaults

def test_set_chunking_defaults_persists(tmp_path):
    directory = str(tmp_path)
    store = SettingsStore(settings_directory=directory)
    store.set_chunking_defaults(True, 4)
    assert store.default_chunking_enabled is True
    assert store.default_chunk_size == 4
    reloaded = SettingsStore(settings_directory=directory)
    assert reloaded.default_chunking_enabled is True
    assert reloaded.default_chunk_size == 4


def test_old_settings_without_chunking_keys_loads_defaults(tmp_path):
    settings_file = tmp_path / "settings.json"
    # A minimal, valid settings.json from before chunking existed.
    settings_file.write_text(json.dumps({"default_wpm": 450}), encoding="utf-8")
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.default_wpm == 450  # the old value is respected
    assert store.default_chunking_enabled is False  # new keys fall back to defaults
    assert store.default_chunk_size == 2


# The export bundle carries the new defaults (and still drops data_directory)

def test_export_settings_includes_chunking_defaults(tmp_path):
    store = SettingsStore(settings_directory=str(tmp_path))
    store.set_chunking_defaults(True, 3)
    exported = store.export_settings()
    assert exported["default_chunking_enabled"] is True
    assert exported["default_chunk_size"] == 3
    assert "data_directory" not in exported


def test_settings_bundle_round_trip_preserves_chunking(tmp_path):
    src = SettingsStore(settings_directory=str(tmp_path / "a"))
    src.set_chunking_defaults(True, 5)
    bundle_settings = src.export_settings()
    dst = SettingsStore(settings_directory=str(tmp_path / "b"))
    dst.replace_from_bundle(bundle_settings)
    assert dst.default_chunking_enabled is True
    assert dst.default_chunk_size == 5