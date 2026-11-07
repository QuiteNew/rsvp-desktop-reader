"""Tests for the actions that change what a person has stored: deleting a
transcript, deleting a space, moving a transcript to another space, adding a
space and renaming one (gui/app.py and the dialogs they open).

test_space_and_move_guards.py and test_sidebar_rows.py already check which dialog
the app opens and what it says, but with the confirmation window swapped for a
stand-in, so nothing ever pressed Delete. Here the windows are the real ones and
the buttons are really clicked: the X on a row, the Delete or Cancel in the
confirmation, a space picked in the move window, the "+" and "v" next to the
space name, and the pencil and X on each row of the space picker. After each
action the test looks at the list on screen, at the store, and at what was
written to disk.

The right-click menu is a real Tk menu that is stopped just before it would pop
up, as in test_sidebar_rows.py: a pop-up menu takes over until it's dismissed,
which would hold a test up for good on Windows.

The last tests are about a row of the sidebar: a title too long for the row is
cut short with "...", and the X lights up while the pointer is over the row."""

import json
import tkinter
from tkinter import font as tkfont

import customtkinter as ctk
import pytest

from gui.components.add_space_dialog import AddSpaceDialog
from gui.components.delete_space_dialog import DeleteSpaceDialog
from gui.components.delete_transcript_dialog import DeleteTranscriptDialog
from gui.components.message_dialog import MessageDialog
from gui.components.move_transcript_dialog import MoveTranscriptDialog
from gui.components.space_selection_dialog import SpaceSelectionDialog
from gui.theme import WARM_LINE, WARM_TAUPE

from tk_helpers import all_widgets, click, click_button, settle

TEXT = " ".join(f"w{i}" for i in range(300))


# ---- helpers ----

def _add(app, *titles, space=None):
    """Add transcripts with some text to a space (the one on screen unless told
    otherwise) and show the sidebar again. Returns them in order."""
    store = app.store
    added = []
    for title in titles:
        transcript = store.add_transcript(title, space or store.current_space)
        store.set_transcript_text(transcript.id, TEXT)
        store.set_transcript_paused(transcript.id, True)
        added.append(transcript)
    app._refresh_transcript_list()
    settle(app, 300)
    return added


def _spaces(app, *names):
    """Add spaces and go back to the first one, so that is the one on screen.
    Returns its name."""
    first = app.store.current_space
    for name in names:
        app._handle_new_space(name)
    app._handle_space_selected(first)
    settle(app, 200)
    return first


def windows(parent, cls):
    return [w for w in parent.winfo_children() if isinstance(w, cls)]


def buttons(window):
    return [w for w in all_widgets(window) if isinstance(w, ctk.CTkButton)]


def button(window, text):
    return next(w for w in buttons(window) if w.cget("text") == text)


def label_texts(window):
    return [w.cget("text") for w in all_widgets(window) if isinstance(w, ctk.CTkLabel)]


def parts(app, transcript):
    """The three things in a sidebar row, in the order they're packed: the X
    button, the title, and the box that takes the title's place while renaming."""
    return app.list_body._rows[transcript.id].winfo_children()


def on_disk(app, data_dir):
    app.store.flush()
    return json.loads((data_dir / "data.json").read_text(encoding="utf-8"))


def press_escape(dialog):
    """Send Esc to whatever has the keyboard in a window, the way a real key
    press arrives."""
    if dialog.focus_get() is None:
        dialog.focus_force()
        dialog.update()
    (dialog.focus_get() or dialog).event_generate("<Escape>")
    settle(dialog, 150)


@pytest.fixture
def menus(monkeypatch):
    """Every right-click menu the sidebar builds. They are real, only stopped
    before they pop up."""
    import gui.components.transcript_list_body as body_module

    made = []

    class _Menu(tkinter.Menu):
        def tk_popup(self, x, y, *args):
            pass

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            made.append(self)

    monkeypatch.setattr(body_module.tk, "Menu", _Menu)
    return made


# ---- the sidebar's X and the confirmation behind it ----

def delete_dialog_for(app, transcript):
    click_button(parts(app, transcript)[0])
    settle(app, 400)
    (dialog,) = windows(app, DeleteTranscriptDialog)
    return dialog


def test_the_x_asks_first_in_a_window_that_names_the_transcript(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")

        dialog = delete_dialog_for(app, b)

        assert any('"B"' in text for text in label_texts(dialog))
        assert [w.cget("text") for w in buttons(dialog)] == ["Cancel", "Delete"]
        assert app.store.transcripts == [a, b], "deleted before it was confirmed"


def test_delete_takes_the_transcript_off_the_list_the_store_and_the_disk(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b, c = _add(app, "A", "B", "C")
        dialog = delete_dialog_for(app, b)

        click_button(button(dialog, "Delete"))
        settle(app, 300)

        assert windows(app, DeleteTranscriptDialog) == []
        assert list(app.list_body._rows) == [a.id, c.id]
        assert app.store.transcripts == [a, c]
        assert [t["title"] for t in on_disk(app, tmp_path)["transcripts"]] == ["A", "C"]


@pytest.mark.parametrize("how", ["Cancel button", "Esc"])
def test_cancel_and_esc_keep_the_transcript(tmp_path, open_real_app, how):
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")
        dialog = delete_dialog_for(app, b)

        if how == "Esc":
            press_escape(dialog)
        else:
            click_button(button(dialog, "Cancel"))
        settle(app, 300)

        assert windows(app, DeleteTranscriptDialog) == []
        assert list(app.list_body._rows) == [a.id, b.id]
        assert app.store.transcripts == [a, b]
        assert [t["title"] for t in on_disk(app, tmp_path)["transcripts"]] == ["A", "B"]


def test_deleting_the_open_transcript_empties_the_reader_and_forgets_it(tmp_path, open_real_app):
    """It is being read when it's deleted. Nothing of it is left on screen, and
    the next start doesn't try to reopen it."""
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")
        app.store.set_transcript_paused(a.id, False)
        click(parts(app, a)[1]._label)
        settle(app, 400)
        assert app._current_transcript is a
        assert app.canvas.reader_display.session is not None
        assert app.settings_store.last_transcript_id == a.id

        click_button(button(delete_dialog_for(app, a), "Delete"))
        settle(app, 300)

        assert app._current_transcript is None
        assert app.canvas.current_transcript is None
        assert app.canvas.reader_display.session is None
        assert app.header._full_title == "No transcript selected"
        assert app.list_body._current_id is None
        assert app.footer.wpm_slider.cget("state") == "disabled"
        assert app.settings_store.last_transcript_id is None
        assert list(app.list_body._rows) == [b.id]


def test_deleting_another_transcript_leaves_the_open_one_alone(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")
        click(parts(app, a)[1]._label)
        settle(app, 400)
        session = app.canvas.reader_display.session

        click_button(button(delete_dialog_for(app, b), "Delete"))
        settle(app, 300)

        assert app._current_transcript is a
        assert app.canvas.reader_display.session is session
        assert app.header._full_title == "A"
        assert app.list_body._current_id == a.id
        assert app.settings_store.last_transcript_id == a.id
        assert app.footer.wpm_slider.cget("state") == "normal"


# ---- moving a transcript to another space ----

def move_dialog_for(app, menus, transcript):
    """Right-click a transcript and choose Move to Space."""
    parts(app, transcript)[1]._label.event_generate("<Button-3>", x=5, y=5)
    menu = menus[-1]
    menu.invoke(0)
    menu.destroy()
    settle(app, 400)
    (dialog,) = windows(app, MoveTranscriptDialog)
    return dialog


def test_picking_a_space_in_the_move_window_files_the_transcript_there(tmp_path, open_real_app, menus):
    with open_real_app(tmp_path) as app:
        _spaces(app, "Work", "Home")
        a, b = _add(app, "A", "B")
        dialog = move_dialog_for(app, menus, a)
        assert [w.cget("text") for w in buttons(dialog)] == ["Work", "Home"]

        click_button(button(dialog, "Home"))
        settle(app, 300)

        assert windows(app, MoveTranscriptDialog) == []
        assert a.space == "Home"
        assert list(app.list_body._rows) == [b.id], "it should have left the list on screen"
        assert app.store.transcripts_in_space("Home") == [a]
        saved = {t["title"]: t["space"] for t in on_disk(app, tmp_path)["transcripts"]}
        assert saved == {"A": "Home", "B": app.store.spaces[0]}


def test_the_moved_transcript_is_found_in_its_new_space(tmp_path, open_real_app, menus):
    with open_real_app(tmp_path) as app:
        _spaces(app, "Work")
        (a,) = _add(app, "A")
        click_button(button(move_dialog_for(app, menus, a), "Work"))
        settle(app, 300)

        app._handle_space_selected("Work")
        settle(app, 300)

        assert list(app.list_body._rows) == [a.id]


def test_esc_closes_the_move_window_and_moves_nothing(tmp_path, open_real_app, menus):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        (a,) = _add(app, "A")
        dialog = move_dialog_for(app, menus, a)

        press_escape(dialog)

        assert windows(app, MoveTranscriptDialog) == []
        assert a.space == first
        assert list(app.list_body._rows) == [a.id]


# ---- the "+" next to the space name ----

def plus(app):
    return next(w for w in buttons(app.spaces) if w.cget("text") == "+")


def new_space_window(app):
    click_button(plus(app))
    settle(app, 400)
    (dialog,) = windows(app, AddSpaceDialog)
    return dialog


def test_creating_a_space_adds_it_and_moves_to_it(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        _add(app, "In the first space")
        dialog = new_space_window(app)

        dialog.name_entry.insert(0, "  Work ")
        click_button(button(dialog, "Create"))
        settle(app, 300)

        assert windows(app, AddSpaceDialog) == []
        assert app.store.spaces == [first, "Work"]
        assert app.store.current_space == "Work"
        assert app.spaces.name_label.cget("text") == "Work"
        assert list(app.list_body._rows) == [], "the new space has nothing in it yet"
        saved = on_disk(app, tmp_path)
        assert saved["spaces"] == [first, "Work"]
        assert saved["current_space_index"] == 1


def test_a_blank_name_creates_nothing_and_the_window_stays(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        dialog = new_space_window(app)

        click_button(button(dialog, "Create"))
        settle(app, 200)
        assert windows(app, AddSpaceDialog) == [dialog]
        dialog.name_entry.insert(0, "   ")
        click_button(button(dialog, "Create"))
        settle(app, 200)

        assert windows(app, AddSpaceDialog) == [dialog]
        assert app.store.spaces == [first]


@pytest.mark.parametrize("how", ["Cancel button", "Esc"])
def test_cancel_and_esc_create_nothing(tmp_path, open_real_app, how):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        dialog = new_space_window(app)
        dialog.name_entry.insert(0, "Work")

        if how == "Esc":
            press_escape(dialog)
        else:
            click_button(button(dialog, "Cancel"))
        settle(app, 200)

        assert windows(app, AddSpaceDialog) == []
        assert app.store.spaces == [first]
        assert app.spaces.name_label.cget("text") == first


def test_a_name_that_is_taken_adds_no_second_space(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        dialog = new_space_window(app)

        dialog.name_entry.insert(0, first)
        click_button(button(dialog, "Create"))
        settle(app, 300)

        assert app.store.spaces == [first]
        assert on_disk(app, tmp_path)["spaces"] == [first]


# ---- the "v" next to the space name, and the space picker ----

def open_picker(app):
    click_button(app.spaces.menu_button)
    settle(app, 500)
    (picker,) = windows(app, SpaceSelectionDialog)
    return picker


def row_parts(picker, name):
    """The four things in the picker's row for a space, in the order they're
    packed: the X, the pencil, the name, and the box that takes the name's
    place while renaming."""
    for row in picker.list_frame.winfo_children():
        row_widgets = row.winfo_children()
        if row_widgets[2].cget("text") == name:
            return row_widgets
    raise AssertionError(f"no row for {name!r}")


def shown_names(picker):
    return [row.winfo_children()[2].cget("text") for row in picker.list_frame.winfo_children()]


def test_the_v_lists_every_space_with_the_current_one_not_clickable(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        _spaces(app, "Work", "Home")
        app._handle_space_selected("Work")
        settle(app, 200)

        picker = open_picker(app)

        assert shown_names(picker) == [app.store.spaces[0], "Work", "Home"]
        assert isinstance(row_parts(picker, "Work")[2], ctk.CTkLabel)
        assert isinstance(row_parts(picker, "Home")[2], ctk.CTkButton)


def test_clicking_another_space_switches_to_it_and_closes_the_picker(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        (kept,) = _add(app, "In the first")
        (worked,) = _add(app, "In Work", space="Work")
        assert app.spaces.name_label.cget("text") == first
        picker = open_picker(app)

        click_button(row_parts(picker, "Work")[2])
        settle(app, 300)

        assert windows(app, SpaceSelectionDialog) == []
        assert app.store.current_space == "Work"
        assert app.spaces.name_label.cget("text") == "Work"
        assert list(app.list_body._rows) == [worked.id]
        assert on_disk(app, tmp_path)["current_space_index"] == 1

        picker = open_picker(app)
        click_button(row_parts(picker, first)[2])
        settle(app, 300)
        assert app.spaces.name_label.cget("text") == first
        assert list(app.list_body._rows) == [kept.id]


def test_esc_closes_the_picker_and_stays_where_it_was(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        picker = open_picker(app)

        press_escape(picker)

        assert windows(app, SpaceSelectionDialog) == []
        assert app.store.current_space == first


# ---- renaming a space in the picker ----

def start_rename(picker, name, new_name):
    """Click a row's pencil and type a new name into the box that comes up.
    Hands the box back, still waiting for Return or for the keyboard to leave.

    The picker is given the keyboard first, as a person clicking into it would
    give it. Without that, a second rename in the same picker never got going
    when the tests ran with no window manager: the box came up, did not get
    the keyboard, and closed again at once."""
    _, pencil, _, entry = row_parts(picker, name)
    picker.focus_force()
    settle(picker, 100)
    click_button(pencil)
    settle(picker, 150)
    entry.delete(0, "end")
    entry.insert(0, new_name)
    return entry


def commit(entry):
    entry._entry.event_generate("<Return>")
    settle(entry, 200)


def test_a_renamed_space_keeps_its_transcripts_and_the_picker_stays_open(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        (t,) = _add(app, "In Work", space="Work")
        picker = open_picker(app)

        commit(start_rename(picker, "Work", "Office"))

        assert windows(app, SpaceSelectionDialog) == [picker]
        assert shown_names(picker) == [first, "Office"]
        assert app.store.spaces == [first, "Office"]
        assert t.space == "Office"
        assert app.spaces.name_label.cget("text") == first, "the space on screen wasn't the one renamed"
        saved = on_disk(app, tmp_path)
        assert saved["spaces"] == [first, "Office"]
        assert saved["transcripts"][0]["space"] == "Office"

        click_button(row_parts(picker, "Office")[2])
        settle(app, 300)
        assert list(app.list_body._rows) == [t.id]


def test_renaming_the_space_on_screen_changes_the_name_below_the_list(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        _spaces(app, "Work")
        app._handle_space_selected("Work")
        (t,) = _add(app, "In Work")
        picker = open_picker(app)

        commit(start_rename(picker, "Work", "Office"))

        assert app.store.current_space == "Office"
        assert app.spaces.name_label.cget("text") == "Office"
        assert list(app.list_body._rows) == [t.id], "the list on screen should be unchanged"


@pytest.mark.parametrize("new_name", ["", "   ", "Work", "Home"], ids=["empty", "spaces", "unchanged", "taken"])
def test_a_name_that_cant_be_used_leaves_the_space_as_it_was(tmp_path, open_real_app, new_name):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work", "Home")
        picker = open_picker(app)

        commit(start_rename(picker, "Work", new_name))

        assert shown_names(picker) == [first, "Work", "Home"]
        assert app.store.spaces == [first, "Work", "Home"]


def test_esc_while_renaming_cancels_only_the_rename(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        picker = open_picker(app)
        entry = start_rename(picker, "Work", "Never saved")

        entry._entry.event_generate("<Escape>")
        settle(app, 150)

        assert windows(app, SpaceSelectionDialog) == [picker], "Esc closed the whole picker"
        assert entry.winfo_manager() == ""
        assert shown_names(picker) == [first, "Work"]
        # Losing the keyboard right after mustn't save what was typed.
        entry._entry.event_generate("<FocusOut>")
        settle(app, 150)
        assert app.store.spaces == [first, "Work"]


def test_leaving_the_box_saves_the_new_name(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        picker = open_picker(app)
        entry = start_rename(picker, "Work", "Office")

        entry._entry.event_generate("<FocusOut>")
        settle(app, 200)

        assert app.store.spaces == [first, "Office"]
        assert shown_names(picker) == [first, "Office"]


def test_a_row_that_was_renamed_is_renamed_again_from_its_new_name(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        (t,) = _add(app, "In Work", space="Work")
        picker = open_picker(app)

        commit(start_rename(picker, "Work", "Office"))
        commit(start_rename(picker, "Office", "Desk"))

        assert app.store.spaces == [first, "Desk"]
        assert t.space == "Desk"
        assert shown_names(picker) == [first, "Desk"]


# ---- deleting a space in the picker ----

def delete_space_window(picker, name):
    click_button(row_parts(picker, name)[0])
    settle(picker, 400)
    (dialog,) = windows(picker, DeleteSpaceDialog)
    return dialog


def test_deleting_an_empty_space_asks_first_and_then_removes_it(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        picker = open_picker(app)

        dialog = delete_space_window(picker, "Work")

        assert any('"Work"' in text for text in label_texts(dialog))
        assert [w.cget("text") for w in buttons(dialog)] == ["Cancel", "Delete"]
        assert app.store.spaces == [first, "Work"], "deleted before it was confirmed"

        click_button(button(dialog, "Delete"))
        settle(app, 300)

        assert app.store.spaces == [first]
        assert on_disk(app, tmp_path)["spaces"] == [first]
        assert windows(app, SpaceSelectionDialog) == [], "the picker should close with it"
        assert not picker.winfo_exists()


@pytest.mark.parametrize("how", ["Cancel button", "Esc"])
def test_cancel_and_esc_keep_the_space(tmp_path, open_real_app, how):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        picker = open_picker(app)
        dialog = delete_space_window(picker, "Work")

        if how == "Esc":
            press_escape(dialog)
        else:
            click_button(button(dialog, "Cancel"))
        settle(app, 300)

        assert windows(picker, DeleteSpaceDialog) == []
        assert windows(app, SpaceSelectionDialog) == [picker]
        assert app.store.spaces == [first, "Work"]


def test_deleting_the_space_on_screen_goes_back_to_the_first_one(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        (kept,) = _add(app, "In the first")
        app._handle_new_space("Work")
        settle(app, 200)
        assert list(app.list_body._rows) == []
        picker = open_picker(app)

        click_button(button(delete_space_window(picker, "Work"), "Delete"))
        settle(app, 300)

        assert app.store.current_space == first
        assert app.spaces.name_label.cget("text") == first
        assert list(app.list_body._rows) == [kept.id]
        assert on_disk(app, tmp_path)["current_space_index"] == 0


def test_deleting_another_space_leaves_the_one_on_screen_where_it_is(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work", "Home")
        app._handle_space_selected("Home")
        (t,) = _add(app, "In Home")
        picker = open_picker(app)

        click_button(button(delete_space_window(picker, "Work"), "Delete"))
        settle(app, 300)

        assert app.store.spaces == [first, "Home"]
        assert app.store.current_space == "Home"
        assert app.spaces.name_label.cget("text") == "Home"
        assert list(app.list_body._rows) == [t.id]
        assert on_disk(app, tmp_path)["current_space_index"] == 1


def test_a_space_that_was_renamed_is_deleted_under_its_new_name(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        picker = open_picker(app)
        commit(start_rename(picker, "Work", "Office"))

        dialog = delete_space_window(picker, "Office")

        assert any('"Office"' in text for text in label_texts(dialog))
        click_button(button(dialog, "Delete"))
        settle(app, 300)
        assert app.store.spaces == [first]


def test_the_only_space_cant_be_deleted_and_the_message_says_why(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        only = app.store.current_space
        picker = open_picker(app)

        click_button(row_parts(picker, only)[0])
        settle(app, 400)

        (message,) = windows(picker, MessageDialog)
        assert any("only space" in text for text in label_texts(message))
        assert windows(picker, DeleteSpaceDialog) == []
        click_button(button(message, "OK"))
        settle(app, 200)
        assert windows(picker, MessageDialog) == []
        assert app.store.spaces == [only]


@pytest.mark.parametrize("count, says", [(1, "1 transcript in it"), (2, "2 transcripts in it")], ids=["one", "two"])
def test_a_space_with_transcripts_in_it_cant_be_deleted_and_the_message_says_why(tmp_path, open_real_app, count, says):
    with open_real_app(tmp_path) as app:
        first = _spaces(app, "Work")
        _add(app, *[f"T{n}" for n in range(count)], space="Work")
        picker = open_picker(app)

        click_button(row_parts(picker, "Work")[0])
        settle(app, 400)

        (message,) = windows(picker, MessageDialog)
        texts = label_texts(message)
        assert any('"Work"' in text and says in text for text in texts), texts
        assert windows(picker, DeleteSpaceDialog) == []
        click_button(button(message, "OK"))
        settle(app, 200)
        assert app.store.spaces == [first, "Work"]
        assert len(app.store.transcripts_in_space("Work")) == count


# ---- a row of the sidebar ----

def assert_cut_where_the_row_runs_out(label, title):
    """What the label shows is the start of the title and "…", it fits the
    label, and one more letter of the title would not."""
    shown = label.cget("text")
    width = label.winfo_width()
    font = tkfont.Font(font=label._label.cget("font"))
    assert shown.endswith("…") and title.startswith(shown[:-1])
    assert font.measure(shown) <= width
    assert font.measure(title[:len(shown)] + "…") > width, "there was room for more"


def test_a_title_too_long_for_the_row_is_cut_short_with_dots_and_the_x_stays(tmp_path, open_real_app):
    title = "A very long title that goes on and on " * 4
    with open_real_app(tmp_path) as app:
        (t,) = _add(app, title)
        delete_button, label, _ = parts(app, t)

        shown = label.cget("text")

        assert len(shown) < len(title)
        assert_cut_where_the_row_runs_out(label, title)
        assert delete_button.winfo_ismapped()
        assert t.title == title, "only what is shown is cut, not the title"


def test_a_short_title_is_shown_whole(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        (t,) = _add(app, "Chapter one")

        assert parts(app, t)[1].cget("text") == "Chapter one"


def test_a_wider_sidebar_shows_more_of_a_long_title(tmp_path, open_real_app):
    """At each width the title is cut where the row runs out. Several widths are
    tried because a cut that is a letter short only shows at some of them."""
    title = "A very long title that goes on and on " * 4
    with open_real_app(tmp_path) as app:
        (t,) = _add(app, title)
        label = parts(app, t)[1]

        lengths = []
        for width in (150, 170, 190, 210, 230, 300, 500):
            app.grid_columnconfigure(0, minsize=width)
            settle(app, 300)
            assert_cut_where_the_row_runs_out(label, title)
            lengths.append(len(label.cget("text")))

        assert lengths == sorted(lengths)
        assert lengths[-1] > lengths[0]


def test_the_x_lights_up_while_the_pointer_is_over_the_row(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        (t,) = _add(app, "A")
        delete_button, label, _ = parts(app, t)
        assert delete_button.cget("text_color") == WARM_TAUPE

        label._label.event_generate("<Enter>")
        settle(app, 100)
        assert delete_button.cget("text_color") == WARM_LINE

        label._label.event_generate("<Leave>")
        settle(app, 100)
        assert delete_button.cget("text_color") == WARM_TAUPE
