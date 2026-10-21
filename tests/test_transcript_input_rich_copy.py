"""Tests for copying the edit box's selection with its bold (gui/components/
transcript_input.py): Ctrl+C while the bold look is on, and "Copy with bold" in the
right-click menu.

The Windows clipboard cannot be used here, so gui.rich_clipboard.copy_rich is swapped
for a stand-in that records what it was given and answers true or false as the test
says. What is checked is everything on this side of it: that the selection is read
off the screen as exactly the right pieces, that the right thing is handed over, and
that when the rich copy does not work (or is not wanted) Tk's own plain copy still
happens. The events run through a real mainloop(), since Tk's own bindings call into
Python there and an error left behind only shows once the loop runs.
Word itself is looked at by hand."""

import random
import tkinter
from types import SimpleNamespace

import customtkinter as ctk
import pytest

from core.bold_starts import bold_ranges
from core.rich_copy import segments_text


@pytest.fixture(scope="module")
def root():
    try:
        window = ctk.CTk()
    except tkinter.TclError:
        pytest.skip("no display available for Tk")
    window.geometry("400x300+0+0")
    yield window
    # See the same fixture in test_transcript_input_edit_forwarder.py: timers a
    # CustomTkinter window leaves behind would run into the next test module.
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.after_cancel(timer)
    window.destroy()


@pytest.fixture
def make_box(root):
    from gui.components.transcript_input import TranscriptInput

    made = []

    def build(text="", **kwargs):
        box = TranscriptInput(root, on_submit=lambda t: None, initial_text=text, **kwargs)
        box.pack(fill="both", expand=True)
        root.update()
        made.append(box)
        return box

    yield build
    for box in made:
        box.destroy()


@pytest.fixture
def rich(monkeypatch):
    """Stands in for copy_rich. rich.answer is what it says; rich.calls is what it
    was given, as (owner, plain text, html bytes)."""
    from gui.components import transcript_input

    stand_in = SimpleNamespace(answer=True, calls=[])

    def fake(owner, plain, html):
        stand_in.calls.append((owner, plain, html))
        return stand_in.answer

    monkeypatch.setattr(transcript_input, "copy_rich", fake)
    return stand_in


def inner_of(box):
    return box.textbox._textbox


def select(box, first, last):
    inner = inner_of(box)
    inner.tag_remove("sel", "1.0", "end")
    inner.tag_add("sel", first, last)


def run_mainloop(root, milliseconds=60):
    root.after(milliseconds, root.quit)
    root.mainloop()


def copy_key(root, box):
    """What Ctrl+C turns into, sent to the edit box, with the real loop run after."""
    inner = inner_of(box)
    inner.focus_force()
    root.update()
    inner.event_generate("<<Copy>>")
    run_mainloop(root)


def cut_key(root, box):
    inner = inner_of(box)
    inner.focus_force()
    root.update()
    inner.event_generate("<<Cut>>")
    run_mainloop(root)


def clipboard_holds(root, text):
    root.clipboard_clear()
    root.clipboard_append(text)


def clipboard_text(root):
    try:
        return root.clipboard_get()
    except tkinter.TclError:
        return ""


def expected_pieces(text):
    """What a selection of the whole text should read as, worked out from the
    algorithm alone, one character at a time: (character, bold)."""
    flags = []
    for line in text.split("\n"):
        bold = [False] * len(line)
        for start, end in bold_ranges(line):
            for index in range(start, end):
                bold[index] = True
        flags.extend(bold)
        flags.append(False)
    flags.pop()
    return list(zip(text, flags))


def flatten(pieces):
    return [(char, bold) for text, bold in pieces for char in text]


# ---- reading the selection off the screen ----

# "hello world" is shown as **hel**lo **wor**ld: five letters get three bold ones.
@pytest.mark.parametrize("first, last, wanted", [
    ("1.0", "1.11", [("hel", True), ("lo ", False), ("wor", True), ("ld", False)]),
    ("1.1", "1.8", [("el", True), ("lo ", False), ("wo", True)]),           # begins and ends inside a bold stretch
    ("1.1", "1.7", [("el", True), ("lo ", False), ("w", True)]),
    ("1.2", "1.7", [("l", True), ("lo ", False), ("w", True)]),             # begins on the last bold letter
    ("1.3", "1.7", [("lo ", False), ("w", True)]),                          # begins in plain text
    ("1.6", "1.11", [("wor", True), ("ld", False)]),                        # begins exactly at a bold stretch
    ("1.0", "1.2", [("he", True)]),                                         # only bold
    ("1.3", "1.6", [("lo ", False)]),                                       # only plain
])
def test_the_selection_reads_as_the_right_pieces(make_box, first, last, wanted):
    box = make_box("hello world", bold_starts=True)
    select(box, first, last)
    assert box._selection_pieces() == wanted

def test_another_tag_over_the_selection_does_not_change_what_is_bold(make_box):
    # Only the bold tag counts. A different tag that starts or stops in the middle
    # of a bold stretch must not switch the bold on or off.
    box = make_box("hello world", bold_starts=True)
    inner = inner_of(box)
    inner.tag_add("other", "1.1", "1.2")           # ends inside the first bold stretch
    inner.tag_add("other", "1.7", "1.8")           # starts and ends inside the second
    select(box, "1.0", "1.11")
    # Tk cuts the text where the other tag changes, so the pieces may be more and
    # smaller (cf_html joins neighbours that are alike). What counts is which
    # characters are bold.
    assert flatten(box._selection_pieces()) == flatten(
        [("hel", True), ("lo ", False), ("wor", True), ("ld", False)])

def test_the_pieces_add_up_to_the_selected_text(make_box):
    box = make_box("hello world\nsecond line here", bold_starts=True)
    select(box, "1.3", "2.6")
    pieces = box._selection_pieces()
    assert segments_text(pieces) == inner_of(box).get("sel.first", "sel.last")

def test_nothing_selected_gives_nothing(make_box):
    box = make_box("hello world", bold_starts=True)
    assert box._selection_pieces() is None

def test_with_the_look_off_everything_is_plain(make_box):
    box = make_box("hello world", bold_starts=False)
    select(box, "1.0", "1.11")
    assert box._selection_pieces() == [("hello world", False)]

def test_lines_over_the_limit_stay_plain_in_the_copy_as_on_screen(make_box):
    from core.bold_spans import MAX_BOLD_LINE

    long_line = ("word " * (MAX_BOLD_LINE // 4))[:MAX_BOLD_LINE + 10]
    box = make_box(long_line + "\nshort one", bold_starts=True)
    select(box, "1.0", "end-1c")
    pieces = box._selection_pieces()
    assert segments_text(pieces) == long_line + "\nshort one"
    first_line = "".join(text for text, _ in pieces)[:len(long_line)]
    assert not any(bold for char, bold in flatten(pieces)[:len(long_line)])
    assert any(bold for char, bold in flatten(pieces)[len(long_line):])
    assert first_line == long_line

def test_the_whole_text_reads_back_exactly_with_cyrillic_emoji_and_line_breaks(make_box):
    rng = random.Random(20261021)
    alphabet = list("abcxyz") + list("абвгде") + ["\U0001F600", " ", " ", " ", "\n", "-", "'", "1", "\t"]
    for _ in range(40):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 60)))
        box = make_box(text, bold_starts=True)
        select(box, "1.0", "end-1c")
        pieces = box._selection_pieces()
        assert segments_text(pieces) == inner_of(box).get("1.0", "end-1c")
        assert flatten(pieces) == expected_pieces(text), repr(text)
        box.destroy()


# ---- Ctrl+C ----

def test_ctrl_c_with_the_look_on_hands_the_selection_and_its_bold_over(root, make_box, rich):
    box = make_box("hello world", bold_starts=True)
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.5")
    copy_key(root, box)
    assert len(rich.calls) == 1
    owner, plain, html = rich.calls[0]
    assert owner == inner_of(box).winfo_id()
    assert plain == "hello"
    assert html.startswith(b"Version:0.9") and b"<b>hel</b>lo" in html

def test_when_the_rich_copy_works_tks_own_copy_does_not_run_after_it(root, make_box, rich):
    box = make_box("hello world", bold_starts=True)
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.5")
    copy_key(root, box)
    assert clipboard_text(root) == "OLD"

def test_when_the_rich_copy_does_not_work_the_plain_copy_still_happens(root, make_box, rich):
    rich.answer = False
    box = make_box("hello world", bold_starts=True)
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.5")
    copy_key(root, box)
    assert len(rich.calls) == 1
    assert clipboard_text(root) == "hello"

def test_with_the_look_off_ctrl_c_is_the_plain_copy_it_always_was(root, make_box, rich):
    box = make_box("hello world", bold_starts=False)
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.5")
    copy_key(root, box)
    assert rich.calls == []
    assert clipboard_text(root) == "hello"

def test_ctrl_c_with_nothing_selected_does_nothing_and_does_not_close_the_app(root, make_box, rich):
    box = make_box("hello world", bold_starts=True)
    clipboard_holds(root, "OLD")
    copy_key(root, box)
    assert rich.calls == []
    assert clipboard_text(root) == "OLD"

def test_pieces_that_do_not_match_the_text_fall_back_to_the_plain_copy(root, make_box, rich):
    box = make_box("hello world", bold_starts=True)
    box._selection_pieces = lambda: [("something else", True)]
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.5")
    copy_key(root, box)
    assert rich.calls == []
    assert clipboard_text(root) == "hello"

def test_a_selection_that_cannot_be_read_falls_back_to_the_plain_copy(root, make_box, rich):
    box = make_box("hello world", bold_starts=True)

    def broken():
        raise tkinter.TclError("gone")

    box._selection_pieces = broken
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.5")
    assert box._copy_with_bold() is False
    errors = []
    previous = root.report_callback_exception
    root.report_callback_exception = lambda kind, value, trace: errors.append(value)
    try:
        copy_key(root, box)
    finally:
        root.report_callback_exception = previous
    assert errors == []                     # nothing went wrong inside Tk's handler
    assert rich.calls == []
    assert clipboard_text(root) == "hello"

def test_a_selection_with_no_text_in_it_is_not_copied_with_bold(root, make_box, rich):
    box = make_box("hello world", bold_starts=True)
    box._selection_pieces = lambda: []
    select(box, "1.0", "1.5")
    assert box._copy_with_bold() is False
    assert rich.calls == []

def test_copying_changes_neither_the_text_nor_the_bold_nor_the_selection(root, make_box, rich):
    from gui.components.transcript_input import BOLD_TAG

    box = make_box("hello world", bold_starts=True)
    inner = inner_of(box)
    select(box, "1.1", "1.8")
    before = (inner.get("1.0", "end-1c"), inner.tag_ranges(BOLD_TAG), inner.tag_ranges("sel"))
    copy_key(root, box)
    assert (inner.get("1.0", "end-1c"), inner.tag_ranges(BOLD_TAG), inner.tag_ranges("sel")) == before

def test_cut_stays_the_plain_cut_and_keeps_the_bold_right(root, make_box, rich):
    from gui.components.transcript_input import BOLD_TAG

    box = make_box("hello world", bold_starts=True)
    inner = inner_of(box)
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.6")
    cut_key(root, box)
    assert rich.calls == []
    assert clipboard_text(root) == "hello "
    assert inner.get("1.0", "end-1c") == "world"
    ranges = inner.tag_ranges(BOLD_TAG)
    assert [(str(ranges[i]), str(ranges[i + 1])) for i in range(0, len(ranges), 2)] == [("1.0", "1.3")]


# ---- the right-click menu ----

def event():
    return SimpleNamespace(x_root=10, y_root=10)


def menu_rows(box):
    popup = box._selection_menu
    frame = popup.winfo_children()[0]
    return [row.cget("text") for row in frame.winfo_children()]


def click_row(root, box, label):
    # The popup has to be on screen before it takes a click, which Tk does when it
    # next gets a turn.
    root.update()
    frame = box._selection_menu.winfo_children()[0]
    for row in frame.winfo_children():
        if row.cget("text") == label:
            row.event_generate("<Button-1>")
            return
    raise AssertionError(f"no row {label!r} in {menu_rows(box)}")


def test_the_menu_offers_copy_with_bold_when_the_look_is_on(make_box):
    box = make_box("hello world", bold_starts=True, on_play_selection=lambda t: None, on_detach_selection=lambda t: None)
    select(box, "1.0", "1.5")
    assert box._show_selection_menu(event()) == "break"
    assert menu_rows(box) == ["Play", "Detach", "Copy with bold"]

def test_the_menu_does_not_offer_it_when_the_look_is_off(make_box):
    box = make_box("hello world", bold_starts=False, on_play_selection=lambda t: None, on_detach_selection=lambda t: None)
    select(box, "1.0", "1.5")
    assert box._show_selection_menu(event()) == "break"
    assert menu_rows(box) == ["Play", "Detach"]

def test_a_box_with_no_play_or_detach_still_gets_the_menu_for_the_copy(make_box):
    box = make_box("hello world", bold_starts=True)
    select(box, "1.0", "1.5")
    assert box._show_selection_menu(event()) == "break"
    assert menu_rows(box) == ["Copy with bold"]

def test_a_box_with_nothing_to_offer_opens_no_menu(make_box):
    box = make_box("hello world", bold_starts=False)
    select(box, "1.0", "1.5")
    assert box._show_selection_menu(event()) is None
    assert box._selection_menu is None

def test_no_selection_no_menu(make_box):
    box = make_box("hello world", bold_starts=True)
    assert box._show_selection_menu(event()) is None
    assert box._selection_menu is None

def test_the_menu_is_there_after_the_look_is_switched_on_and_gone_after_off(make_box):
    box = make_box("hello world", bold_starts=False)
    select(box, "1.0", "1.5")
    assert box._show_selection_menu(event()) is None
    box.set_bold_starts(True)
    assert box._show_selection_menu(event()) == "break"
    assert menu_rows(box) == ["Copy with bold"]
    box._close_selection_menu()
    box.set_bold_starts(False)
    assert box._show_selection_menu(event()) is None

def test_clicking_copy_with_bold_copies_and_says_so(root, make_box, rich):
    from gui.components.transcript_input import COPIED_WITH_BOLD

    box = make_box("hello world", bold_starts=True)
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.5")
    box._show_selection_menu(event())
    click_row(root, box, "Copy with bold")
    run_mainloop(root)
    assert len(rich.calls) == 1 and rich.calls[0][1] == "hello" and b"<b>hel</b>lo" in rich.calls[0][2]
    assert box.feedback_label.cget("text") == COPIED_WITH_BOLD
    assert box._selection_menu_visible is False
    assert clipboard_text(root) == "OLD"

def test_clicking_it_when_the_rich_copy_fails_copies_plain_text_and_says_so(root, make_box, rich):
    from gui.components.transcript_input import COPIED_PLAIN

    rich.answer = False
    box = make_box("hello world", bold_starts=True)
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.5")
    box._show_selection_menu(event())
    click_row(root, box, "Copy with bold")
    run_mainloop(root)
    assert clipboard_text(root) == "hello"
    assert box.feedback_label.cget("text") == COPIED_PLAIN

def test_the_plain_fallback_uses_the_whole_selection_not_the_trimmed_one(root, make_box, rich):
    rich.answer = False
    box = make_box("  hello world  ", bold_starts=True)
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.15")
    box._show_selection_menu(event())
    click_row(root, box, "Copy with bold")
    run_mainloop(root)
    assert clipboard_text(root) == "  hello world  "

def test_the_plain_fallback_still_works_if_the_selection_is_gone_by_the_click(root, make_box, rich):
    rich.answer = False
    box = make_box("hello world", bold_starts=True)
    clipboard_holds(root, "OLD")
    select(box, "1.0", "1.5")
    box._show_selection_menu(event())
    inner_of(box).tag_remove("sel", "1.0", "end")
    click_row(root, box, "Copy with bold")
    run_mainloop(root)
    assert clipboard_text(root) == "hello"

def test_clicking_copy_does_not_run_play_or_detach(root, make_box, rich):
    asked = []
    box = make_box("hello world", bold_starts=True,
                   on_play_selection=asked.append, on_detach_selection=asked.append)
    select(box, "1.0", "1.5")
    box._show_selection_menu(event())
    click_row(root, box, "Copy with bold")
    run_mainloop(root)
    assert asked == []