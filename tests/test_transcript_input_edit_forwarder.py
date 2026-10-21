"""Tests for the forwarder that sits in front of the edit box's Text command
(gui/components/transcript_input.py: _EditBox).

The forwarder passes every call on and reports edits. The tests in
test_transcript_input_bold_live.py check the reporting. This file checks the part
that has to be invisible: errors, results and Tk's own bindings behave exactly as
they do on a plain Text widget.

Why it needs its own file. Tk's copy, cut and (on Windows) paste bindings call the
widget command inside a Tcl catch, and with nothing selected that call fails on
purpose. A forwarder written as a Python command made that failure escape the
catch: tkinter remembers an exception raised by a command it registered, and raises
it again out of mainloop(), so pasting into the draft closed the whole app. None of
the earlier tests could see it, because they drive Tk with update() and never run
mainloop(). So these do run it, through the real key bindings, and compare with a
plain Text widget doing the same thing."""

import tkinter

import customtkinter as ctk
import pytest

from core.bold_spans import tk_spans


@pytest.fixture(scope="module")
def root():
    try:
        window = ctk.CTk()
    except tkinter.TclError:
        pytest.skip("no display available for Tk")
    window.geometry("400x300+0+0")
    yield window
    # CustomTkinter keeps a few timers going on its windows, and a destroyed app
    # leaves the next round of them pending. They would run during the next test
    # module and report errors about a destroyed app, so cancel them first.
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
def plain_text(root):
    """A Text widget with nothing in front of it, for comparing against."""
    widget = tkinter.Text(root)
    widget.pack()
    root.update()
    yield widget
    widget.destroy()


@pytest.fixture
def pretend_windows(root):
    """Makes `tk windowingsystem` say win32 for a test. Tk's paste binding only
    tries to delete the selection first when it is not running on X11, and that is
    the call that closed the app on Windows."""
    root.tk.eval(
        "rename tk ::real_tk; proc tk {args} {"
        " if {[lindex $args 0] eq {windowingsystem}} {return win32};"
        " uplevel 1 ::real_tk $args }"
    )
    yield
    root.tk.eval("rename tk {}; rename ::real_tk tk")


def inner_of(box):
    return box.textbox._textbox


def run_mainloop(root, milliseconds=60):
    """Let Tk's real event loop run for a moment, the way the running app does.
    An error that an earlier call left behind is raised from here."""
    root.after(milliseconds, root.quit)
    root.mainloop()


def clipboard_holds(root, text):
    root.clipboard_clear()
    root.clipboard_append(text)


def press(root, widget, event):
    """Send a virtual event (<<Copy>>, <<Cut>>, <<Paste>>), which is what Ctrl+C,
    Ctrl+X and Ctrl+V turn into, to a widget that has the focus."""
    widget.focus_force()
    root.update()
    widget.mark_set("insert", "end-1c")
    widget.event_generate(event)


# ---- Tk's own bindings, with nothing selected ----

@pytest.mark.parametrize("event", ["<<Copy>>", "<<Cut>>", "<<Paste>>"])
def test_the_key_bindings_with_nothing_selected_do_not_close_the_app(root, make_box, event):
    box = make_box("hello world")
    clipboard_holds(root, "PASTED")
    press(root, inner_of(box), event)
    run_mainloop(root)

@pytest.mark.parametrize("event", ["<<Copy>>", "<<Cut>>", "<<Paste>>"])
def test_the_key_bindings_do_the_same_as_on_a_plain_text_widget(root, make_box, plain_text, event):
    box = make_box("hello world")
    plain_text.insert("1.0", "hello world")
    clipboard_holds(root, "PASTED")
    press(root, inner_of(box), event)
    run_mainloop(root)
    clipboard_holds(root, "PASTED")
    press(root, plain_text, event)
    run_mainloop(root)
    assert inner_of(box).get("1.0", "end-1c") == plain_text.get("1.0", "end-1c")

def test_paste_on_windows_with_nothing_selected_does_not_close_the_app(root, make_box, plain_text, pretend_windows):
    # The case that was reported: Windows first tries to delete the selection,
    # which fails when there is none.
    box = make_box("hello world")
    plain_text.insert("1.0", "hello world")
    clipboard_holds(root, "PASTED")
    press(root, inner_of(box), "<<Paste>>")
    run_mainloop(root)
    clipboard_holds(root, "PASTED")
    press(root, plain_text, "<<Paste>>")
    run_mainloop(root)
    assert inner_of(box).get("1.0", "end-1c") == plain_text.get("1.0", "end-1c") == "hello worldPASTED"

def test_paste_on_windows_over_a_selection_replaces_it_and_keeps_the_bold_right(root, make_box, plain_text, pretend_windows):
    from gui.components import transcript_input

    box = make_box("hello world", bold_starts=True)
    inner = inner_of(box)
    plain_text.insert("1.0", "hello world")
    for widget in (inner, plain_text):
        # The selection and the cursor at the start of it, as a person leaves them.
        widget.tag_add("sel", "1.0", "1.5")
        widget.mark_set("insert", "1.0")
        clipboard_holds(root, "brand new")
        widget.focus_force()
        root.update()
        widget.event_generate("<<Paste>>")
        run_mainloop(root)
    text = inner.get("1.0", "end-1c")
    assert text == plain_text.get("1.0", "end-1c") == "brand new world"
    ranges = inner.tag_ranges(transcript_input.BOLD_TAG)
    found = [(str(ranges[i]), str(ranges[i + 1])) for i in range(0, len(ranges), 2)]
    wanted = tk_spans(text, transcript_input._tk_astral_width(box), 1, transcript_input.MAX_BOLD_LINE)
    assert found == [(f"{line}.{a}", f"{line}.{b}") for line, a, b in wanted]


# ---- errors are handed back untouched ----

def test_a_failing_call_reaches_python_with_tks_own_message(root, make_box, plain_text):
    box = make_box("hello world")
    plain_text.insert("1.0", "hello world")
    with pytest.raises(tkinter.TclError) as plain:
        plain_text.delete("sel.first", "sel.last")
    with pytest.raises(tkinter.TclError) as wrapped:
        inner_of(box).delete("sel.first", "sel.last")
    assert str(wrapped.value) == str(plain.value)

def test_a_failing_call_caught_in_python_does_not_close_the_app_later(root, make_box):
    box = make_box("hello world")
    with pytest.raises(tkinter.TclError):
        inner_of(box).get("sel.first", "sel.last")
    with pytest.raises(tkinter.TclError):
        inner_of(box).delete("sel.first", "sel.last")
    run_mainloop(root)

def test_a_failing_call_inside_a_tcl_catch_does_not_close_the_app(root, make_box):
    box = make_box("hello world")
    path = str(inner_of(box))
    code = root.tk.eval(f"catch {{{path} delete sel.first sel.last}}")
    assert str(code) == "1"
    run_mainloop(root)

def test_a_bad_index_and_a_bad_subcommand_fail_the_way_they_always_did(root, make_box, plain_text):
    box = make_box("hello world")
    plain_text.insert("1.0", "hello world")
    for call in (
        lambda w: w.insert("not-an-index", "x"),
        lambda w: w.delete("not-an-index"),
        lambda w: w.tk.call(str(w), "nonsense"),
        lambda w: w.tk.call(str(w)),
    ):
        with pytest.raises(tkinter.TclError) as plain:
            call(plain_text)
        with pytest.raises(tkinter.TclError) as wrapped:
            call(inner_of(box))
        assert type(wrapped.value) is type(plain.value)
    run_mainloop(root)
    assert inner_of(box).get("1.0", "end-1c") == "hello world"


# ---- results and edits pass through once, unchanged ----

def test_an_edit_is_carried_out_exactly_once(make_box):
    box = make_box("hello world")
    inner = inner_of(box)
    inner.insert("end", " again")
    assert inner.get("1.0", "end-1c") == "hello world again"
    inner.replace("1.0", "1.5", "HELLO")
    assert inner.get("1.0", "end-1c") == "HELLO world again"
    inner.delete("1.5", "1.11")
    assert inner.get("1.0", "end-1c") == "HELLO again"

def test_results_of_reading_calls_are_unchanged(make_box, plain_text):
    box = make_box("one two\nthree four")
    plain_text.insert("1.0", "one two\nthree four")
    inner = inner_of(box)
    assert inner.get("1.0", "end-1c") == plain_text.get("1.0", "end-1c")
    assert inner.index("end") == plain_text.index("end")
    assert inner.index("1.3 + 2 chars") == plain_text.index("1.3 + 2 chars")
    assert inner.search("three", "1.0") == plain_text.search("three", "1.0")
    assert inner.count("1.0", "end", "chars") == plain_text.count("1.0", "end", "chars")

def test_a_good_edit_is_reported_once_with_its_lines(root):
    from gui.components.transcript_input import _EditBox

    told = []
    box = _EditBox(root, on_edited=lambda first, last: told.append((first, last)))
    box.pack()
    root.update()
    try:
        inner = box._textbox
        inner.insert("1.0", "one\ntwo\nthree")
        assert told == [(1, 3)]
        inner.delete("2.0", "3.0")
        assert told == [(1, 3), (2, 2)]
    finally:
        box.destroy()

def test_a_failed_edit_is_not_reported(root):
    from gui.components.transcript_input import _EditBox

    told = []
    box = _EditBox(root, on_edited=lambda first, last: told.append((first, last)))
    box.pack()
    root.update()
    try:
        inner = box._textbox
        inner.insert("1.0", "one two")
        told.clear()
        with pytest.raises(tkinter.TclError):
            inner.delete("sel.first", "sel.last")
        with pytest.raises(tkinter.TclError):
            inner.insert("not-an-index", "x")
        # These two get past the first index and only fail inside the real command.
        with pytest.raises(tkinter.TclError):
            inner.delete("1.0", "not-an-index")
        with pytest.raises(tkinter.TclError):
            inner.replace("1.0", "not-an-index", "x")
        assert told == []
        assert inner.get("1.0", "end-1c") == "one two"
    finally:
        box.destroy()

def test_reading_calls_are_never_reported(root):
    from gui.components.transcript_input import _EditBox

    told = []
    box = _EditBox(root, on_edited=lambda first, last: told.append((first, last)))
    box.pack()
    root.update()
    try:
        inner = box._textbox
        inner.insert("1.0", "one two")
        told.clear()
        inner.get("1.0", "end")
        inner.index("end")
        inner.tag_add("x", "1.0", "1.3")
        inner.mark_set("insert", "1.2")
        assert told == []
    finally:
        box.destroy()

def test_a_box_with_no_listener_still_edits_and_fails_like_any_other(root):
    from gui.components.transcript_input import _EditBox

    box = _EditBox(root)
    box.pack()
    root.update()
    try:
        inner = box._textbox
        inner.insert("1.0", "one two")
        assert inner.get("1.0", "end-1c") == "one two"
        with pytest.raises(tkinter.TclError):
            inner.delete("sel.first", "sel.last")
        run_mainloop(root)
    finally:
        box.destroy()


# ---- a listener that fails cannot take the box down ----

def test_a_listener_that_raises_is_reported_but_the_edit_stands(root):
    from gui.components.transcript_input import _EditBox

    def broken(first, last):
        raise RuntimeError("listener failed")

    seen = []
    previous = root.report_callback_exception
    root.report_callback_exception = lambda exc, val, tb: seen.append(val)
    box = _EditBox(root, on_edited=broken)
    box.pack()
    root.update()
    try:
        box._textbox.insert("1.0", "one two")
        run_mainloop(root)
        assert box._textbox.get("1.0", "end-1c") == "one two"
        assert [str(error) for error in seen] == ["listener failed"]
    finally:
        root.report_callback_exception = previous
        box.destroy()


# ---- taking it down ----

def test_destroying_the_box_leaves_no_forwarder_behind(root, make_box):
    box = make_box("hello world")
    path = str(inner_of(box))
    assert root.tk.call("info", "commands", path)
    assert root.tk.call("info", "commands", path + "_original")
    box.destroy()
    assert not root.tk.call("info", "commands", path)
    assert not root.tk.call("info", "commands", path + "_original")
    run_mainloop(root)

def test_the_command_name_helper_takes_real_names_and_refuses_odd_ones():
    from gui.components.transcript_input import _tcl_word

    assert _tcl_word(".!ctkframe2.!_editbox.!text_original") == ".!ctkframe2.!_editbox.!text_original"
    assert _tcl_word("140574625162432_before_edit") == "140574625162432_before_edit"
    for odd in ("", "has space", "a;b", "a[b]", "a$b", "a{b}", "a\nb"):
        with pytest.raises(ValueError):
            _tcl_word(odd)