"""Tests for the header row (gui/components/header.py): a long transcript name
must never push the Settings button out of the row.

A file import names the transcript after the file, so titles can be much longer
than the room beside the button. Before, the title label was packed first and
asked for all the width its text needed, which left the button no room at all:
it was not drawn. Now the button is packed first and the title is cut down with
an ellipsis to what is left.

These run against a real Tk with one hidden root for the whole module. A hidden
window never gets a real size, so everything that measures is built in a mapped
CTkToplevel, and sizes are read from the widgets, never assumed from a 100%
display."""

import customtkinter as ctk
import pytest

from core.text_fit import ELLIPSIS
from gui.components.header import Header

LONG_TITLE = (
    "Lecture week seven, the long recording transcript with an extra long title "
    "that just goes on and on and on, far past the room beside the button"
)


@pytest.fixture
def scaling():
    """Sets CustomTkinter's extra scaling factor for one test and always puts it
    back to 1.0. It stacks on top of the display's own scaling."""
    def set_to(factor):
        ctk.set_widget_scaling(factor)
        ctk.set_window_scaling(factor)

    yield set_to
    set_to(1.0)


@pytest.fixture
def shown_header(root, wait_until_shown):
    """Builds a header with a title in a mapped window of the given width and
    returns (window, header). The window is destroyed after the test."""
    windows = []

    def build(width=700, title=LONG_TITLE):
        top = ctk.CTkToplevel(root)
        top.geometry(f"{width}x200+0+0")
        header = Header(top)
        header.pack(fill="x")
        if title is not None:
            header.set_title(title)
        wait_until_shown(top)
        assert header.winfo_width() > 1, "the window was not laid out"
        windows.append(top)
        return top, header

    yield build
    for top in windows:
        for timer in top.tk.splitlist(top.tk.call("after", "info")):
            top.tk.call("after", "cancel", timer)
        top.destroy()


def resize(top, width, wait):
    top.geometry(f"{width}x200")
    wait(top)


def shown_text(header) -> str:
    return header.title_label.cget("text")


def text_fits(header) -> bool:
    """Whether the text the label draws fits inside the label itself. The text
    sits on an inner tkinter label, whose requested width is the width of the
    text in real screen pixels."""
    return header.title_label._label.winfo_reqwidth() <= header.title_label.winfo_width()


def button_is_inside(header) -> bool:
    button = header.settings_button
    left = header.winfo_rootx()
    return (
        button.winfo_ismapped()
        and button.winfo_width() > 1
        and button.winfo_rootx() >= left
        and button.winfo_rootx() + button.winfo_width() <= left + header.winfo_width()
    )


def title_ends_before_button(header) -> bool:
    label = header.title_label
    return label.winfo_rootx() + label.winfo_width() <= header.settings_button.winfo_rootx()


# ---- a long title ----

def test_a_long_title_keeps_the_settings_button_in_the_row(shown_header):
    _, header = shown_header(700)
    assert button_is_inside(header)
    assert title_ends_before_button(header)


def test_a_long_title_is_cut_with_an_ellipsis_and_fits(shown_header):
    _, header = shown_header(700)
    shown = shown_text(header)
    assert shown.endswith(ELLIPSIS)
    assert len(shown) < len(LONG_TITLE)
    assert LONG_TITLE.startswith(shown[:-1])
    assert text_fits(header)


def test_a_title_set_after_the_window_is_shown_is_cut_at_once(shown_header):
    _, header = shown_header(700, title=None)
    header.set_title(LONG_TITLE)
    assert shown_text(header).endswith(ELLIPSIS)
    assert text_fits(header)


def test_a_short_title_is_shown_whole(shown_header):
    _, header = shown_header(700, title="Short title")
    assert shown_text(header) == "Short title"
    assert button_is_inside(header)


def test_nothing_selected_is_shown_whole_at_the_start(shown_header):
    _, header = shown_header(700, title=None)
    assert shown_text(header) == "No transcript selected"


def test_a_long_title_followed_by_a_short_one_shows_the_short_one_whole(shown_header):
    _, header = shown_header(700)
    header.set_title("Short title")
    assert shown_text(header) == "Short title"


# ---- following the window ----

def test_the_title_follows_the_window_when_it_gets_narrower_and_wider(shown_header, wait_until_shown):
    top, header = shown_header(900)
    wide = shown_text(header)
    resize(top, 500, wait_until_shown)
    narrow = shown_text(header)
    assert len(narrow) < len(wide)
    assert narrow.endswith(ELLIPSIS)
    assert text_fits(header)
    assert button_is_inside(header)

    resize(top, 900, wait_until_shown)
    assert shown_text(header) == wide


def test_a_title_that_got_cut_comes_back_whole_in_a_wide_enough_window(shown_header, wait_until_shown):
    title = "A title of middling length for this test"
    top, header = shown_header(220, title=title)
    assert shown_text(header).endswith(ELLIPSIS)
    assert button_is_inside(header)

    resize(top, 900, wait_until_shown)
    assert shown_text(header) == title


def test_a_very_narrow_window_still_keeps_the_button(shown_header):
    _, header = shown_header(260)
    assert button_is_inside(header)
    assert text_fits(header)


# ---- display scaling ----

@pytest.mark.parametrize("factor", [1.5, 2.0])
def test_a_scaled_display_keeps_the_button_and_the_title_fits(shown_header, scaling, factor):
    scaling(factor)
    _, header = shown_header(700)
    assert header.title_label._get_widget_scaling() > 1.0
    assert button_is_inside(header)
    assert title_ends_before_button(header)
    assert shown_text(header).endswith(ELLIPSIS)
    assert text_fits(header)


# ---- the button still works ----

def test_the_settings_button_still_calls_back(root):
    calls = []
    header = Header(root, on_settings=lambda: calls.append(1))
    try:
        header.settings_button.invoke()
        assert calls == [1]
    finally:
        header.destroy()