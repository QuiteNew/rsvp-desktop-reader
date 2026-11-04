"""Tests for the rows of the sidebar's transcript list
(gui/components/transcript_list_body.py) as a person uses them, and for what the
app does with each action (gui/app.py): a click on a title opens that
transcript, a double click renames it, a right click offers to move it to
another space, and the X asks about deleting it.

Sorting and searching have their own tests, in test_transcript_sort.py and
test_transcript_list_current.py. These are the parts of a row that were never
pressed. Each test builds the real app with open_real_app (conftest.py) and
sends real clicks and keys to the row, the way test_bookmarks_list.py does.

A double click renames and opens at the same time: its first press is an
ordinary click, so the transcript opens, and the box for the new title comes up
on the second.

Esc closes a rename box, and in the main window Esc also stops reading. The app
leaves the second alone while a text box has the keyboard, so Esc in the rename
box has to cancel the rename and nothing else. The last tests check that, and
that Esc does stop reading when no box has the keyboard, so the first isn't true
only because Esc never does anything.

The right-click menu is a real Tk menu that is stopped just before it would pop
up. A pop-up menu takes over until it's dismissed, which would hold a test up for
good on Windows. The dialogs the app might open are stood in for, since what's
tested here is which one opens and for what."""

import json
import tkinter

import pytest

from test_space_and_move_guards import Opened
from tk_helpers import click, click_button, settle

WORDS = [f"w{i}" for i in range(300)]
TEXT = " ".join(WORDS)


def _add(app, *titles, paused=True):
    """Add transcripts with some text and show them in the sidebar. They open
    paused unless told otherwise. Returns them in order."""
    store = app.store
    added = []
    for title in titles:
        transcript = store.add_transcript(title, store.current_space)
        store.set_transcript_text(transcript.id, TEXT)
        store.set_transcript_paused(transcript.id, paused)
        added.append(transcript)
    app._refresh_transcript_list()
    settle(app, 300)
    return added


def parts(app, transcript):
    """The three things in a row, in the order they're packed: the X button, the
    title, and the box that takes the title's place while renaming."""
    delete_button, title_label, title_entry = app.list_body._rows[transcript.id].winfo_children()
    return delete_button, title_label, title_entry


def click_title(app, transcript, times=1):
    click(parts(app, transcript)[1]._label, times)


def shown_title(app, transcript):
    return parts(app, transcript)[1].cget("text")


def rename_with(app, transcript, new_title):
    """Double-click a title and type a new one into the box. Hands back the
    box, which is still waiting for Return or for the keyboard to leave it."""
    click_title(app, transcript, 2)
    settle(app, 150)
    entry = parts(app, transcript)[2]
    entry.delete(0, "end")
    entry.insert(0, new_title)
    return entry


def saved_title(app, data_dir, transcript):
    app.store.flush()
    saved = json.loads((data_dir / "data.json").read_text(encoding="utf-8"))
    return next(t for t in saved["transcripts"] if t["id"] == transcript.id)["title"]


@pytest.fixture
def title_saves(monkeypatch):
    """Hands back a function that, given the app, notes every time the store is
    asked to save a transcript's title. The save itself still happens."""
    def watch(app):
        calls = []
        real = app.store.set_transcript_title

        def set_transcript_title(*args):
            calls.append(args)
            return real(*args)

        monkeypatch.setattr(app.store, "set_transcript_title", set_transcript_title)
        return calls

    return watch


# ---- a click on a title ----

def test_a_click_on_a_title_opens_that_transcript(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")

        click_title(app, b)
        settle(app, 300)

        assert app._current_transcript is b
        assert app.canvas.current_transcript is b
        assert app.header._full_title == "B"
        assert app.list_body._current_id == b.id

        click_title(app, a)
        settle(app, 300)

        assert app._current_transcript is a
        assert app.header._full_title == "A"
        assert app.list_body._current_id == a.id


# ---- renaming ----

def test_a_double_click_opens_the_transcript_and_starts_the_rename(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")

        click_title(app, b, 2)
        settle(app, 150)

        assert app._current_transcript is b
        _, title_label, title_entry = parts(app, b)
        assert title_entry.winfo_manager() == "pack"
        assert title_label.winfo_manager() == ""
        assert title_entry.get() == "B"
        assert parts(app, a)[2].winfo_manager() == "", "only the double-clicked row is renamed"


def test_return_saves_the_new_title_and_the_header_follows(tmp_path, open_real_app, title_saves):
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")
        saves = title_saves(app)
        entry = rename_with(app, b, "  Chapter two ")

        entry._entry.event_generate("<Return>")
        settle(app, 200)

        assert saves == [(b.id, "Chapter two")]
        assert b.title == "Chapter two"
        assert saved_title(app, tmp_path, b) == "Chapter two"
        assert shown_title(app, b) == "Chapter two"
        assert parts(app, b)[2].winfo_manager() == ""
        assert app.header._full_title == "Chapter two"
        assert app._current_transcript is b
        assert app.list_body._current_id == b.id
        assert (a.title, shown_title(app, a)) == ("A", "A")


def test_leaving_the_box_saves_the_new_title_too(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        _, b = _add(app, "A", "B")
        entry = rename_with(app, b, "Chapter two")

        entry._entry.event_generate("<FocusOut>")
        settle(app, 200)

        assert b.title == "Chapter two"
        assert saved_title(app, tmp_path, b) == "Chapter two"
        assert app.header._full_title == "Chapter two"


@pytest.mark.parametrize("typed", ["   ", " B "], ids=["empty", "same_title"])
def test_an_empty_or_unchanged_title_is_not_saved(tmp_path, open_real_app, title_saves, typed):
    with open_real_app(tmp_path) as app:
        _, b = _add(app, "A", "B")
        saves = title_saves(app)
        entry = rename_with(app, b, typed)

        entry._entry.event_generate("<Return>")
        settle(app, 200)

        assert saves == []
        assert b.title == "B"
        assert shown_title(app, b) == "B"
        assert parts(app, b)[2].winfo_manager() == "", "the box should still go away"


def test_renaming_a_transcript_that_is_not_open_leaves_the_header_alone(tmp_path, open_real_app):
    """Every rename through the sidebar opens the transcript first, so this is
    the app's handler on its own."""
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")
        click_title(app, a)
        settle(app, 300)

        app._handle_rename_requested(b, "Chapter two")
        settle(app, 200)

        assert shown_title(app, b) == "Chapter two"
        assert app.header._full_title == "A"
        assert app._current_transcript is a


# ---- Esc while renaming ----

def test_esc_cancels_the_rename_and_saves_nothing(tmp_path, open_real_app, title_saves):
    with open_real_app(tmp_path) as app:
        _, b = _add(app, "A", "B")
        saves = title_saves(app)
        entry = rename_with(app, b, "Never saved")

        entry._entry.event_generate("<Escape>")
        settle(app, 150)

        assert parts(app, b)[2].winfo_manager() == ""
        assert shown_title(app, b) == "B"
        # Losing the keyboard right after mustn't save what was typed.
        entry._entry.event_generate("<FocusOut>")
        settle(app, 150)
        assert saves == []
        assert b.title == "B"


def test_esc_in_the_rename_box_does_not_also_stop_reading(tmp_path, open_real_app):
    """Esc is the shortcut for stopping, and the person is typing in a box, so
    it should only cancel the rename."""
    with open_real_app(tmp_path) as app:
        (a,) = _add(app, "A", paused=False)
        app.focus_force()
        entry = rename_with(app, a, "Never saved")
        canvas = app.canvas
        session = canvas.reader_display.session
        assert session is not None and not canvas._input_currently_shown

        entry._entry.event_generate("<Escape>")
        settle(app, 200)

        assert parts(app, a)[2].winfo_manager() == ""
        assert canvas.reader_display.session is session
        assert not canvas._input_currently_shown, "Esc went on to stop reading"


def test_esc_stops_reading_when_no_box_has_the_keyboard(tmp_path, open_real_app):
    """The same Esc as above, with nothing being typed. It does what it is for,
    so it not stopping above means something."""
    with open_real_app(tmp_path) as app:
        (a,) = _add(app, "A", paused=False)
        click_title(app, a)
        settle(app, 400)
        assert not app.canvas._input_currently_shown
        app.focus_force()
        app.focus_set()
        settle(app, 100)

        (app.focus_get() or app).event_generate("<Escape>")
        settle(app, 200)

        assert app.canvas._input_currently_shown


# ---- right click ----

@pytest.mark.parametrize("where", ["title", "row"])
def test_a_right_click_offers_to_move_that_transcript_to_another_space(tmp_path, open_real_app, monkeypatch, where):
    import gui.app
    import gui.components.transcript_list_body as body_module

    menus = []

    class _Menu(tkinter.Menu):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            menus.append(self)
            self.popped_up_at = None

        def tk_popup(self, x, y, *args):
            self.popped_up_at = (x, y)

    move_dialog = Opened()
    monkeypatch.setattr(body_module.tk, "Menu", _Menu)
    monkeypatch.setattr(gui.app, "MoveTranscriptDialog", move_dialog)
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        app._handle_new_space("Work")
        app._handle_space_selected(first)
        settle(app, 200)
        a, b = _add(app, "A", "B")
        _, title_label, _ = parts(app, b)
        target = title_label._label if where == "title" else app.list_body._rows[b.id]._canvas

        target.event_generate("<Button-3>", x=5, y=5)

        (menu,) = menus
        assert menu.popped_up_at is not None
        assert [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)] == ["Move to Space..."]
        assert app._current_transcript is None, "a right click shouldn't open the transcript"
        assert move_dialog.calls == []

        menu.invoke(0)

        (master, _, kwargs), = move_dialog.calls
        assert master is app
        assert kwargs["transcript_title"] == "B"
        assert kwargs["other_spaces"] == ["Work"]
        menu.destroy()


# ---- the X ----

def test_the_x_asks_before_deleting_that_transcript(tmp_path, open_real_app, monkeypatch):
    import gui.app

    delete_dialog = Opened()
    monkeypatch.setattr(gui.app, "DeleteTranscriptDialog", delete_dialog)
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")

        click_button(parts(app, b)[0])
        settle(app, 200)

        (master, _, kwargs), = delete_dialog.calls
        assert master is app
        assert kwargs["transcript_title"] == "B"
        assert app._current_transcript is None, "the X shouldn't open the transcript"
        assert app.store.transcripts == [a, b], "deleted before it was confirmed"

        kwargs["on_confirm"]()
        settle(app, 200)

        assert app.store.transcripts == [a]
        assert list(app.list_body._rows) == [a.id]
