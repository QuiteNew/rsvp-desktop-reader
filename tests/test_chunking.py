"""Tests for the chunking (multi-word flash) feature.

Step 1 covers the data layer: the new Transcript and AppSettings fields,
their defaults, that they persist, and that save files written before the
feature load with the right defaults. Step 2 covers the grouping and
chunk-aware navigation in ReaderSession. The reader display and settings UI
are tested as later steps add them. See claude/chunking-v1-design.md."""

import json

import core.storage as storage
from core.models import Transcript
from core.settings_store import AppSettings, SettingsStore, CHUNK_SIZE_RANGE
from core.reader import ReaderSession, CHUNK_CHAR_CAP


# ---------------------------------------------------------------------------
# Step 1: data model and settings.
# ---------------------------------------------------------------------------

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


def test_transcript_chunking_fields_round_trip(tmp_path):
    directory = str(tmp_path)
    t = Transcript(id=1, title="Doc", space="General", chunking_enabled=True, chunk_size=4)
    storage.save_state(directory, ["General"], 0, [t], next_id=2)
    loaded = storage.load_state(directory)
    assert loaded is not None
    restored = loaded["transcripts"][0]
    assert restored.chunking_enabled is True
    assert restored.chunk_size == 4


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


# ---------------------------------------------------------------------------
# Step 2: grouping and chunk-aware navigation in ReaderSession.
# ---------------------------------------------------------------------------

def test_grouping_splits_by_size_with_short_final_chunk():
    s = ReaderSession("one two three four five", chunk_enabled=True, chunk_size=2)
    assert s.chunk_ranges() == [(0, 2), (2, 4), (4, 5)]


def test_grouping_breaks_at_a_sentence_end():
    # "two." ends a sentence, so the chunk closes there despite size 3.
    s = ReaderSession("one two. three four five six", chunk_enabled=True, chunk_size=3)
    assert s.chunk_ranges() == [(0, 2), (2, 5), (5, 6)]


def test_grouping_respects_the_character_cap():
    # Three ten-character words, cap 30. Adding the third would make the chunk
    # 10 + 1 + 10 + 1 + 10 = 32 chars, so it starts a new chunk.
    assert CHUNK_CHAR_CAP == 30
    word = "a" * 10
    text = " ".join([word, word, word])
    s = ReaderSession(text, chunk_enabled=True, chunk_size=5)
    assert s.chunk_ranges() == [(0, 2), (2, 3)]


def test_grouping_never_makes_an_empty_chunk_for_an_overlong_word():
    long_word = "x" * 40  # longer than the cap on its own
    s = ReaderSession(long_word + " short", chunk_enabled=True, chunk_size=3)
    assert s.chunk_ranges() == [(0, 1), (1, 2)]


def test_disabled_groups_every_word_on_its_own():
    s = ReaderSession("one two three", chunk_enabled=False)
    assert s.chunk_ranges() == [(0, 1), (1, 2), (2, 3)]


def test_advance_moves_by_whole_chunks():
    s = ReaderSession("one two three four five", chunk_enabled=True, chunk_size=2)
    assert s.index == 0
    s.advance()
    assert s.index == 2
    s.advance()
    assert s.index == 4
    s.advance()
    assert s.index == 5
    assert s.is_finished


def test_advance_ages_warmup_by_the_chunk_word_count():
    s = ReaderSession("one two three four five", chunk_enabled=True, chunk_size=2)
    s.advance()                       # passed a 2-word chunk
    assert s._words_shown == 2
    s.advance()                       # another 2-word chunk
    assert s._words_shown == 4
    s.advance()                       # final 1-word chunk
    assert s._words_shown == 5


def test_seek_snaps_to_the_enclosing_chunk_start():
    s = ReaderSession("w0 w1 w2 w3 w4 w5", chunk_enabled=True, chunk_size=2)  # (0,2)(2,4)(4,6)
    s.seek_to(3)
    assert s.index == 2               # word 3 lives in chunk (2, 4)
    s.seek_to(5)
    assert s.index == 4
    s.seek_to(0)
    assert s.index == 0


def test_start_index_snaps_to_a_chunk_boundary():
    s = ReaderSession("w0 w1 w2 w3", start_index=3, chunk_enabled=True, chunk_size=2)
    assert s.index == 2               # starts at the chunk containing word 3


def test_current_chunk_returns_the_member_frames():
    s = ReaderSession("alpha beta gamma", chunk_enabled=True, chunk_size=2)
    chunk = s.current_chunk()
    assert chunk is not None and len(chunk) == 2
    texts = [f.before + f.focus + f.after for f in chunk]
    assert texts == ["alpha", "beta"]
    assert s.current_chunk_bounds() == (0, 2)


def test_current_chunk_delay_equals_the_sum_of_its_words_with_warmup():
    # The chunk's dwell must equal what the same words would take read singly,
    # including the warm-up ramp ageing word by word. Compare a chunked
    # session against a single-word one over the same text.
    text = "alpha beta gamma delta"
    chunked = ReaderSession(text, wpm=300, chunk_enabled=True, chunk_size=2, warm_up_enabled=True)
    single = ReaderSession(text, wpm=300, warm_up_enabled=True)

    expected_first = single.current_delay_ms()
    single.advance()
    expected_first += single.current_delay_ms()
    single.advance()
    assert chunked.current_chunk_delay_ms() == expected_first

    chunked.advance()
    expected_second = single.current_delay_ms()
    single.advance()
    expected_second += single.current_delay_ms()
    single.advance()
    assert chunked.current_chunk_delay_ms() == expected_second


def test_remaining_ms_is_unaffected_by_chunking():
    text = "one two three four five six"
    chunked = ReaderSession(text, wpm=300, chunk_enabled=True, chunk_size=3)
    single = ReaderSession(text, wpm=300)
    assert chunked.remaining_ms() == single.remaining_ms()


def test_disabled_session_matches_single_word_stepping():
    text = "one two three four"
    s = ReaderSession(text, chunk_enabled=False)
    # current_chunk collapses to one word, and advancing steps by one.
    for expected_index in range(4):
        assert s.index == expected_index
        chunk = s.current_chunk()
        assert chunk is not None and len(chunk) == 1
        assert s.current_chunk_delay_ms() == s.current_delay_ms()
        s.advance()
    assert s.is_finished