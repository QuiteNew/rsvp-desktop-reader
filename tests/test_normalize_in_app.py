"""Normalize and Revert the way the app keeps them.

The edit box's Normalize button has its own tests (test_normalizer.py for the
tidying, the transcript input tests for the icon). This file is about the app's
side: what it saves when the button is clicked, what ends Revert, and what is
still there when a transcript is left and opened again. It clicks the real
button in a real app and looks at what the store ends up holding, both in
memory and on disk.

Revert only lasts while the text is exactly what normalizing produced. The app
checks that whenever the edit box is saved, which happens when another
transcript is opened, when the app closes, and when Start reading is clicked.
So most of these tests make a change, leave the transcript and look at what was
kept.
"""
import pytest

from core.transcript_store import TranscriptStore
from tk_helpers import click_button, settle

WRAPPED = "The meeting started late\nbecause the speaker was\nstuck in traffic.\n\nSecond paragraph here."
NORMALIZED = "The meeting started late because the speaker was stuck in traffic.\n\nSecond paragraph here."
CLEAN = "Nothing in here needs tidying."


# ---- helpers ----

def _add(app, title, draft="", raw="", stopped=False):
    """A transcript in the current space, with a draft, or with text that has
    been read and stopped."""
    store = app.store
    transcript = store.add_transcript(title, store.current_space)
    if draft:
        store.set_transcript_draft_text(transcript.id, draft)
    if raw:
        store.set_transcript_text(transcript.id, raw)
    if stopped:
        store.set_transcript_stopped(transcript.id, True)
    app._refresh_transcript_list()
    settle(app, 200)
    return transcript


def _open(app, transcript):
    app._handle_open_transcript(transcript)
    settle(app, 200)


def _icon(box):
    """Which of the button's two faces is showing."""
    return "Revert" if box.normalize_button.cget("image") is box._revert_image else "Normalize"


def _press(app, box):
    click_button(box.normalize_button)
    settle(app, 100)


def _type(app, box, text):
    """Add to the end of the text, the way typing there would."""
    box.textbox.insert("end", text)
    settle(app, 100)


def _undo_info(transcript):
    return transcript.pre_normalize_text, transcript.normalized_text


def _on_disk(directory, transcript):
    """The transcript as a fresh start of the app would find it."""
    return next(t for t in TranscriptStore(data_directory=str(directory)).transcripts if t.id == transcript.id)


@pytest.fixture
def two(tmp_path, open_real_app):
    """An app with a wrapped draft open in the edit box, and a second
    transcript to leave it for."""
    with open_real_app(tmp_path) as app:
        first = _add(app, "Lecture", draft=WRAPPED)
        other = _add(app, "Other", draft=CLEAN)
        _open(app, first)
        yield app, first, other, tmp_path


# ---- clicking the button ----

def test_normalizing_tidies_the_text_and_keeps_the_way_back(two):
    app, transcript, _, directory = two
    box = app.canvas.input_view
    assert _icon(box) == "Normalize"

    _press(app, box)

    assert box.get_text().strip() == NORMALIZED
    assert _icon(box) == "Revert"
    assert _undo_info(transcript) == (WRAPPED, NORMALIZED)
    assert transcript.draft_text == NORMALIZED
    assert transcript.raw_text == "", "it hasn't been started"
    on_disk = _on_disk(directory, transcript)
    assert _undo_info(on_disk) == (WRAPPED, NORMALIZED)
    assert on_disk.draft_text == NORMALIZED


def test_a_second_click_puts_the_original_back_and_forgets_it(two):
    app, transcript, _, directory = two
    box = app.canvas.input_view

    _press(app, box)
    _press(app, box)

    assert box.get_text().strip() == WRAPPED
    assert _icon(box) == "Normalize"
    assert _undo_info(transcript) == ("", "")
    assert transcript.draft_text == WRAPPED
    on_disk = _on_disk(directory, transcript)
    assert _undo_info(on_disk) == ("", "")
    assert on_disk.draft_text == WRAPPED


def test_text_that_needs_no_tidying_is_left_alone_and_nothing_is_kept(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _add(app, "Tidy", draft=CLEAN)
        _open(app, transcript)
        box = app.canvas.input_view

        _press(app, box)

        assert box.feedback_label.cget("text") == "Nothing to change"
        assert box.get_text().strip() == CLEAN
        assert _icon(box) == "Normalize"
        assert _undo_info(transcript) == ("", "")
        assert transcript.draft_text == CLEAN


def test_normalizing_again_after_an_edit_goes_back_to_the_edited_text(two):
    app, transcript, _, _ = two
    box = app.canvas.input_view
    _press(app, box)
    _type(app, box, "\nand a wrapped line\nthat was added later.")
    edited = box.get_text().strip()

    _press(app, box)

    tidied = box.get_text().strip()
    assert tidied != edited
    assert _undo_info(transcript) == (edited, tidied), "the original to go back to is the edited text"
    _press(app, box)
    assert box.get_text().strip() == edited


# ---- leaving the transcript and coming back ----

def test_revert_is_still_there_after_leaving_and_coming_back_with_the_text_as_it_was(two):
    app, transcript, other, directory = two
    box = app.canvas.input_view
    _press(app, box)

    _open(app, other)
    assert _icon(box) == "Normalize", "the other transcript has nothing to revert"
    assert _undo_info(transcript) == (WRAPPED, NORMALIZED)

    _open(app, transcript)
    assert box.get_text().strip() == NORMALIZED
    assert _icon(box) == "Revert"
    assert _undo_info(_on_disk(directory, transcript)) == (WRAPPED, NORMALIZED)

    _press(app, box)
    assert box.get_text().strip() == WRAPPED


def test_spaces_and_blank_lines_added_at_the_end_dont_end_revert(two):
    app, transcript, other, _ = two
    box = app.canvas.input_view
    _press(app, box)
    _type(app, box, "   \n\n  ")

    _open(app, other)
    _open(app, transcript)

    assert _undo_info(transcript) == (WRAPPED, NORMALIZED)
    assert _icon(box) == "Revert"


def test_an_edit_ends_revert_and_the_edit_is_kept(two):
    app, transcript, other, directory = two
    box = app.canvas.input_view
    _press(app, box)
    _type(app, box, " And one more thing.")
    assert _icon(box) == "Normalize", "the button notices at once"

    _open(app, other)

    edited = NORMALIZED + " And one more thing."
    assert _undo_info(transcript) == ("", "")
    assert transcript.draft_text == edited
    on_disk = _on_disk(directory, transcript)
    assert _undo_info(on_disk) == ("", "")
    assert on_disk.draft_text == edited

    _open(app, transcript)
    assert box.get_text().strip() == edited
    assert _icon(box) == "Normalize"


def test_a_transcript_that_was_never_normalized_has_nothing_cleared(two, monkeypatch):
    app, transcript, other, _ = two
    cleared = []
    monkeypatch.setattr(app.store, "set_transcript_normalization", lambda *args: cleared.append(args))
    _type(app, app.canvas.input_view, " An edit.")

    _open(app, other)
    _open(app, transcript)

    assert transcript.draft_text == WRAPPED + " An edit."
    assert cleared == [], "there was nothing to clear, so nothing was written"


# ---- starting to read ----

def test_start_reading_ends_revert_and_saves_the_tidied_text(two):
    app, transcript, _, directory = two
    box = app.canvas.input_view
    _press(app, box)

    click_button(box.start_button)
    settle(app, 300)
    app.canvas.stop()
    settle(app, 200)

    assert transcript.raw_text == NORMALIZED
    assert transcript.draft_text == ""
    assert _undo_info(transcript) == ("", "")
    assert _undo_info(_on_disk(directory, transcript)) == ("", "")
    assert _icon(box) == "Normalize"


# ---- a transcript that was read and stopped ----

@pytest.fixture
def stopped(tmp_path, open_real_app):
    """The same, but the text is one that was read and stopped, so the edit box
    holds its text and not a draft."""
    with open_real_app(tmp_path) as app:
        transcript = _add(app, "Stopped", raw=WRAPPED, stopped=True)
        other = _add(app, "Other", draft=CLEAN)
        _open(app, transcript)
        yield app, transcript, other


def test_normalizing_a_stopped_transcript_changes_its_text_and_not_its_draft(stopped):
    app, transcript, _ = stopped
    box = app.canvas.input_view
    assert box.get_text().strip() == WRAPPED

    _press(app, box)

    assert transcript.raw_text == NORMALIZED
    assert transcript.draft_text == ""
    assert _undo_info(transcript) == (WRAPPED, NORMALIZED)
    assert _icon(box) == "Revert"

    _press(app, box)

    assert transcript.raw_text == WRAPPED
    assert _undo_info(transcript) == ("", "")


def test_an_edit_to_a_stopped_transcript_ends_revert_and_is_kept_as_its_text(stopped):
    app, transcript, other = stopped
    box = app.canvas.input_view
    _press(app, box)
    _type(app, box, " Edited.")

    _open(app, other)

    assert transcript.raw_text == NORMALIZED + " Edited."
    assert transcript.draft_text == ""
    assert _undo_info(transcript) == ("", "")


# ---- the detached window ----

@pytest.fixture
def detached(tmp_path, open_real_app):
    """The wrapped draft in a detached window, with another transcript open in
    the main one."""
    with open_real_app(tmp_path) as app:
        transcript = _add(app, "Lecture", draft=WRAPPED)
        other = _add(app, "Other", draft=CLEAN)
        _open(app, transcript)
        app.canvas._handle_detach()
        settle(app, 600)
        _open(app, other)
        window = app.canvas._detached_window
        settle(window, 300)
        yield app, window, transcript, tmp_path


def test_normalizing_in_the_detached_window_is_saved_the_same_way(detached):
    app, window, transcript, directory = detached
    box = window.input_view

    _press(window, box)

    assert box.get_text().strip() == NORMALIZED
    assert _icon(box) == "Revert"
    assert _undo_info(transcript) == (WRAPPED, NORMALIZED)
    assert transcript.draft_text == NORMALIZED
    assert _undo_info(_on_disk(directory, transcript)) == (WRAPPED, NORMALIZED)

    _press(window, box)

    assert box.get_text().strip() == WRAPPED
    assert _undo_info(transcript) == ("", "")
    assert transcript.draft_text == WRAPPED


def test_an_edit_in_the_detached_window_ends_revert_when_it_is_closed(detached):
    app, window, transcript, directory = detached
    box = window.input_view
    _press(window, box)
    _type(window, box, " Late edit.")

    app.canvas._handle_reattach()
    settle(app, 300)

    assert transcript.draft_text == NORMALIZED + " Late edit."
    assert _undo_info(transcript) == ("", "")
    assert _undo_info(_on_disk(directory, transcript)) == ("", "")
