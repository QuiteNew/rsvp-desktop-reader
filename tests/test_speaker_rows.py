"""Tests for the speaker list rows in core/speakers.py: speaker_rows() (what the
Configure speaker cues window shows for a transcript), speaker_row_name() and
speakers_to_save() (what it saves back).

TEXT: Ann and Bob start two lines each, so Auto switches them on. Cat starts
only one, so Auto leaves her off, but she still gets a row."""

from dataclasses import replace

from core.speakers import (
    AUTO_MIN_APPEARANCES, MAX_LABEL_CHARS, SpeakerRow, clean_custom_speakers,
    speaker_row_name, speaker_rows, speakers_to_save,
)

TEXT = "Ann: hi\nBob: yo\nCat: once\nAnn: and\nBob: so"


def _rows(custom=None):
    return {row.key: row for row in speaker_rows(TEXT, custom)}


def _changed(rows, key, **changes):
    """The rows with one of them changed, the way the window changes them."""
    return [replace(row, **changes) if row.key == key else row for row in rows]


# --- speaker_rows() -----------------------------------------------------------

def test_under_auto_every_label_gets_a_row_and_autos_picks_are_ticked():
    assert speaker_rows(TEXT) == [
        SpeakerRow("ann", "Ann", 2, True, "Ann"),
        SpeakerRow("bob", "Bob", 2, True, "Bob"),
        SpeakerRow("cat", "Cat", 1, False, "Cat"),
    ]


def test_auto_still_needs_two_appearances():
    # Pinned, so a change to the rule shows up here as well.
    assert AUTO_MIN_APPEARANCES == 2


def test_rows_come_in_order_of_first_appearance():
    rows = speaker_rows("Zed: a\nAmy: b\nZed: c\nAmy: d")
    assert [row.key for row in rows] == ["zed", "amy"]


def test_rows_follow_the_transcripts_own_list():
    rows = _rows({"cat": "Kat", "ann": "Ann"})
    assert (rows["ann"].ticked, rows["ann"].name) == (True, "Ann")
    assert (rows["bob"].ticked, rows["bob"].name) == (False, "Bob")
    assert (rows["cat"].ticked, rows["cat"].name) == (True, "Kat")


def test_an_empty_own_list_ticks_nothing():
    assert [row.ticked for row in speaker_rows(TEXT, {})] == [False, False, False]


def test_a_name_in_the_own_list_that_is_not_in_the_text_gets_no_row():
    assert set(_rows({"dan": "Dan", "ann": "Ann"})) == {"ann", "bob", "cat"}


def test_unnamed_changes_and_text_without_labels_give_no_rows():
    assert speaker_rows(">> hello\n>> there") == []
    assert speaker_rows("just some words") == []
    assert speaker_rows("") == []


# --- speaker_row_name() -------------------------------------------------------

def _named(name, label="Ann"):
    return speaker_row_name(SpeakerRow("ann", label, 2, True, name))


def test_a_typed_name_has_its_spaces_squeezed():
    assert _named("  Dr.   Who  ") == "Dr. Who"


def test_an_empty_name_falls_back_to_the_label():
    assert _named("") == "Ann"
    assert _named("   ") == "Ann"


def test_a_long_name_is_cut_to_the_limit_without_a_space_at_the_end():
    assert MAX_LABEL_CHARS == 30
    assert _named("x" * 40) == "x" * 30
    # Cut after 30 characters this would end in a space.
    assert _named("y" * 29 + " zzz") == "y" * 29


# --- speakers_to_save() -------------------------------------------------------

def test_rows_left_as_auto_made_them_save_as_automatic():
    assert speakers_to_save(speaker_rows(TEXT)) is None


def test_ticking_a_row_saves_a_custom_list():
    rows = _changed(speaker_rows(TEXT), "cat", ticked=True)
    assert speakers_to_save(rows) == {"ann": "Ann", "bob": "Bob", "cat": "Cat"}


def test_ticking_and_unticking_again_is_automatic_again():
    rows = _changed(speaker_rows(TEXT), "cat", ticked=True)
    rows = _changed(rows, "cat", ticked=False)
    assert speakers_to_save(rows) is None


def test_unticking_a_row_leaves_it_out():
    rows = _changed(speaker_rows(TEXT), "bob", ticked=False)
    assert speakers_to_save(rows) == {"ann": "Ann"}


def test_a_new_name_is_saved():
    rows = _changed(speaker_rows(TEXT), "ann", name="Annie")
    assert speakers_to_save(rows) == {"ann": "Annie", "bob": "Bob"}


def test_the_same_name_on_two_rows_merges_them():
    rows = _changed(speaker_rows(TEXT), "bob", name="Ann")
    assert speakers_to_save(rows) == {"ann": "Ann", "bob": "Ann"}


def test_a_name_that_only_differs_in_spaces_is_still_automatic():
    rows = _changed(speaker_rows(TEXT), "ann", name="  Ann ")
    assert speakers_to_save(rows) is None


def test_the_name_of_an_unticked_row_does_not_matter():
    rows = _changed(speaker_rows(TEXT), "cat", name="Kat")
    assert speakers_to_save(rows) is None


def test_nothing_ticked_is_an_empty_list_and_not_automatic():
    rows = [replace(row, ticked=False) for row in speaker_rows(TEXT)]
    assert speakers_to_save(rows) == {}


def test_nothing_ticked_where_auto_picks_nobody_is_automatic():
    assert speakers_to_save(speaker_rows("Ann: once\nBob: once")) is None


def test_an_own_list_that_matches_auto_saves_as_automatic():
    assert speakers_to_save(speaker_rows(TEXT, {"ann": "Ann", "bob": "Bob"})) is None


def test_rows_can_come_from_any_iterable():
    # Looked through twice inside, so a generator has to work too.
    assert speakers_to_save(row for row in speaker_rows(TEXT)) is None


def test_an_own_list_comes_back_unchanged():
    custom = {"cat": "Kat", "bob": "Ann", "ann": "Ann"}
    saved = speakers_to_save(speaker_rows(TEXT, custom))
    assert saved == custom
    assert clean_custom_speakers(saved) == saved
