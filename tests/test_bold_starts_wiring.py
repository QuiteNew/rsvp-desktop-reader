"""Tests for how the bold word starts button is wired through the windows
(gui/components/canvas.py, detached_window.py and selection_preview_window.py).

The button and the look itself are tested in test_transcript_input_bold_starts.py
and test_transcript_input_bold_live.py. This file checks the plumbing around it:

- the main edit box and the detached window's are one setting, so a click in
  either is passed on to the owner (who saves it) and the other one follows;
- a selection preview (right-click Detach) opens with the look the app has at
  that moment, but keeps its own button: a click there stays in that window, and
  later changes in the app do not reach it, like the rest of its styling.

A Canvas is built on its own here, with a plain callback standing in for the app,
on the hidden root conftest.py gives each module. The toolbar keeps a picture made
for the root it was first built on, and that fixture empties those caches around
the root."""

import pytest

from core.models import Transcript

from tk_helpers import cancel_pending_afters, settle


@pytest.fixture
def make_canvas(root):
    """Builds Canvases, each remembering what its owner was told, and takes down
    every window they opened afterwards."""
    from gui.components.canvas import Canvas

    made = []

    def build(**kwargs):
        told = []
        canvas = Canvas(root, on_bold_starts_toggled=told.append, **kwargs)
        canvas.pack()
        canvas.load_transcript(Transcript(id=1, title="Test", space="Main"))
        root.update()
        made.append(canvas)
        return canvas, told

    yield build
    for canvas in made:
        for window, _, _ in list(canvas._selection_previews):
            settle(window)
            cancel_pending_afters(window)
            window.close()
        if canvas._detached_window is not None:
            window = canvas._detached_window
            settle(window)
            cancel_pending_afters(window)
            window.close()
        settle(root, 100)
        canvas.destroy()


def bold_pieces(input_view):
    """What the edit box really has in bold, read back through the Tk tag."""
    from gui.components.transcript_input import BOLD_TAG

    inner = input_view.textbox._textbox
    ranges = inner.tag_ranges(BOLD_TAG)
    return [inner.get(str(ranges[i]), str(ranges[i + 1])) for i in range(0, len(ranges), 2)]


def is_on(input_view):
    """Whether the box shows the look, by its text: the same words in bold or not."""
    input_view.set_text("hello world")
    return bold_pieces(input_view) == ["hel", "wor"]


def click(input_view):
    input_view.bold_starts_button.invoke()


def open_detached(canvas):
    canvas._handle_detach()
    window = canvas._detached_window
    assert window is not None
    settle(window)
    return window


def open_preview(canvas, text="alpha beta gamma"):
    canvas.open_selection_preview(text)
    window = canvas._selection_previews[-1][0]
    settle(window)
    return window


# ---- the main edit box ----

def test_the_main_edit_box_starts_out_plain(make_canvas):
    canvas, told = make_canvas()
    assert not is_on(canvas.input_view)

def test_the_main_edit_box_starts_out_with_the_look_the_app_remembers(make_canvas):
    canvas, told = make_canvas(bold_starts_enabled=True)
    assert is_on(canvas.input_view)

def test_a_click_in_the_main_edit_box_tells_the_owner(make_canvas):
    canvas, told = make_canvas()
    click(canvas.input_view)
    click(canvas.input_view)
    assert told == [True, False]

def test_a_click_in_the_main_edit_box_changes_the_look_there(make_canvas):
    canvas, told = make_canvas()
    click(canvas.input_view)
    assert is_on(canvas.input_view)
    click(canvas.input_view)
    assert not is_on(canvas.input_view)

def test_a_click_is_fine_when_nobody_is_listening(root):
    from gui.components.canvas import Canvas

    canvas = Canvas(root)
    try:
        canvas.pack()
        click(canvas.input_view)
        assert is_on(canvas.input_view)
    finally:
        canvas.destroy()
        settle(root, 100)

def test_set_bold_starts_enabled_changes_the_main_box_without_telling_the_owner(make_canvas):
    canvas, told = make_canvas()
    canvas.set_bold_starts_enabled(True)
    assert is_on(canvas.input_view)
    canvas.set_bold_starts_enabled(False)
    assert not is_on(canvas.input_view)
    assert told == []


# ---- the detached window ----

def test_a_detached_window_opens_with_the_look_the_app_has(make_canvas):
    canvas, told = make_canvas(bold_starts_enabled=True)
    window = open_detached(canvas)
    assert is_on(window.input_view)

def test_a_detached_window_opens_plain_when_the_look_is_off(make_canvas):
    canvas, told = make_canvas()
    window = open_detached(canvas)
    assert not is_on(window.input_view)

def test_a_detached_window_opened_after_a_click_has_the_new_look(make_canvas):
    canvas, told = make_canvas()
    click(canvas.input_view)
    window = open_detached(canvas)
    assert is_on(window.input_view)

def test_a_click_in_the_detached_window_tells_the_owner(make_canvas):
    canvas, told = make_canvas()
    window = open_detached(canvas)
    click(window.input_view)
    assert told == [True]
    click(window.input_view)
    assert told == [True, False]

def test_a_click_in_the_detached_window_reaches_the_main_box_too(make_canvas):
    canvas, told = make_canvas()
    window = open_detached(canvas)
    click(window.input_view)
    assert is_on(canvas.input_view)
    assert is_on(window.input_view)
    click(window.input_view)
    assert not is_on(canvas.input_view)

def test_the_main_box_changing_reaches_an_open_detached_window(make_canvas):
    canvas, told = make_canvas()
    window = open_detached(canvas)
    canvas.set_bold_starts_enabled(True)
    assert is_on(window.input_view)
    canvas.set_bold_starts_enabled(False)
    assert not is_on(window.input_view)
    assert told == []

def test_the_look_still_changes_after_the_detached_window_is_closed(make_canvas, root):
    canvas, told = make_canvas()
    window = open_detached(canvas)
    click(window.input_view)
    cancel_pending_afters(window)
    window.close()
    settle(root, 100)
    assert canvas._detached_window is None
    canvas.set_bold_starts_enabled(False)
    assert not is_on(canvas.input_view)
    click(canvas.input_view)
    assert told == [True, True]
    assert is_on(canvas.input_view)


# ---- the selection previews ----

def test_a_preview_opens_with_the_look_the_app_has(make_canvas):
    canvas, told = make_canvas(bold_starts_enabled=True)
    preview = open_preview(canvas)
    assert is_on(preview.input_view)

def test_a_preview_opens_plain_when_the_look_is_off(make_canvas):
    canvas, told = make_canvas()
    preview = open_preview(canvas)
    assert not is_on(preview.input_view)

def test_a_preview_opened_after_a_click_has_the_new_look(make_canvas):
    canvas, told = make_canvas()
    click(canvas.input_view)
    preview = open_preview(canvas)
    assert is_on(preview.input_view)

def test_a_click_in_a_preview_changes_only_that_preview(make_canvas):
    canvas, told = make_canvas()
    first = open_preview(canvas, "alpha beta gamma")
    second = open_preview(canvas, "delta epsilon zeta")
    click(first.input_view)
    assert is_on(first.input_view)
    assert not is_on(second.input_view)
    assert not is_on(canvas.input_view)

def test_a_click_in_a_preview_is_not_saved_or_reported(make_canvas):
    canvas, told = make_canvas()
    preview = open_preview(canvas)
    click(preview.input_view)
    click(preview.input_view)
    assert told == []
    assert canvas._bold_starts_enabled is False

def test_a_click_in_a_preview_does_not_reach_the_detached_window(make_canvas):
    canvas, told = make_canvas()
    detached = open_detached(canvas)
    preview = open_preview(canvas)
    click(preview.input_view)
    assert is_on(preview.input_view)
    assert not is_on(detached.input_view)

def test_an_open_preview_keeps_its_look_when_the_app_changes(make_canvas):
    canvas, told = make_canvas()
    preview = open_preview(canvas)
    canvas.set_bold_starts_enabled(True)
    assert not is_on(preview.input_view)
    click(preview.input_view)
    canvas.set_bold_starts_enabled(False)
    assert is_on(preview.input_view)

def test_a_click_in_the_main_box_does_not_reach_an_open_preview(make_canvas):
    canvas, told = make_canvas()
    preview = open_preview(canvas)
    click(canvas.input_view)
    assert not is_on(preview.input_view)
    assert told == [True]