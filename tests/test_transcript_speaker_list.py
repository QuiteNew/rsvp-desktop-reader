"""Tests for a transcript's own Speaker cues list (Transcript.speaker_custom):
None for Auto, or a dict of label key to the name shown for Custom.

Covers the cleaner in core/speakers.py, the TranscriptStore setter, loading
from data.json (old, damaged and partly damaged files), and export and import
in both modes. Finding the speakers themselves is tested in test_speakers.py."""

import json

import pytest

from core.models import Transcript
from core.speakers import MAX_LABEL_CHARS, clean_custom_speakers
from core.storage import parse_data
from core.transcript_store import TranscriptStore


@pytest.fixture
def store(tmp_path):
    return TranscriptStore(data_directory=str(tmp_path))


def _saved_transcripts(directory):
    return json.loads((directory / "data.json").read_text(encoding="utf-8"))["transcripts"]


def _write_data(directory, transcripts):
    data = {"next_id": 10, "current_space_index": 0, "spaces": ["General"], "transcripts": transcripts}
    (directory / "data.json").write_text(json.dumps(data), encoding="utf-8")


# ---- The default ----

def test_a_transcript_starts_in_auto():
    assert Transcript(id=1, title="T", space="General").speaker_custom is None

def test_a_new_transcript_in_the_store_starts_in_auto(store):
    assert store.add_transcript("T", "General").speaker_custom is None


# ---- The cleaner ----

@pytest.mark.parametrize("value", [None, [], ["bob"], "bob", 0, 1, True, 2.5])
def test_anything_that_is_not_a_dict_means_auto(value):
    assert clean_custom_speakers(value) is None

def test_an_empty_dict_stays_custom_with_no_one_switched_on():
    assert clean_custom_speakers({}) == {}

def test_good_entries_are_kept_as_they_are():
    custom = {"dr. smith": "Smith", "smith": "Smith", "ann": "Ann", "speaker 2": "Speaker 2"}
    assert clean_custom_speakers(custom) == custom

def test_spaces_in_a_name_are_squeezed():
    assert clean_custom_speakers({"ann": "  Ann   Lee "}) == {"ann": "Ann Lee"}

@pytest.mark.parametrize("key", ["", "Ann", " ann", "ann ", "speaker  2", 1, None, True])
def test_a_key_that_is_not_a_label_key_is_dropped(key):
    assert clean_custom_speakers({key: "Ann", "bob": "Bob"}) == {"bob": "Bob"}

@pytest.mark.parametrize("name", ["", "   ", "\t\n", None, 1, True, ["Ann"], {"x": "y"}])
def test_an_empty_or_odd_name_is_dropped(name):
    assert clean_custom_speakers({"ann": name, "bob": "Bob"}) == {"bob": "Bob"}

def test_a_name_of_the_longest_length_is_kept_and_one_more_is_dropped():
    longest = "A" * MAX_LABEL_CHARS
    assert clean_custom_speakers({"ann": longest}) == {"ann": longest}
    assert clean_custom_speakers({"ann": longest + "B"}) == {}

def test_the_length_is_measured_after_spaces_are_squeezed():
    name = "A" * 14 + "      " + "B" * 15
    assert clean_custom_speakers({"ann": name}) == {"ann": "A" * 14 + " " + "B" * 15}

def test_the_answer_is_a_new_dict():
    custom = {"ann": "Ann"}
    cleaned = clean_custom_speakers(custom)
    assert cleaned is not custom
    custom["bob"] = "Bob"
    assert cleaned == {"ann": "Ann"}


# ---- The store setter ----

def test_a_custom_list_can_be_set_and_read_back(store):
    t = store.add_transcript("T", "General")
    store.set_transcript_speakers(t.id, {"ann": "Ann", "bob": "Robert"})
    assert t.speaker_custom == {"ann": "Ann", "bob": "Robert"}

def test_setting_none_goes_back_to_auto(store):
    t = store.add_transcript("T", "General")
    store.set_transcript_speakers(t.id, {"ann": "Ann"})
    store.set_transcript_speakers(t.id, None)
    assert t.speaker_custom is None

def test_setting_an_empty_dict_keeps_custom_with_no_one_on(store):
    t = store.add_transcript("T", "General")
    store.set_transcript_speakers(t.id, {})
    assert t.speaker_custom == {}

def test_the_list_is_cleaned_on_the_way_in(store):
    t = store.add_transcript("T", "General")
    store.set_transcript_speakers(t.id, {"ann": " Ann ", "Bad Key": "X", "bob": ""})
    assert t.speaker_custom == {"ann": "Ann"}

def test_changing_the_callers_dict_afterwards_changes_nothing(store):
    t = store.add_transcript("T", "General")
    custom = {"ann": "Ann"}
    store.set_transcript_speakers(t.id, custom)
    custom["bob"] = "Bob"
    assert t.speaker_custom == {"ann": "Ann"}

def test_it_is_saved_straight_away(store, tmp_path):
    t = store.add_transcript("T", "General")
    store.set_transcript_speakers(t.id, {"ann": "Ann"})
    assert _saved_transcripts(tmp_path)[0]["speaker_custom"] == {"ann": "Ann"}

@pytest.mark.parametrize("custom", [None, {}, {"ann": "Ann", "dr. smith": "Smith", "smith": "Smith"}])
def test_it_survives_a_reload(tmp_path, custom):
    first = TranscriptStore(data_directory=str(tmp_path))
    t = first.add_transcript("T", "General")
    first.set_transcript_speakers(t.id, {"x": "first"})
    first.set_transcript_speakers(t.id, custom)
    second = TranscriptStore(data_directory=str(tmp_path))
    assert second.transcripts[0].speaker_custom == custom

def test_only_the_named_transcript_changes(store):
    first = store.add_transcript("One", "General")
    second = store.add_transcript("Two", "General")
    store.set_transcript_speakers(second.id, {"ann": "Ann"})
    assert first.speaker_custom is None
    assert second.speaker_custom == {"ann": "Ann"}

def test_an_unknown_transcript_is_ignored(store):
    t = store.add_transcript("T", "General")
    store.set_transcript_speakers(t.id + 99, {"ann": "Ann"})
    assert t.speaker_custom is None

def test_other_setters_leave_it_alone(store):
    t = store.add_transcript("T", "General")
    store.set_transcript_speakers(t.id, {"ann": "Ann"})
    store.set_transcript_chunking(t.id, True, 3, "adaptive", 40)
    store.set_transcript_text(t.id, "Ann: hi\nBob: hey")
    store.set_transcript_wpm(t.id, 450)
    assert t.speaker_custom == {"ann": "Ann"}

def test_it_leaves_other_fields_alone(store):
    t = store.add_transcript("T", "General")
    store.set_transcript_chunking(t.id, True, 3, "adaptive", 40)
    store.set_transcript_speakers(t.id, {"ann": "Ann"})
    assert (t.chunking_enabled, t.chunk_size, t.chunk_mode, t.chunk_char_target) == (True, 3, "adaptive", 40)


# ---- Loading data.json ----

def test_an_older_save_without_the_key_loads_in_auto(tmp_path):
    _write_data(tmp_path, [{"id": 1, "title": "Old", "space": "General", "wpm": 450}])
    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.transcripts[0].wpm == 450
    assert store.transcripts[0].speaker_custom is None

@pytest.mark.parametrize("damaged", ["Ann", 5, True, ["ann"], None])
def test_a_damaged_list_loads_as_auto_and_the_rest_of_the_save_is_kept(tmp_path, damaged):
    _write_data(tmp_path, [
        {"id": 1, "title": "Damaged", "space": "General", "wpm": 450, "speaker_custom": damaged},
        {"id": 2, "title": "Fine", "space": "General", "speaker_custom": {"ann": "Ann"}},
    ])
    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.damaged_file is None
    first, second = store.transcripts
    assert (first.title, first.wpm, first.speaker_custom) == ("Damaged", 450, None)
    assert second.speaker_custom == {"ann": "Ann"}

def test_a_partly_damaged_list_keeps_its_good_entries(tmp_path):
    _write_data(tmp_path, [{
        "id": 1, "title": "T", "space": "General",
        "speaker_custom": {"ann": "Ann", "Bad": "X", "bob": 7, "carl": " Carl "},
    }])
    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.transcripts[0].speaker_custom == {"ann": "Ann", "carl": "Carl"}

def test_parse_data_cleans_the_list():
    data = {"next_id": 2, "current_space_index": 0, "spaces": ["General"], "transcripts": [
        {"id": 1, "title": "T", "space": "General", "speaker_custom": {"ann": "  Ann ", "X": "x"}},
    ]}
    assert parse_data(data)["transcripts"][0].speaker_custom == {"ann": "Ann"}


# ---- Export and import ----

def test_the_export_carries_the_list(store):
    t = store.add_transcript("T", "General")
    store.set_transcript_speakers(t.id, {"ann": "Ann"})
    other = store.add_transcript("U", "General")
    exported = store.export_state()["transcripts"]
    assert exported[0]["speaker_custom"] == {"ann": "Ann"}
    assert exported[1]["speaker_custom"] is None
    assert other.speaker_custom is None

def test_a_replace_import_carries_the_list_over(tmp_path):
    source = TranscriptStore(data_directory=str(tmp_path / "source"))
    t = source.add_transcript("T", "General")
    source.set_transcript_speakers(t.id, {"dr. smith": "Smith", "smith": "Smith"})
    target = TranscriptStore(data_directory=str(tmp_path / "target"))
    target.replace_all(parse_data(source.export_state()))
    assert target.transcripts[0].speaker_custom == {"dr. smith": "Smith", "smith": "Smith"}

def test_an_expand_import_carries_the_list_over(tmp_path):
    source = TranscriptStore(data_directory=str(tmp_path / "source"))
    t = source.add_transcript("T", "General")
    source.set_transcript_speakers(t.id, {"ann": "Ann"})
    target = TranscriptStore(data_directory=str(tmp_path / "target"))
    mine = target.add_transcript("Mine", "General")
    target.merge_all(parse_data(source.export_state()))
    assert mine.speaker_custom is None
    assert target.transcripts[1].speaker_custom == {"ann": "Ann"}

def test_a_bundle_from_before_speaker_cues_imports_in_auto(tmp_path):
    source = TranscriptStore(data_directory=str(tmp_path / "source"))
    source.add_transcript("T", "General")
    state = source.export_state()
    del state["transcripts"][0]["speaker_custom"]
    target = TranscriptStore(data_directory=str(tmp_path / "target"))
    target.replace_all(parse_data(state))
    assert target.transcripts[0].speaker_custom is None
