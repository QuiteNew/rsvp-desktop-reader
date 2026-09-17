import json
import pytest
from core.transcript_store import TranscriptStore


@pytest.fixture
def store(tmp_path):
    """A fresh TranscriptStore backed by a unique, disposable temporary
    directory — tmp_path is a built-in pytest fixture, so this never
    touches your real ~/.rsvp_reader data."""
    return TranscriptStore(data_directory=str(tmp_path))


# ---- Fresh store defaults ----

def test_fresh_store_has_one_default_space():
    fresh_store = TranscriptStore(data_directory="unused")  # no file exists yet, so this never actually reads/writes
    assert fresh_store.spaces == ["General"]

def test_fresh_store_default_space_is_current(store):
    assert store.current_space == "General"
    assert store.default_space == "General"

def test_fresh_store_has_no_transcripts(store):
    assert store.transcripts == []
    assert store.transcripts_in_current_space == []


# ---- add_space ----

def test_add_space_appends_and_switches_to_it(store):
    store.add_space("Work")
    assert store.spaces == ["General", "Work"]
    assert store.current_space == "Work"

def test_add_space_strips_whitespace_from_name(store):
    store.add_space("  Work  ")
    assert store.spaces == ["General", "Work"]

def test_add_space_ignores_blank_name(store):
    store.add_space("   ")
    assert store.spaces == ["General"]

def test_add_space_ignores_duplicate_name(store):
    store.add_space("Work")
    store.switch_to_space("General")
    store.add_space("Work")  # already exists
    assert store.spaces == ["General", "Work"]  # not duplicated
    assert store.current_space == "General"  # did not switch, since nothing was actually added


# ---- switch_to_space ----

def test_switch_to_space_changes_current_space(store):
    store.add_space("Work")
    store.switch_to_space("General")
    assert store.current_space == "General"

def test_switch_to_nonexistent_space_is_a_safe_no_op(store):
    store.switch_to_space("Does Not Exist")
    assert store.current_space == "General"  # unchanged


# ---- add_transcript ----

def test_add_transcript_returns_transcript_with_correct_fields(store):
    t = store.add_transcript("My Title", "General")
    assert t.title == "My Title"
    assert t.space == "General"
    assert t.id == 1

def test_add_transcript_uses_default_wpm_and_colors_when_not_specified(store):
    t = store.add_transcript("Title", "General")
    assert t.wpm == 300
    assert t.font_color == "#FFFFFF"
    assert t.highlight_color == "#E74C3C"
    assert t.background_color == "#1E1E1E"

def test_add_transcript_uses_custom_wpm_and_colors_when_specified(store):
    t = store.add_transcript("Title", "General", wpm=450, font_color="#111111", highlight_color="#222222", background_color="#333333")
    assert t.wpm == 450
    assert t.font_color == "#111111"
    assert t.highlight_color == "#222222"
    assert t.background_color == "#333333"

def test_add_transcript_ids_increment(store):
    t1 = store.add_transcript("First", "General")
    t2 = store.add_transcript("Second", "General")
    t3 = store.add_transcript("Third", "General")
    assert (t1.id, t2.id, t3.id) == (1, 2, 3)

def test_add_transcript_id_not_reused_after_delete(store):
    t1 = store.add_transcript("First", "General")
    store.delete_transcript(t1.id)
    t2 = store.add_transcript("Second", "General")
    assert t2.id == 2  # continues from next_id, does not reuse the deleted id


# ---- transcripts / transcripts_in_current_space ----

def test_transcripts_in_current_space_filters_by_active_space(store):
    store.add_transcript("In General", "General")
    store.add_space("Work")
    store.add_transcript("In Work", "Work")

    assert len(store.transcripts_in_current_space) == 1
    assert store.transcripts_in_current_space[0].title == "In Work"

    store.switch_to_space("General")
    assert len(store.transcripts_in_current_space) == 1
    assert store.transcripts_in_current_space[0].title == "In General"

def test_transcripts_property_includes_all_spaces_regardless_of_current(store):
    store.add_transcript("In General", "General")
    store.add_space("Work")
    store.add_transcript("In Work", "Work")
    assert len(store.transcripts) == 2

def test_spaces_property_returns_a_copy_not_the_live_list(store):
    spaces_list = store.spaces
    spaces_list.append("Sneaky")
    assert store.spaces == ["General"]

def test_transcripts_property_returns_a_copy_not_the_live_list(store):
    store.add_transcript("Test", "General")
    transcripts_list = store.transcripts
    transcripts_list.clear()
    assert len(store.transcripts) == 1


# ---- Per-transcript setters ----

def test_set_transcript_text_updates_raw_text(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_text(t.id, "Hello world")
    assert store.transcripts[0].raw_text == "Hello world"

def test_set_transcript_position_updates_position(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_position(t.id, 42)
    assert store.transcripts[0].position == 42

def test_set_transcript_paused_updates_is_paused(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_paused(t.id, True)
    assert store.transcripts[0].is_paused is True

def test_set_transcript_wpm_updates_wpm(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_wpm(t.id, 600)
    assert store.transcripts[0].wpm == 600

def test_set_transcript_font_color_updates_font_color(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_font_color(t.id, "#ABCDEF")
    assert store.transcripts[0].font_color == "#ABCDEF"

def test_set_transcript_highlight_color_updates_highlight_color(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_highlight_color(t.id, "#ABCDEF")
    assert store.transcripts[0].highlight_color == "#ABCDEF"

def test_set_transcript_background_color_updates_background_color(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_background_color(t.id, "#ABCDEF")
    assert store.transcripts[0].background_color == "#ABCDEF"

def test_set_transcript_draft_text_updates_draft_text(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_draft_text(t.id, "unsaved draft")
    assert store.transcripts[0].draft_text == "unsaved draft"

def test_set_transcript_stopped_updates_is_stopped(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_stopped(t.id, True)
    assert store.transcripts[0].is_stopped is True

def test_setter_on_nonexistent_id_is_a_safe_no_op(store):
    # Every setter shares the identical _find_transcript -> `if t:` guard
    # pattern — this confirms that pattern actually works, using one
    # representative setter rather than repeating this check eight times.
    store.add_transcript("Title", "General")
    store.set_transcript_text(999, "should not crash or change anything")
    assert store.transcripts[0].raw_text == ""


# ---- delete_transcript ----

def test_delete_transcript_removes_it(store):
    t = store.add_transcript("Title", "General")
    store.delete_transcript(t.id)
    assert store.transcripts == []

def test_delete_transcript_leaves_others_untouched(store):
    t1 = store.add_transcript("First", "General")
    t2 = store.add_transcript("Second", "General")
    store.delete_transcript(t1.id)
    assert len(store.transcripts) == 1
    assert store.transcripts[0].id == t2.id

def test_delete_nonexistent_transcript_is_a_safe_no_op(store):
    store.add_transcript("Title", "General")
    store.delete_transcript(999)
    assert len(store.transcripts) == 1


# ---- Persistence ----

def test_persists_and_reloads_full_state_correctly(tmp_path):
    directory = str(tmp_path)

    first = TranscriptStore(data_directory=directory)
    first.add_space("Work")
    t1 = first.add_transcript("Lecture notes", "General", wpm=450)
    first.add_transcript("Meeting recap", "Work")
    first.set_transcript_text(t1.id, "Hello world")
    first.set_transcript_position(t1.id, 3)
    first.set_transcript_paused(t1.id, True)
    first.switch_to_space("General")

    second = TranscriptStore(data_directory=directory)

    assert second.spaces == ["General", "Work"]
    assert second.current_space == "General"
    assert len(second.transcripts) == 2

    reloaded_t1 = next(t for t in second.transcripts if t.id == t1.id)
    assert reloaded_t1.title == "Lecture notes"
    assert reloaded_t1.wpm == 450
    assert reloaded_t1.raw_text == "Hello world"
    assert reloaded_t1.position == 3
    assert reloaded_t1.is_paused is True

def test_next_id_continues_incrementing_after_reload(tmp_path):
    directory = str(tmp_path)

    first = TranscriptStore(data_directory=directory)
    first.add_transcript("First", "General")
    first.add_transcript("Second", "General")

    second = TranscriptStore(data_directory=directory)
    third = second.add_transcript("Third", "General")

    assert third.id == 3  # continues correctly, does not reset to 1

def test_missing_data_file_falls_back_to_fresh_defaults(tmp_path):
    # No data.json exists yet in this fresh tmp_path — same situation as
    # a genuinely first-ever launch of the app.
    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.spaces == ["General"]
    assert store.transcripts == []

def test_corrupted_data_file_falls_back_to_fresh_defaults(tmp_path):
    data_file = tmp_path / "data.json"
    data_file.write_text("{not valid json!!!", encoding="utf-8")

    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.spaces == ["General"]
    assert store.transcripts == []

def test_out_of_range_current_space_index_clamps_on_load(tmp_path):
    """The clamp min(loaded_index, len(spaces) - 1) in __init__ is
    defensive code for a state that can't currently arise through normal
    app use (spaces only ever grow) — but it exists, so it's worth
    confirming it actually protects against a hand-edited or corrupted
    data file claiming an index the current spaces list can't support."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({
        "next_id": 1,
        "current_space_index": 5,
        "spaces": ["General"],
        "transcripts": [],
    }), encoding="utf-8")

    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.current_space == "General"


# ---- set_data_directory ----

def test_set_data_directory_saves_to_new_location(tmp_path):
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    old_dir.mkdir()
    new_dir.mkdir()

    store = TranscriptStore(data_directory=str(old_dir))
    store.add_transcript("Test", "General")
    store.set_data_directory(str(new_dir))

    assert (new_dir / "data.json").exists()
    reloaded = TranscriptStore(data_directory=str(new_dir))
    assert len(reloaded.transcripts) == 1
    assert reloaded.transcripts[0].title == "Test"

def test_set_data_directory_does_not_delete_old_location(tmp_path):
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    old_dir.mkdir()
    new_dir.mkdir()

    store = TranscriptStore(data_directory=str(old_dir))
    store.add_transcript("Test", "General")
    store.set_data_directory(str(new_dir))

    assert (old_dir / "data.json").exists()