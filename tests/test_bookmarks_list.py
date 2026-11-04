"""Tests for the bookmarks list (gui/components/bookmarks_popover.py) as a person
uses it: what its rows say, what a click on one does, renaming and deleting a
bookmark, the add/remove button, and closing the list. It opens from the main
window (gui/components/canvas.py) and from the detached window
(detached_window.py), which share this one class, so the tests that check what
the list does to the reader and to the saved data run in both.

test_seeking_in_the_windows.py already checks where a jump lands, but it calls
the list's jump handler directly. Here the clicks are real ones sent to the
row, so the single/double click handling is covered too: a single click waits a
moment before it jumps, so that a double click can cancel the jump and open the
rename box instead.

Each test builds the real app with open_real_app (conftest.py) and the
transcript used is A, with a few bookmarks already in it. For the detached
window, A is detached and a second transcript, B, is open in the main window,
with a bookmark of its own at the same word. That's what shows a change going
to the wrong transcript. Tk's key and click events are sent to the real widgets,
the same way test_window_esc.py does it."""

import json

import pytest

from gui.components.bookmarks_popover import BookmarksPopover

from tk_helpers import click, click_button, settle

WORDS = [f"w{i}" for i in range(1200)]
TEXT = " ".join(WORDS)

# A's bookmarks to start with: the word, and the few words around it that the
# list shows when the bookmark has no name.
SNIPPET_70 = "w67 w68 w69 w70 w71 w72 w73"
SNIPPET_300 = "w297 w298 w299 w300 w301 w302 w303"

# How long to run the event loop to be sure a single click's jump has had its
# turn: the list's own wait, and a little over.
AFTER_THE_WAIT_MS = BookmarksPopover.CLICK_DELAY_MS + 150


class Scene:
    """What a test works with: the app, the two transcripts, and the window the
    bookmarks list opens from. `owner` is the main window's canvas or the
    detached window, and both have the same parts under the same names."""

    def __init__(self, app, data_dir, where, a, b):
        self.app = app
        self.data_dir = data_dir
        self.where = where
        self.a = a
        self.b = b
        self.owner = app.canvas if where == "main" else app.canvas._detached_window
        self.reader = self.owner.reader_display

    @property
    def popover(self):
        return self.owner._bookmarks_popover

    def open_list(self):
        self.owner.open_bookmarks()
        settle(self.app, 400)
        return self.popover

    def saved(self, transcript):
        """The transcript as it's stored on disk right now."""
        self.app.store.flush()
        saved = json.loads((self.data_dir / "data.json").read_text(encoding="utf-8"))
        return next(t for t in saved["transcripts"] if t["id"] == transcript.id)

    def shown_word(self):
        return "".join(
            label.cget("text") for label in (self.reader.before_label, self.reader.focus_label, self.reader.after_label)
        )


def _build(app, data_dir, where):
    store = app.store
    a, b = (store.add_transcript(title, store.current_space) for title in ("A", "B"))
    for transcript in (a, b):
        store.set_transcript_text(transcript.id, TEXT)
        store.set_transcript_paused(transcript.id, True)
    store.add_bookmark(a.id, 70, SNIPPET_70)
    store.add_bookmark(a.id, 300, SNIPPET_300)
    store.add_bookmark(b.id, 70, "b's own")
    app._refresh_transcript_list()
    settle(app, 300)
    app._handle_open_transcript(a)
    settle(app, 300)
    if where == "detached":
        app.canvas._handle_detach()
        settle(app, 600)
        app._handle_open_transcript(b)
        settle(app, 300)
    return Scene(app, data_dir, where, a, b)


@pytest.fixture(params=["main", "detached"])
def scene(request, tmp_path, open_real_app):
    """The list's tests that run in both windows."""
    with open_real_app(tmp_path) as app:
        yield _build(app, tmp_path, request.param)


@pytest.fixture
def main_scene(tmp_path, open_real_app):
    """The ones about the list itself, which don't depend on the window."""
    with open_real_app(tmp_path) as app:
        yield _build(app, tmp_path, "main")


# ---- ways to reach into the list ----

def rows(popover):
    return [child for child in popover.list_frame.winfo_children() if child is not popover.empty_label]


def parts(row):
    """The three things in a row, in the order they're packed: the ✕ button,
    the name label, and the box that takes the label's place while renaming."""
    delete_button, name_label, rename_entry = row.winfo_children()
    return delete_button, name_label, rename_entry


def texts(popover):
    return [parts(row)[1].cget("text") for row in rows(popover)]


def click_label(row, times=1):
    click(parts(row)[1]._label, times)


def click_background(row, times=1):
    click(row._canvas, times)


def rename_with(scene, row, new_name):
    """Double-click a row and type a name into its box. Hands back the box,
    which is still waiting for Return or for the focus to leave."""
    click_label(row, 2)
    settle(scene.app, 100)
    entry = parts(row)[2]
    entry.delete(0, "end")
    entry.insert(0, new_name)
    return entry


def press(scene, key, target=None):
    """Send a key to a widget, by default whatever has the keyboard in the
    list, the way a real key press arrives."""
    target = target or scene.popover.focus_get() or scene.popover
    target.event_generate(f"<{key}>")
    settle(scene.app, 150)


def labels_saved(scene, transcript=None):
    return {b["index"]: b["label"] for b in scene.saved(transcript or scene.a)["bookmarks"]}


@pytest.fixture
def rename_calls(monkeypatch, main_scene):
    """Every time the app is asked to save a bookmark's name, with what it was
    asked. The save itself still happens."""
    calls = []
    store = main_scene.app.store
    real = store.set_bookmark_label

    def set_bookmark_label(*args):
        calls.append(args)
        return real(*args)

    monkeypatch.setattr(store, "set_bookmark_label", set_bookmark_label)
    return calls


# ---- what the list shows ----

def test_an_empty_list_says_so_until_a_bookmark_is_added(main_scene):
    scene = main_scene
    for index in (70, 300):
        scene.app.store.remove_bookmark(scene.a.id, index)
    popover = scene.open_list()

    assert rows(popover) == []
    assert popover.empty_label.winfo_ismapped()
    assert popover.empty_label.cget("text") == "No bookmarks yet."

    scene.owner.toggle_bookmark_here()
    settle(scene.app, 100)

    assert len(rows(popover)) == 1
    assert not popover.empty_label.winfo_ismapped()


def test_each_row_shows_its_name_and_where_it_is(main_scene):
    """A name wins over the words around the bookmark, the place is counted
    from 1 and has thousands separators, and a name that doesn't fit is cut
    with an ellipsis. One of exactly the limit stays whole."""
    scene = main_scene
    store = scene.app.store
    limit = BookmarksPopover.SNIPPET_MAX_CHARS
    exactly_fits = "abcdefghij" * 4 + "abcd"
    too_long = exactly_fits + "e"
    assert len(exactly_fits) == limit
    store.set_bookmark_label(scene.a.id, 300, "Chapter two")
    store.add_bookmark(scene.a.id, 5, "")
    store.add_bookmark(scene.a.id, 400, "a snippet")
    store.set_bookmark_label(scene.a.id, 400, exactly_fits)
    store.add_bookmark(scene.a.id, 500, "a snippet")
    store.set_bookmark_label(scene.a.id, 500, too_long)
    store.add_bookmark(scene.a.id, 1000, "w997 w998 w999 w1000 w1001 w1002 w1003")

    popover = scene.open_list()

    assert texts(popover) == [
        "word 6 of 1,200",
        f"{SNIPPET_70}   word 71 of 1,200",
        "Chapter two   word 301 of 1,200",
        f"{exactly_fits}   word 401 of 1,200",
        f"{too_long[:limit - 1]}…   word 501 of 1,200",
        "w997 w998 w999 w1000 w1001 w1002 w1003   word 1,001 of 1,200",
    ]


# ---- a click on a row ----

def test_a_click_on_a_row_jumps_there_after_a_moment_and_closes_the_list(scene):
    popover = scene.open_list()
    first = rows(popover)[0]

    click_label(first)

    assert scene.reader.session.index == 0, "it jumped before a double click could cancel it"
    assert scene.popover is popover

    settle(scene.app, AFTER_THE_WAIT_MS)

    assert scene.shown_word() == "w70"
    assert scene.reader.session.index == 70
    assert scene.owner.toolbar.pause_button.cget("text") == "▶"
    assert scene.popover is None
    assert not popover.winfo_exists()
    entry = scene.saved(scene.a)
    assert (entry["position"], entry["is_paused"]) == (70, True)
    assert scene.saved(scene.b)["position"] == 0


def test_a_click_anywhere_on_the_row_jumps_not_just_on_the_text(main_scene):
    scene = main_scene
    popover = scene.open_list()

    click_background(rows(popover)[1])
    settle(scene.app, AFTER_THE_WAIT_MS)

    assert scene.reader.session.index == 300
    assert scene.popover is None


def test_a_double_click_renames_instead_of_jumping(main_scene):
    """On the text or on the rest of the row alike. The box opens with the
    name there now, empty for a bookmark without one, and takes the keyboard."""
    scene = main_scene
    scene.app.store.set_bookmark_label(scene.a.id, 300, "Chapter two")
    popover = scene.open_list()
    first, second = rows(popover)

    click_label(first, 2)
    click_background(second, 2)
    settle(scene.app, AFTER_THE_WAIT_MS)

    assert scene.reader.session.index == 0
    assert scene.popover is popover
    assert popover._pending_click_ids == set()
    first_box, second_box = parts(first)[2], parts(second)[2]
    assert first_box.winfo_manager() == "pack" and parts(first)[1].winfo_manager() == ""
    assert second_box.winfo_manager() == "pack"
    assert first_box.get() == ""
    assert second_box.get() == "Chapter two"
    assert popover.focus_get() is second_box._entry


def test_a_click_on_the_row_being_renamed_doesnt_also_jump(main_scene):
    """The click takes the keyboard from the box, which ends the rename, and
    the same click mustn't go on to count as a jump."""
    scene = main_scene
    popover = scene.open_list()
    first = rows(popover)[0]
    click_label(first, 2)
    settle(scene.app, 100)

    click_background(first)
    settle(scene.app, AFTER_THE_WAIT_MS)

    assert scene.reader.session.index == 0
    assert scene.popover is popover
    assert popover._pending_click_ids == set()


# ---- renaming ----

def test_return_saves_the_new_name_for_that_bookmark_only(scene):
    popover = scene.open_list()
    entry = rename_with(scene, rows(popover)[1], "  Chapter two ")

    entry._entry.event_generate("<Return>")
    settle(scene.app, 150)

    assert scene.popover is popover, "renaming shouldn't close the list"
    assert texts(popover) == [f"{SNIPPET_70}   word 71 of 1,200", "Chapter two   word 301 of 1,200"]
    assert parts(rows(popover)[1])[2].winfo_manager() == ""
    assert scene.reader.session.index == 0
    assert labels_saved(scene) == {70: "", 300: "Chapter two"}
    assert labels_saved(scene, scene.b) == {70: ""}


def test_leaving_the_box_saves_the_name_too(main_scene, rename_calls):
    """And each name is saved once. Return takes the box away, which takes the
    keyboard from it, so the box has to know it's already done."""
    scene = main_scene
    popover = scene.open_list()

    entry = rename_with(scene, rows(popover)[0], "Start")
    entry._entry.event_generate("<FocusOut>")
    settle(scene.app, 150)

    assert rename_calls == [(scene.a.id, 70, "Start")]
    assert texts(popover)[0] == "Start   word 71 of 1,200"
    assert labels_saved(scene) == {70: "Start", 300: ""}

    entry = rename_with(scene, rows(popover)[1], "End")
    entry._entry.event_generate("<Return>")
    settle(scene.app, 150)

    assert rename_calls == [(scene.a.id, 70, "Start"), (scene.a.id, 300, "End")]


def test_an_empty_name_takes_the_name_off_and_shows_the_words_again(main_scene):
    scene = main_scene
    scene.app.store.set_bookmark_label(scene.a.id, 70, "Start")
    popover = scene.open_list()
    assert texts(popover)[0] == "Start   word 71 of 1,200"

    entry = rename_with(scene, rows(popover)[0], "   ")
    entry._entry.event_generate("<Return>")
    settle(scene.app, 150)

    assert texts(popover)[0] == f"{SNIPPET_70}   word 71 of 1,200"
    assert labels_saved(scene)[70] == ""


def test_the_same_name_isnt_saved_again(main_scene, rename_calls):
    scene = main_scene
    scene.app.store.set_bookmark_label(scene.a.id, 70, "Start")
    rename_calls.clear()
    popover = scene.open_list()

    entry = rename_with(scene, rows(popover)[0], " Start ")
    entry._entry.event_generate("<Return>")
    settle(scene.app, 150)

    assert rename_calls == []
    assert parts(rows(popover)[0])[2].winfo_manager() == ""
    assert texts(popover)[0] == "Start   word 71 of 1,200"


def test_escape_stops_the_rename_without_closing_the_list(main_scene, rename_calls):
    """Esc closes the list, so while a name is being typed it has to stop at
    the box and only cancel the rename. A second Esc then closes the list."""
    scene = main_scene
    popover = scene.open_list()
    first = rows(popover)[0]
    entry = rename_with(scene, first, "Never saved")

    entry._entry.event_generate("<Escape>")
    settle(scene.app, 150)

    assert scene.popover is popover
    assert entry.winfo_manager() == ""
    assert texts(popover)[0] == f"{SNIPPET_70}   word 71 of 1,200"
    # Losing the keyboard right after mustn't save what was typed.
    entry._entry.event_generate("<FocusOut>")
    settle(scene.app, 100)
    assert rename_calls == []
    assert labels_saved(scene)[70] == ""

    press(scene, "Escape")

    assert scene.popover is None
    assert not popover.winfo_exists()


# ---- deleting ----

def test_the_x_button_removes_that_bookmark_and_nothing_else(scene):
    popover = scene.open_list()
    first = rows(popover)[0]

    click_button(parts(first)[0])
    settle(scene.app, AFTER_THE_WAIT_MS)

    assert [b.index for b in scene.a.bookmarks] == [300]
    assert texts(popover) == [f"{SNIPPET_300}   word 301 of 1,200"]
    assert scene.popover is popover, "deleting shouldn't close the list"
    assert scene.reader.session.index == 0, "the click went through to the row and jumped"
    assert scene.owner.scrub_bar._bookmark_indices == [300]
    assert [b["index"] for b in scene.saved(scene.a)["bookmarks"]] == [300]
    assert [b["index"] for b in scene.saved(scene.b)["bookmarks"]] == [70]


# ---- the add / remove button ----

def test_the_button_adds_and_removes_a_bookmark_at_the_current_word(scene):
    scene.reader.jump_to(40)
    popover = scene.open_list()
    button = popover.toggle_button
    assert (button.cget("text"), button.cget("state")) == ("Add bookmark here", "normal")

    button.invoke()
    settle(scene.app, 100)

    assert [b.index for b in scene.a.bookmarks] == [40, 70, 300]
    assert scene.a.bookmarks[0].snippet == "w37 w38 w39 w40 w41 w42 w43"
    assert button.cget("text") == "Remove bookmark here"
    assert len(rows(popover)) == 3
    assert scene.owner.scrub_bar._bookmark_indices == [40, 70, 300]
    assert [b["index"] for b in scene.saved(scene.a)["bookmarks"]] == [40, 70, 300]
    assert [b["index"] for b in scene.saved(scene.b)["bookmarks"]] == [70]

    button.invoke()
    settle(scene.app, 100)

    assert [b.index for b in scene.a.bookmarks] == [70, 300]
    assert button.cget("text") == "Add bookmark here"
    assert len(rows(popover)) == 2
    assert scene.owner.scrub_bar._bookmark_indices == [70, 300]


def test_with_no_word_on_screen_the_button_is_off(main_scene, monkeypatch):
    """Once reading has finished there is no word to bookmark, which is what
    current_bookmark_target() answers with None for."""
    scene = main_scene
    popover = scene.open_list()
    monkeypatch.setattr(scene.reader, "current_bookmark_target", lambda: None)

    scene.owner._refresh_bookmarks_popover()
    settle(scene.app, 100)
    popover.toggle_button.invoke()

    assert popover.toggle_button.cget("state") == "disabled"
    assert popover.toggle_button.cget("text") == "Add bookmark here"
    assert [b.index for b in scene.a.bookmarks] == [70, 300]


# ---- closing ----

@pytest.fixture
def background_errors(scene):
    """Whatever Tk reports as an error from a timer or other background
    callback while the test runs. It would normally go to the console, where
    nobody would see it."""
    errors = []
    scene.app.tk.createcommand("bgerror", lambda *message: errors.append(message))
    return errors


def test_closing_the_list_cancels_a_jump_that_is_waiting(scene, background_errors):
    """Closing destroys the list, and a timer left behind by a destroyed window
    doesn't jump, but Tk reports an error for it when it goes off."""
    popover = scene.open_list()
    click_label(rows(popover)[0])
    assert popover._pending_click_ids

    press(scene, "Escape")
    settle(scene.app, AFTER_THE_WAIT_MS)

    assert not popover.winfo_exists()
    assert scene.reader.session.index == 0
    assert scene.saved(scene.a)["position"] == 0
    assert background_errors == []


def test_a_change_to_the_list_cancels_a_jump_that_is_waiting(main_scene):
    """The rows a click was waiting on are rebuilt when the list changes, so
    it jumps nowhere."""
    scene = main_scene
    popover = scene.open_list()
    click_label(rows(popover)[1])

    scene.owner.toggle_bookmark_here()
    settle(scene.app, AFTER_THE_WAIT_MS)

    assert popover._pending_click_ids == set()
    assert scene.reader.session.index == 0
    assert scene.popover is popover


def test_esc_closes_the_list_and_it_opens_again(scene):
    popover = scene.open_list()

    press(scene, "Escape")

    assert scene.popover is None
    assert not popover.winfo_exists()
    assert scene.owner is not None and scene.reader.session.index == 0

    again = scene.open_list()
    assert again is not popover
    assert len(rows(again)) == 2


def test_opening_it_while_it_is_open_shows_the_same_window_up_to_date(scene):
    popover = scene.open_list()
    scene.app.store.add_bookmark(scene.a.id, 500, "w497 w498 w499 w500 w501 w502 w503")

    scene.owner.open_bookmarks()
    settle(scene.app, 200)

    assert scene.popover is popover
    assert len(rows(popover)) == 3
