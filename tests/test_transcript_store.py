import json
import pytest
from core.transcript_store import TranscriptStore
from core.models import Bookmark


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

def test_set_transcript_normalization_saves_both_fields(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_normalization(t.id, "1. Original", "Original")
    assert store.transcripts[0].pre_normalize_text == "1. Original"
    assert store.transcripts[0].normalized_text == "Original"

def test_set_transcript_normalization_with_empty_strings_clears_it(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_normalization(t.id, "1. Original", "Original")
    store.set_transcript_normalization(t.id, "", "")
    assert store.transcripts[0].pre_normalize_text == ""
    assert store.transcripts[0].normalized_text == ""

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

def test_normalization_undo_information_persists_across_reload(tmp_path):
    # So Revert is still offered after switching transcripts or
    # restarting the app.
    directory = str(tmp_path)

    first = TranscriptStore(data_directory=directory)
    t1 = first.add_transcript("Lecture notes", "General")
    first.set_transcript_normalization(t1.id, "1. Original", "Original")

    second = TranscriptStore(data_directory=directory)
    reloaded_t1 = next(t for t in second.transcripts if t.id == t1.id)
    assert reloaded_t1.pre_normalize_text == "1. Original"
    assert reloaded_t1.normalized_text == "Original"

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

def test_old_save_file_missing_normalization_fields_defaults_them_to_empty(tmp_path):
    """Like the stats fields above, a save file from before the Normalize
    button has no pre_normalize_text or normalized_text. Both fall back
    to the dataclass default, which means "nothing to revert"."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({
        "next_id": 2,
        "current_space_index": 0,
        "spaces": ["General"],
        "transcripts": [{"id": 1, "title": "Old Transcript", "space": "General"}],
    }), encoding="utf-8")

    store = TranscriptStore(data_directory=str(tmp_path))
    t = store.transcripts[0]
    assert t.pre_normalize_text == ""
    assert t.normalized_text == ""


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

# Bookmarks tests below:

def test_add_bookmark_stores_index_and_snippet(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 5, "the quick brown")
    bms = store.transcripts[0].bookmarks
    assert len(bms) == 1
    assert isinstance(bms[0], Bookmark)
    assert bms[0].index == 5
    assert bms[0].snippet == "the quick brown"
    assert bms[0].created_at  # a non-empty ISO-8601 timestamp string

def test_add_bookmark_is_deduped_by_index(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 5, "first")
    store.add_bookmark(t.id, 5, "second attempt")  # same index -> no-op
    bms = store.transcripts[0].bookmarks
    assert len(bms) == 1
    assert bms[0].snippet == "first"  # the original is kept, not replaced

def test_add_bookmark_keeps_list_sorted_by_index(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 10, "ten")
    store.add_bookmark(t.id, 2, "two")
    store.add_bookmark(t.id, 7, "seven")
    assert [b.index for b in store.transcripts[0].bookmarks] == [2, 7, 10]

def test_add_bookmark_on_nonexistent_transcript_is_a_safe_no_op(store):
    store.add_transcript("Title", "General")
    store.add_bookmark(999, 1, "nope")
    assert store.transcripts[0].bookmarks == []

def test_remove_bookmark_removes_by_index(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 2, "two")
    store.add_bookmark(t.id, 5, "five")
    store.remove_bookmark(t.id, 2)
    assert [b.index for b in store.transcripts[0].bookmarks] == [5]

def test_remove_bookmark_nonexistent_index_is_a_safe_no_op(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 2, "two")
    store.remove_bookmark(t.id, 99)
    assert [b.index for b in store.transcripts[0].bookmarks] == [2]

def test_remove_bookmark_on_nonexistent_transcript_is_a_safe_no_op(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 2, "two")
    store.remove_bookmark(999, 2)
    assert len(store.transcripts[0].bookmarks) == 1

def test_new_transcript_has_no_bookmarks(store):
    store.add_transcript("Title", "General")
    assert store.transcripts[0].bookmarks == []

def test_bookmarks_persist_across_reload(tmp_path):
    directory = str(tmp_path)
    first = TranscriptStore(data_directory=directory)
    t = first.add_transcript("Doc", "General")
    first.add_bookmark(t.id, 3, "three")
    first.add_bookmark(t.id, 8, "eight")

    second = TranscriptStore(data_directory=directory)
    reloaded = next(x for x in second.transcripts if x.id == t.id)
    assert [b.index for b in reloaded.bookmarks] == [3, 8]
    assert reloaded.bookmarks[0].snippet == "three"
    # Rebuilt as real Bookmark objects, not plain dicts (see core/storage.py).
    assert all(isinstance(b, Bookmark) for b in reloaded.bookmarks)

def test_old_save_file_missing_bookmarks_field_defaults_to_empty_list(tmp_path):
    """A save file from before bookmarks existed has no "bookmarks" key on
    its transcripts. Transcript's field(default_factory=list) default means
    it loads as an empty list, no explicit backfill needed, the same as the
    stats and normalization fields."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({
        "next_id": 2,
        "current_space_index": 0,
        "spaces": ["General"],
        "transcripts": [{"id": 1, "title": "Old Transcript", "space": "General"}],
    }), encoding="utf-8")

    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.transcripts[0].bookmarks == []


# Bookmark labels

def test_new_bookmark_has_empty_label(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 5, "the quick brown")
    assert store.transcripts[0].bookmarks[0].label == ""

def test_set_bookmark_label_sets_the_label(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 5, "the quick brown")
    store.set_bookmark_label(t.id, 5, "Chapter 2 start")
    assert store.transcripts[0].bookmarks[0].label == "Chapter 2 start"

def test_set_bookmark_label_overwrites_an_existing_label(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 5, "snippet")
    store.set_bookmark_label(t.id, 5, "First name")
    store.set_bookmark_label(t.id, 5, "Second name")
    assert store.transcripts[0].bookmarks[0].label == "Second name"

def test_set_bookmark_label_empty_string_clears_it(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 5, "snippet")
    store.set_bookmark_label(t.id, 5, "A name")
    store.set_bookmark_label(t.id, 5, "")
    assert store.transcripts[0].bookmarks[0].label == ""

def test_set_bookmark_label_does_not_touch_snippet_or_index(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 5, "the quick brown")
    store.set_bookmark_label(t.id, 5, "My label")
    b = store.transcripts[0].bookmarks[0]
    assert b.index == 5
    assert b.snippet == "the quick brown"

def test_set_bookmark_label_only_affects_the_matching_index(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 2, "two")
    store.add_bookmark(t.id, 5, "five")
    store.set_bookmark_label(t.id, 5, "Only five")
    by_index = {b.index: b.label for b in store.transcripts[0].bookmarks}
    assert by_index == {2: "", 5: "Only five"}

def test_set_bookmark_label_nonexistent_index_is_a_safe_no_op(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 2, "two")
    store.set_bookmark_label(t.id, 99, "nope")
    assert store.transcripts[0].bookmarks[0].label == ""

def test_set_bookmark_label_on_nonexistent_transcript_is_a_safe_no_op(store):
    t = store.add_transcript("Title", "General")
    store.add_bookmark(t.id, 2, "two")
    store.set_bookmark_label(999, 2, "nope")  # should not crash or change anything
    assert store.transcripts[0].bookmarks[0].label == ""

def test_bookmark_label_persists_across_reload(tmp_path):
    directory = str(tmp_path)
    first = TranscriptStore(data_directory=directory)
    t = first.add_transcript("Doc", "General")
    first.add_bookmark(t.id, 3, "three")
    first.set_bookmark_label(t.id, 3, "The good part")

    second = TranscriptStore(data_directory=directory)
    reloaded = next(x for x in second.transcripts if x.id == t.id)
    assert reloaded.bookmarks[0].label == "The good part"

def test_old_save_file_bookmark_missing_label_defaults_to_empty(tmp_path):
    """A bookmark saved before labels existed has no "label" key. parse_data()
    in core/storage.py filters to the Bookmark dataclass fields and rebuilds,
    so the missing key falls back to the field default of "", the same way a
    missing stats or normalization field does on a Transcript."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({
        "next_id": 2,
        "current_space_index": 0,
        "spaces": ["General"],
        "transcripts": [{
            "id": 1, "title": "Doc", "space": "General",
            "bookmarks": [{"index": 3, "snippet": "three", "created_at": "2020-01-01T00:00:00+00:00"}],
        }],
    }), encoding="utf-8")

    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.transcripts[0].bookmarks[0].label == ""


# rename_space

def test_rename_space_renames_and_returns_true(store):
    store.add_space("Work")
    assert store.rename_space("Work", "Office") is True
    assert "Office" in store.spaces
    assert "Work" not in store.spaces

def test_rename_space_reassigns_transcripts_in_that_space(store):
    store.add_space("Work")
    store.add_transcript("Doc", "Work")
    store.rename_space("Work", "Office")
    assert store.transcripts[0].space == "Office"

def test_rename_space_leaves_other_spaces_transcripts_untouched(store):
    store.add_space("Work")
    store.add_transcript("Keep", "General")
    store.add_transcript("Move", "Work")
    store.rename_space("Work", "Office")
    by_title = {t.title: t.space for t in store.transcripts}
    assert by_title["Keep"] == "General"  # a transcript in another space is not touched
    assert by_title["Move"] == "Office"

def test_rename_space_unknown_name_returns_false(store):
    assert store.rename_space("Nope", "Whatever") is False
    assert store.spaces == ["General"]

def test_rename_space_blank_new_name_returns_false(store):
    store.add_space("Work")
    assert store.rename_space("Work", "   ") is False
    assert store.spaces == ["General", "Work"]

def test_rename_space_same_name_returns_false(store):
    store.add_space("Work")
    assert store.rename_space("Work", "Work") is False
    assert store.spaces == ["General", "Work"]

def test_rename_space_to_an_existing_name_returns_false(store):
    # Renaming "Work" to "General" would collide with the space that already exists.
    store.add_space("Work")
    assert store.rename_space("Work", "General") is False
    assert store.spaces == ["General", "Work"]

def test_rename_space_strips_whitespace_from_new_name(store):
    store.add_space("Work")
    store.rename_space("Work", "  Office  ")
    assert "Office" in store.spaces
    assert "  Office  " not in store.spaces

def test_rename_current_space_keeps_it_current(store):
    store.add_space("Work")  # add_space switches current to the new space
    assert store.current_space == "Work"
    store.rename_space("Work", "Office")
    # Renamed in place at the same index, so current_space reads the new name.
    assert store.current_space == "Office"

def test_rename_space_persists_across_reload(tmp_path):
    directory = str(tmp_path)
    first = TranscriptStore(data_directory=directory)
    first.add_space("Work")
    t = first.add_transcript("Doc", "Work")
    first.rename_space("Work", "Office")

    second = TranscriptStore(data_directory=directory)
    assert "Office" in second.spaces
    assert "Work" not in second.spaces
    reloaded = next(x for x in second.transcripts if x.id == t.id)
    assert reloaded.space == "Office"


# delete_space

def test_delete_space_removes_an_empty_space_and_returns_true(store):
    store.add_space("Work")           # current is now "Work", and it has no transcripts
    store.switch_to_space("General")  # so "Work" isn't the current space when we delete it
    assert store.delete_space("Work") is True
    assert store.spaces == ["General"]

def test_delete_space_unknown_name_returns_false(store):
    store.add_space("Work")
    assert store.delete_space("Nope") is False
    assert store.spaces == ["General", "Work"]

def test_delete_space_refuses_the_last_remaining_space(store):
    # A fresh store has only "General", and there always has to be at least one.
    assert store.delete_space("General") is False
    assert store.spaces == ["General"]

def test_delete_space_refuses_a_space_that_still_has_transcripts(store):
    store.add_space("Work")
    store.add_transcript("Doc", "General")
    assert store.delete_space("General") is False
    assert store.spaces == ["General", "Work"]

def test_delete_current_space_falls_back_to_the_first_space(store):
    store.add_space("Work")  # current is "Work", empty
    assert store.current_space == "Work"
    assert store.delete_space("Work") is True
    assert store.current_space == "General"  # fell back to index 0

def test_delete_a_space_before_the_current_one_keeps_current_correct(store):
    # End state before the delete: ["General", "Work", "Reading"] with "Reading" current.
    store.add_space("Work")
    store.add_space("Reading")
    assert store.current_space == "Reading"
    store.delete_space("Work")  # deleting a space that sits before the current one
    assert store.spaces == ["General", "Reading"]
    # current is re-derived from the name, so it still points at "Reading", not a stale index.
    assert store.current_space == "Reading"

def test_delete_space_persists_across_reload(tmp_path):
    directory = str(tmp_path)
    first = TranscriptStore(data_directory=directory)
    first.add_space("Work")
    first.switch_to_space("General")
    first.delete_space("Work")

    second = TranscriptStore(data_directory=directory)
    assert second.spaces == ["General"]


# set_transcript_space

def test_set_transcript_space_moves_to_another_space(store):
    store.add_space("Work")
    t = store.add_transcript("Doc", "General")
    store.set_transcript_space(t.id, "Work")
    assert store.transcripts[0].space == "Work"

def test_set_transcript_space_unknown_space_is_a_safe_no_op(store):
    # The UI only ever offers real spaces, so this guard is a defensive
    # backstop: an unknown destination leaves the transcript where it was.
    t = store.add_transcript("Doc", "General")
    store.set_transcript_space(t.id, "Does Not Exist")
    assert store.transcripts[0].space == "General"

def test_set_transcript_space_on_nonexistent_id_is_a_safe_no_op(store):
    store.add_space("Work")
    store.add_transcript("Doc", "General")
    store.set_transcript_space(999, "Work")  # should not crash or change anything
    assert store.transcripts[0].space == "General"


# set_transcript_title

def test_set_transcript_title_updates_title(store):
    t = store.add_transcript("Old Title", "General")
    store.set_transcript_title(t.id, "New Title")
    assert store.transcripts[0].title == "New Title"

def test_set_transcript_title_on_nonexistent_id_is_a_safe_no_op(store):
    store.add_transcript("Old Title", "General")
    store.set_transcript_title(999, "Should Not Apply")
    assert store.transcripts[0].title == "Old Title"


# set_transcript_font_size

def test_set_transcript_font_size_updates_font_size(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_font_size(t.id, 48)
    assert store.transcripts[0].font_size == 48

def test_set_transcript_font_size_on_nonexistent_id_is_a_safe_no_op(store):
    store.add_transcript("Title", "General")
    store.set_transcript_font_size(999, 48)
    assert store.transcripts[0].font_size == 32  # the default, unchanged


# resync_default_reading_colors

def test_resync_updates_a_transcript_still_tracking_the_defaults(store):
    # A freshly added transcript keeps the dataclass default flags, so all
    # three colors are still tracking the theme default.
    store.add_transcript("Title", "General")
    store.resync_default_reading_colors("#000000", "#111111", "#222222")
    updated = store.transcripts[0]
    assert updated.font_color == "#000000"
    assert updated.highlight_color == "#111111"
    assert updated.background_color == "#222222"

def test_resync_leaves_a_hand_picked_color_but_updates_the_still_default_ones(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_font_color(t.id, "#AAAAAA")  # retires the font color from theme-tracking
    store.resync_default_reading_colors("#000000", "#111111", "#222222")
    updated = store.transcripts[0]
    assert updated.font_color == "#AAAAAA"        # hand-picked, left alone
    assert updated.highlight_color == "#111111"   # still default, updated
    assert updated.background_color == "#222222"  # still default, updated

def test_resync_leaves_a_fully_hand_picked_transcript_untouched(store):
    t = store.add_transcript("Title", "General")
    store.set_transcript_font_color(t.id, "#AAAAAA")
    store.set_transcript_highlight_color(t.id, "#BBBBBB")
    store.set_transcript_background_color(t.id, "#CCCCCC")
    store.resync_default_reading_colors("#000000", "#111111", "#222222")
    updated = store.transcripts[0]
    assert updated.font_color == "#AAAAAA"
    assert updated.highlight_color == "#BBBBBB"
    assert updated.background_color == "#CCCCCC"

def test_resync_to_the_colors_already_in_place_changes_nothing(store):
    # The transcript already holds the default colors, so every != guard
    # fails and nothing is changed (internally, nothing is saved either).
    store.add_transcript("Title", "General")
    store.resync_default_reading_colors("#FFFFFF", "#E74C3C", "#1E1E1E")
    updated = store.transcripts[0]
    assert updated.font_color == "#FFFFFF"
    assert updated.highlight_color == "#E74C3C"
    assert updated.background_color == "#1E1E1E"

def test_resync_persists_updated_colors_across_reload(tmp_path):
    directory = str(tmp_path)
    first = TranscriptStore(data_directory=directory)
    t = first.add_transcript("Title", "General")
    first.resync_default_reading_colors("#000000", "#111111", "#222222")

    second = TranscriptStore(data_directory=directory)
    reloaded = next(x for x in second.transcripts if x.id == t.id)
    assert reloaded.font_color == "#000000"
    assert reloaded.highlight_color == "#111111"
    assert reloaded.background_color == "#222222"




# flush

def test_flush_forces_a_throttled_wpm_change_to_disk(tmp_path):
    # set_transcript_wpm() is throttled (it's the footer's live WPM drag), so
    # a change can sit in memory unsaved. flush() forces it out, which is what
    # gui/app.py relies on at app close. The first throttled write saves (the
    # throttle has never fired), a second one moments later is held back (the
    # two calls are microseconds apart, well inside the throttle window), and
    # flush() then persists it.
    directory = str(tmp_path)
    first = TranscriptStore(data_directory=directory)
    t = first.add_transcript("Doc", "General")
    first.set_transcript_wpm(t.id, 500)  # saved: the throttle has never fired
    first.set_transcript_wpm(t.id, 600)  # throttled: in memory only
    assert first.transcripts[0].wpm == 600

    before_flush = TranscriptStore(data_directory=directory)
    assert next(x for x in before_flush.transcripts if x.id == t.id).wpm == 500

    first.flush()
    after_flush = TranscriptStore(data_directory=directory)
    assert next(x for x in after_flush.transcripts if x.id == t.id).wpm == 600