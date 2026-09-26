import json
import pytest
from core.transcript_store import TranscriptStore


@pytest.fixture
def store(tmp_path):
    """A fresh TranscriptStore in a throwaway temporary folder. tmp_path is
    a built in pytest fixture, so this never touches your real
    ~/.rsvp_reader data."""
    return TranscriptStore(data_directory=str(tmp_path))


# A fresh store's defaults

def test_fresh_store_has_one_default_space():
    fresh_store = TranscriptStore(data_directory="unused")  # no file exists yet, so nothing is read or written
    assert fresh_store.spaces == ["General"]

def test_fresh_store_default_space_is_current(store):
    assert store.current_space == "General"
    assert store.default_space == "General"

def test_fresh_store_has_no_transcripts(store):
    assert store.transcripts == []
    assert store.transcripts_in_current_space == []


# add_space

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
    assert store.current_space == "General"  # didn't switch, since nothing was added


# switch_to_space

def test_switch_to_space_changes_current_space(store):
    store.add_space("Work")
    store.switch_to_space("General")
    assert store.current_space == "General"

def test_switch_to_nonexistent_space_is_a_safe_no_op(store):
    store.switch_to_space("Does Not Exist")
    assert store.current_space == "General"  # unchanged


# add_transcript

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
    assert t2.id == 2  # continues from next_id and doesn't reuse the deleted id

def test_add_transcript_defaults_session_stats_to_zero(store):
    t = store.add_transcript("Title", "General")
    assert t.times_read == 0
    assert t.total_words_read == 0
    assert t.total_time_spent_seconds == 0


# transcripts and transcripts_in_current_space

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


# Setters for a single transcript

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
    # Every setter uses the same pattern, a _find_transcript call followed
    # by an `if t:` guard. This checks that pattern with one setter instead
    # of repeating it for all of them.
    store.add_transcript("Title", "General")
    store.set_transcript_text(999, "should not crash or change anything")
    assert store.transcripts[0].raw_text == ""


# add_session_stats

def test_add_session_stats_adds_words_and_time(store):
    t = store.add_transcript("Title", "General")
    store.add_session_stats(t.id, words_read=120, active_seconds=30)
    updated = store.transcripts[0]
    assert updated.total_words_read == 120
    assert updated.total_time_spent_seconds == 30

def test_add_session_stats_increments_times_read_when_at_or_above_floor(store):
    t = store.add_transcript("Title", "General")
    store.add_session_stats(t.id, words_read=50, active_seconds=store.MIN_ACTIVE_SECONDS_TO_COUNT_AS_READ)
    assert store.transcripts[0].times_read == 1

def test_add_session_stats_does_not_increment_times_read_below_floor(store):
    t = store.add_transcript("Title", "General")
    store.add_session_stats(t.id, words_read=2, active_seconds=store.MIN_ACTIVE_SECONDS_TO_COUNT_AS_READ - 0.5)
    assert store.transcripts[0].times_read == 0

def test_add_session_stats_still_adds_words_and_time_below_floor(store):
    """The minimum time only decides whether times_read goes up. A short
    session's words and time are still kept, since some real reading did
    happen, even if it wasn't enough to count as a full read. See the
    add_session_stats() docstring."""
    t = store.add_transcript("Title", "General")
    store.add_session_stats(t.id, words_read=4, active_seconds=1)
    updated = store.transcripts[0]
    assert updated.times_read == 0
    assert updated.total_words_read == 4
    assert updated.total_time_spent_seconds == 1

def test_add_session_stats_accumulates_across_multiple_sessions(store):
    t = store.add_transcript("Title", "General")
    store.add_session_stats(t.id, words_read=100, active_seconds=20)
    store.add_session_stats(t.id, words_read=50, active_seconds=10)
    updated = store.transcripts[0]
    assert updated.times_read == 2
    assert updated.total_words_read == 150
    assert updated.total_time_spent_seconds == 30

def test_add_session_stats_rounds_active_seconds_for_storage(store):
    t = store.add_transcript("Title", "General")
    store.add_session_stats(t.id, words_read=10, active_seconds=12.6)
    assert store.transcripts[0].total_time_spent_seconds == 13

def test_add_session_stats_zero_words_read_is_not_special_cased(store):
    """A session that ends before moving past the first word is a normal
    call. words_read=0 just adds nothing to the word total, and times_read
    follows the same minimum time rule as any other call."""
    t = store.add_transcript("Title", "General")
    store.add_session_stats(t.id, words_read=0, active_seconds=store.MIN_ACTIVE_SECONDS_TO_COUNT_AS_READ)
    updated = store.transcripts[0]
    assert updated.total_words_read == 0
    assert updated.times_read == 1

def test_add_session_stats_on_nonexistent_id_is_a_safe_no_op(store):
    store.add_transcript("Title", "General")
    store.add_session_stats(999, words_read=100, active_seconds=30)  # should not crash or change anything
    updated = store.transcripts[0]
    assert updated.times_read == 0
    assert updated.total_words_read == 0
    assert updated.total_time_spent_seconds == 0


# delete_transcript

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


# Saving and loading

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

def test_session_stats_persist_across_reload(tmp_path):
    directory = str(tmp_path)

    first = TranscriptStore(data_directory=directory)
    t1 = first.add_transcript("Lecture notes", "General")
    first.add_session_stats(t1.id, words_read=200, active_seconds=45)

    second = TranscriptStore(data_directory=directory)
    reloaded_t1 = next(t for t in second.transcripts if t.id == t1.id)
    assert reloaded_t1.times_read == 1
    assert reloaded_t1.total_words_read == 200
    assert reloaded_t1.total_time_spent_seconds == 45

def test_next_id_continues_incrementing_after_reload(tmp_path):
    directory = str(tmp_path)

    first = TranscriptStore(data_directory=directory)
    first.add_transcript("First", "General")
    first.add_transcript("Second", "General")

    second = TranscriptStore(data_directory=directory)
    third = second.add_transcript("Third", "General")

    assert third.id == 3  # keeps counting and doesn't reset to 1

def test_missing_data_file_falls_back_to_fresh_defaults(tmp_path):
    # There's no data.json in this new tmp_path yet, just like the very
    # first launch of the app.
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
    """The min(loaded_index, len(spaces) - 1) clamp in __init__ guards
    against a state normal use can't produce right now. This checks that it
    protects against a hand edited or corrupted data file pointing at a
    space index that doesn't exist."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({
        "next_id": 1,
        "current_space_index": 5,
        "spaces": ["General"],
        "transcripts": [],
    }), encoding="utf-8")

    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.current_space == "General"

def test_old_save_file_missing_stats_fields_defaults_them_to_zero(tmp_path):
    """An older save file has no times_read, total_words_read or
    total_time_spent_seconds on its transcripts. This checks that
    parse_data() in core/storage.py falls back to the dataclass default of
    0 for a missing key. No explicit backfill is needed, unlike the color
    flag fields (see core/models.py)."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({
        "next_id": 2,
        "current_space_index": 0,
        "spaces": ["General"],
        "transcripts": [{"id": 1, "title": "Old Transcript", "space": "General"}],
    }), encoding="utf-8")

    store = TranscriptStore(data_directory=str(tmp_path))
    t = store.transcripts[0]
    assert t.times_read == 0
    assert t.total_words_read == 0
    assert t.total_time_spent_seconds == 0


# set_data_directory

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