"""Tests for marking the open transcript in the sidebar list
(gui/components/transcript_list_body.py, set_current(), and the two places
in gui/app.py that call it).

What was agreed: the row of the transcript open in the reader stands out, with
a soft ember tint and an ember border, in both themes. Only one row is marked
at a time, the mark follows the open transcript, and it is gone when nothing is
open. It stays through anything that builds the list again (a search, a new
sort, a rename), and marking a row doesn't build the list again, so the list
doesn't jump back to the top.

The list runs against a real Tk with one hidden root for the whole module,
inside a shown window, because a hidden window never gets a real size. The app
side is checked by running the app's own two methods on a small stand-in."""

import tkinter

import customtkinter as ctk
import pytest

from core.models import Transcript
from gui.components.transcript_list_body import (
    OPEN_ROW_BORDER, OPEN_ROW_FILL, ROW_BORDER_WIDTH, TranscriptListBody,
)
from gui.theme import EMBER_GLOW, HEARTH_PAPER


@pytest.fixture(scope="module")
def root():
    try:
        window = ctk.CTk()
    except tkinter.TclError:
        pytest.skip("no display available for Tk")
    window.withdraw()
    yield window
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()


TRANSCRIPTS = [
    Transcript(id=1, title="Lecture week seven", space="General"),
    Transcript(id=2, title="Chapter 3 notes", space="General"),
    Transcript(id=3, title="Interview transcript", space="General"),
]


@pytest.fixture
def body(root, wait_until_shown):
    top = ctk.CTkToplevel(root)
    top.geometry("320x400+0+0")
    widget = TranscriptListBody(top)
    widget.pack(fill="both", expand=True)
    widget.render_transcripts(TRANSCRIPTS)
    wait_until_shown(top)
    yield widget
    for timer in top.tk.splitlist(top.tk.call("after", "info")):
        top.tk.call("after", "cancel", timer)
    top.destroy()


def is_marked(row) -> bool:
    return row.cget("fg_color") == OPEN_ROW_FILL and row.cget("border_color") == OPEN_ROW_BORDER


def marked_ids(body) -> list:
    return [transcript_id for transcript_id, row in body._rows.items() if is_marked(row)]


def search(body, text):
    body._search_box.set_text(text)
    body.update()


# ---- the mark itself ----

def test_the_open_row_looks_different_from_the_others():
    assert OPEN_ROW_FILL != HEARTH_PAPER
    assert OPEN_ROW_BORDER == EMBER_GLOW


def test_no_row_is_marked_while_nothing_is_open(body):
    assert marked_ids(body) == []


def test_only_the_open_transcript_is_marked(body):
    body.set_current(2)
    assert marked_ids(body) == [2]


def test_the_mark_follows_the_open_transcript(body):
    body.set_current(2)
    body.set_current(3)
    assert marked_ids(body) == [3]


def test_the_mark_is_gone_when_nothing_is_open(body):
    body.set_current(2)
    body.set_current(None)
    assert marked_ids(body) == []


def test_marking_a_row_does_not_build_the_list_again(body):
    """The same row widgets stay, so the list keeps its scroll position."""
    before = dict(body._rows)
    body.set_current(2)
    body.set_current(3)
    assert body._rows == before
    assert all(row.winfo_exists() for row in before.values())


def test_a_row_keeps_its_size_when_it_is_marked(body):
    """Every row has the same border width, and the border only changes colour,
    so nothing moves."""
    assert {row.cget("border_width") for row in body._rows.values()} == {ROW_BORDER_WIDTH}
    sizes = {transcript_id: row.winfo_height() for transcript_id, row in body._rows.items()}
    body.set_current(2)
    body.update()
    assert {transcript_id: row.winfo_height() for transcript_id, row in body._rows.items()} == sizes


def test_a_transcript_not_in_the_list_marks_nothing(body):
    """After a switch to another space, the open transcript isn't listed."""
    body.set_current(99)
    assert marked_ids(body) == []


# ---- the mark stays when the list is built again ----

def test_the_mark_stays_when_the_list_is_given_again(body):
    """A rename, move or delete hands the list over again."""
    body.set_current(2)
    body.render_transcripts(TRANSCRIPTS)
    assert marked_ids(body) == [2]


def test_the_mark_stays_when_the_sort_changes(body):
    body.set_current(2)
    body._handle_sort_selected("Title (Z–A)")
    assert marked_ids(body) == [2]


def test_the_mark_comes_back_when_a_search_is_cleared(body):
    body.set_current(2)
    search(body, "interview")
    assert marked_ids(body) == []
    search(body, "")
    assert marked_ids(body) == [2]


# ---- the app ----

class Anything:
    """Stands in for any part of the app: every attribute is another stand-in,
    and every call is remembered with its arguments."""

    def __init__(self, name="app"):
        self.name = name
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        part = Anything(name)
        object.__setattr__(self, name, part)
        return part

    def __call__(self, *args):
        self.calls.append(args)


def test_opening_a_transcript_marks_it():
    from gui.app import RSVPApp

    app = Anything()
    RSVPApp._handle_open_transcript(app, TRANSCRIPTS[1])
    assert app.list_body.set_current.calls == [(2,)]


def test_deleting_the_open_transcript_removes_the_mark():
    from gui.app import RSVPApp

    app = Anything()
    app._current_transcript = TRANSCRIPTS[1]
    RSVPApp._handle_delete_confirmed(app, TRANSCRIPTS[1])
    assert app.list_body.set_current.calls == [(None,)]


def test_deleting_another_transcript_leaves_the_mark_alone():
    from gui.app import RSVPApp

    app = Anything()
    app._current_transcript = TRANSCRIPTS[1]
    RSVPApp._handle_delete_confirmed(app, TRANSCRIPTS[2])
    assert app.list_body.set_current.calls == []