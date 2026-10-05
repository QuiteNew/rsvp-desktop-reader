import json
from pathlib import Path

import pytest

from core.storage import (
    save_state, parse_data, load_state,
    LIVE_SAVE_INTERVAL_SECONDS, DEFAULT_DATA_DIR,
)
from core.models import Transcript, Bookmark


def _read_json(directory) -> dict:
    return json.loads((Path(directory) / "data.json").read_text(encoding="utf-8"))


def _write_json(directory, data) -> None:
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    (path / "data.json").write_text(json.dumps(data), encoding="utf-8")


def _valid_data(transcripts=None) -> dict:
    """A minimal valid on-disk data dict, the shape save_state() writes and
    parse_data() expects. transcripts are plain dicts, as they'd be in the
    file, not Transcript objects."""
    return {
        "next_id": 1,
        "current_space_index": 0,
        "spaces": ["General"],
        "transcripts": transcripts if transcripts is not None else [],
    }


# Module constants

def test_live_save_interval_seconds_is_positive():
    assert LIVE_SAVE_INTERVAL_SECONDS > 0

def test_default_data_dir_is_under_home():
    assert DEFAULT_DATA_DIR == Path.home() / ".rsvp_reader"


# save_state

def test_save_state_creates_missing_directory(tmp_path):
    # A directory that doesn't exist yet, including a missing parent, like
    # the very first launch into a fresh data location.
    target = tmp_path / "does" / "not" / "exist"
    save_state(str(target), ["General"], 0, [], 1)
    assert (target / "data.json").exists()

def test_save_state_writes_expected_top_level_shape(tmp_path):
    t = Transcript(id=1, title="Lecture", space="General")
    save_state(str(tmp_path), ["General", "Work"], 1, [t], 5)

    raw = _read_json(tmp_path)
    assert raw["next_id"] == 5
    assert raw["current_space_index"] == 1
    assert raw["spaces"] == ["General", "Work"]
    assert len(raw["transcripts"]) == 1
    assert raw["transcripts"][0]["id"] == 1
    assert raw["transcripts"][0]["title"] == "Lecture"

def test_save_state_serializes_bookmarks_as_dicts(tmp_path):
    # asdict() turns each Bookmark into a plain dict on disk; parse_data()
    # is what rebuilds them on the way back in.
    t = Transcript(
        id=1, title="Doc", space="General",
        bookmarks=[Bookmark(index=3, snippet="the quick brown", created_at="2020-01-01T00:00:00+00:00", label="Intro")],
    )
    save_state(str(tmp_path), ["General"], 0, [t], 2)

    stored_bookmarks = _read_json(tmp_path)["transcripts"][0]["bookmarks"]
    assert isinstance(stored_bookmarks, list)
    assert isinstance(stored_bookmarks[0], dict)
    assert stored_bookmarks[0]["index"] == 3
    assert stored_bookmarks[0]["snippet"] == "the quick brown"
    assert stored_bookmarks[0]["label"] == "Intro"


# parse_data: the happy path

def test_parse_data_returns_real_transcript_objects():
    result = parse_data(_valid_data([{"id": 1, "title": "T", "space": "General"}]))
    assert result is not None
    assert isinstance(result["transcripts"][0], Transcript)

def test_parse_data_preserves_top_level_values():
    result = parse_data({
        "next_id": 7,
        "current_space_index": 2,
        "spaces": ["General", "Work", "Reading"],
        "transcripts": [],
    })
    assert result["next_id"] == 7
    assert result["current_space_index"] == 2
    assert result["spaces"] == ["General", "Work", "Reading"]
    assert result["transcripts"] == []

def test_parse_data_preserves_transcript_fields():
    result = parse_data(_valid_data([{
        "id": 4, "title": "Full", "space": "Work",
        "raw_text": "hello world", "wpm": 450, "position": 12,
        "font_color": "#111111", "highlight_color": "#222222", "background_color": "#333333",
        "font_size": 40, "is_paused": True, "is_stopped": True,
        "times_read": 3, "total_words_read": 900, "total_time_spent_seconds": 120,
        "pre_normalize_text": "1. x", "normalized_text": "x",
    }]))
    t = result["transcripts"][0]
    assert t.id == 4
    assert t.raw_text == "hello world"
    assert t.wpm == 450
    assert t.position == 12
    assert t.font_color == "#111111"
    assert t.font_size == 40
    assert t.is_paused is True
    assert t.is_stopped is True
    assert t.times_read == 3
    assert t.total_words_read == 900
    assert t.total_time_spent_seconds == 120
    assert t.pre_normalize_text == "1. x"
    assert t.normalized_text == "x"

def test_parse_data_empty_transcripts_is_valid():
    result = parse_data(_valid_data([]))
    assert result is not None
    assert result["transcripts"] == []


# parse_data: color-flag backfill (old saves)

def test_parse_data_backfills_missing_color_flags_to_false():
    # A save from before the color-default flags existed has no keys for
    # them; they must resolve to False so the transcript keeps its own
    # colors instead of being treated as still tracking the theme default.
    result = parse_data(_valid_data([{"id": 1, "title": "Old", "space": "General"}]))
    t = result["transcripts"][0]
    assert t.font_color_is_default is False
    assert t.highlight_color_is_default is False
    assert t.background_color_is_default is False

def test_parse_data_preserves_present_color_flags():
    # setdefault must not clobber flags that are actually stored.
    result = parse_data(_valid_data([{
        "id": 1, "title": "New", "space": "General",
        "font_color_is_default": True,
        "highlight_color_is_default": True,
        "background_color_is_default": True,
    }]))
    t = result["transcripts"][0]
    assert t.font_color_is_default is True
    assert t.highlight_color_is_default is True
    assert t.background_color_is_default is True


# parse_data: bookmark reconstruction

def test_parse_data_rebuilds_bookmarks_into_objects():
    result = parse_data(_valid_data([{
        "id": 1, "title": "Doc", "space": "General",
        "bookmarks": [
            {"index": 2, "snippet": "two", "created_at": "2020-01-01T00:00:00+00:00", "label": "A"},
            {"index": 9, "snippet": "nine", "created_at": "2020-01-02T00:00:00+00:00", "label": ""},
        ],
    }]))
    bookmarks = result["transcripts"][0].bookmarks
    assert all(isinstance(b, Bookmark) for b in bookmarks)
    assert [b.index for b in bookmarks] == [2, 9]
    assert bookmarks[0].snippet == "two"
    assert bookmarks[0].label == "A"

def test_parse_data_filters_unknown_bookmark_keys():
    # A bookmark field added by a future version must be dropped, not passed
    # to Bookmark() (which would raise and discard the whole save).
    result = parse_data(_valid_data([{
        "id": 1, "title": "Doc", "space": "General",
        "bookmarks": [{
            "index": 5, "snippet": "s", "created_at": "2020-01-01T00:00:00+00:00",
            "label": "Kept", "future_field": "ignored",
        }],
    }]))
    assert result is not None
    bookmark = result["transcripts"][0].bookmarks[0]
    assert bookmark.index == 5
    assert bookmark.label == "Kept"
    assert not hasattr(bookmark, "future_field")

def test_parse_data_missing_bookmarks_key_defaults_to_empty():
    result = parse_data(_valid_data([{"id": 1, "title": "Doc", "space": "General"}]))
    assert result["transcripts"][0].bookmarks == []


# parse_data: failure paths all return None

def test_parse_data_missing_next_id_returns_none():
    assert parse_data({
        "current_space_index": 0, "spaces": ["General"], "transcripts": [],
    }) is None

def test_parse_data_missing_transcripts_returns_none():
    assert parse_data({
        "next_id": 1, "current_space_index": 0, "spaces": ["General"],
    }) is None

def test_parse_data_transcript_missing_required_field_returns_none():
    # Transcript() requires id/title/space, so a transcript dict missing one
    # raises TypeError inside parse_data, which treats the whole thing as
    # "no valid save" rather than crashing.
    assert parse_data(_valid_data([{"id": 1, "space": "General"}])) is None  # no title

def test_parse_data_unrelated_dict_returns_none():
    assert parse_data({"something": "else"}) is None

def test_parse_data_non_dict_returns_none():
    assert parse_data([]) is None
    assert parse_data("not a dict") is None
    assert parse_data(None) is None


# load_state

def test_load_state_missing_file_returns_none(tmp_path):
    # No data.json written yet, like a brand-new data directory.
    assert load_state(str(tmp_path)) is None

def test_load_state_corrupt_json_returns_none(tmp_path):
    (tmp_path / "data.json").write_text("{not valid json!!!", encoding="utf-8")
    assert load_state(str(tmp_path)) is None

def test_load_state_valid_json_but_invalid_shape_returns_none(tmp_path):
    # Parses as JSON fine, but isn't a save file, so parse_data rejects it.
    _write_json(tmp_path, {"unrelated": 1})
    assert load_state(str(tmp_path)) is None

def test_load_state_valid_file_returns_transcript_objects(tmp_path):
    _write_json(tmp_path, _valid_data([{"id": 1, "title": "T", "space": "General"}]))
    result = load_state(str(tmp_path))
    assert result is not None
    assert isinstance(result["transcripts"][0], Transcript)
    assert result["transcripts"][0].title == "T"


# Full round trip through save_state + load_state

def test_save_then_load_round_trip_preserves_everything(tmp_path):
    original = Transcript(
        id=1, title="Lecture", space="Work",
        raw_text="hello world", wpm=400, position=5,
        font_color="#101010", font_color_is_default=False,
        times_read=2, total_words_read=300, total_time_spent_seconds=60,
        bookmarks=[Bookmark(index=4, snippet="world", created_at="2020-01-01T00:00:00+00:00", label="Here")],
    )
    save_state(str(tmp_path), ["General", "Work"], 1, [original], 9)

    result = load_state(str(tmp_path))
    assert result["next_id"] == 9
    assert result["current_space_index"] == 1
    assert result["spaces"] == ["General", "Work"]

    reloaded = result["transcripts"][0]
    assert isinstance(reloaded, Transcript)
    assert reloaded.title == "Lecture"
    assert reloaded.raw_text == "hello world"
    assert reloaded.wpm == 400
    assert reloaded.position == 5
    assert reloaded.font_color == "#101010"
    assert reloaded.font_color_is_default is False
    assert reloaded.times_read == 2
    assert reloaded.total_words_read == 300
    assert reloaded.total_time_spent_seconds == 60

    assert len(reloaded.bookmarks) == 1
    assert isinstance(reloaded.bookmarks[0], Bookmark)
    assert reloaded.bookmarks[0].index == 4
    assert reloaded.bookmarks[0].snippet == "world"
    assert reloaded.bookmarks[0].label == "Here"