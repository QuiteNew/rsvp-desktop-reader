"""Tests for the bold word starts following the text as it is edited
(gui/components/transcript_input.py: _EditBox and _handle_edited_lines).

The button, the tag and its font are tested in
test_transcript_input_bold_starts.py. Here the edit box is changed the way a
person changes it (typing, pasting, cutting, deleting, joining and splitting
lines) and after each change the tag is compared with what a full recompute of
the whole text says it should be. A full recompute is the reference because it
is the simple way to get the answer, and the point of the live version is only
to get the same answer without redoing every line.

Typing, pasting and cutting are done through Tk's own procedures for them
(tk::TextInsert, tk_textPaste, tk_textCut), which is what the key bindings call,
so the tests go the same way a real key press goes."""

import random
import tkinter

import customtkinter as ctk
import pytest

from core.bold_spans import tk_spans
from core.bold_starts import bold_ranges


@pytest.fixture(scope="module")
def root():
    try:
        window = ctk.CTk()
    except tkinter.TclError:
        pytest.skip("no display available for Tk")
    window.withdraw()
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
        box.pack()
        root.update()
        made.append(box)
        return box

    yield build
    for box in made:
        box.destroy()


def inner_of(box):
    return box.textbox._textbox


def text_of(box):
    return inner_of(box).get("1.0", "end-1c")


def tagged(box):
    """The bold stretches the widget really has, as (line, start, end)."""
    from gui.components.transcript_input import BOLD_TAG

    ranges = inner_of(box).tag_ranges(BOLD_TAG)
    found = []
    for i in range(0, len(ranges), 2):
        (l1, c1), (l2, c2) = (str(ranges[i]).split("."), str(ranges[i + 1]).split("."))
        assert l1 == l2, "a bold stretch should never run over a line break"
        found.append((int(l1), int(c1), int(c2)))
    return found


def full_recompute(box):
    """What the bold should be, worked out again from the whole text."""
    from gui.components import transcript_input

    return tk_spans(text_of(box), transcript_input._tk_astral_width(box), 1, transcript_input.MAX_BOLD_LINE)


def pieces(box):
    inner = inner_of(box)
    return [inner.get(f"{line}.{a}", f"{line}.{b}") for line, a, b in tagged(box)]


def expected_pieces(text):
    from gui.components import transcript_input

    out = []
    for line in text.split("\n"):
        if len(line) <= transcript_input.MAX_BOLD_LINE:
            out += [line[a:b] for a, b in bold_ranges(line)]
    return out


def edit(root, box, action):
    """Change the text with action(inner Text), then let Tk deliver the event."""
    action(inner_of(box))
    root.update()


def assert_in_step(box):
    assert tagged(box) == full_recompute(box)


# ---- typing ----

def test_typing_a_word_one_letter_at_a_time_keeps_up(root, make_box):
    box = make_box("", bold_starts=True)
    for letter in "interesting reading speed charlie":
        edit(root, box, lambda t, c=letter: t.insert("end-1c", c))
        assert_in_step(box)
    assert pieces(box) == expected_pieces("interesting reading speed charlie")

def test_a_word_that_grows_gets_a_longer_bold_start(root, make_box):
    box = make_box("hell", bold_starts=True)
    assert pieces(box) == ["he"]
    edit(root, box, lambda t: t.insert("end-1c", "o"))
    assert pieces(box) == ["hel"]

def test_typing_in_the_middle_of_a_line_leaves_the_rest_of_it_right(root, make_box):
    box = make_box("one two three four", bold_starts=True)
    edit(root, box, lambda t: t.insert("1.8", "extra "))
    assert text_of(box) == "one two extra three four"
    assert_in_step(box)

def test_typing_a_new_line_at_the_end(root, make_box):
    box = make_box("first line", bold_starts=True)
    edit(root, box, lambda t: t.insert("end-1c", "\nsecond line"))
    assert_in_step(box)
    assert pieces(box) == expected_pieces("first line\nsecond line")

def test_the_text_is_exactly_what_was_typed(root, make_box):
    box = make_box("hello", bold_starts=True)
    edit(root, box, lambda t: t.insert("end-1c", " world"))
    assert text_of(box) == "hello world"

def test_text_inserted_inside_a_bold_start_does_not_inherit_the_bold_by_accident(root, make_box):
    # Tk gives text typed between two tagged characters the tag. The line is
    # bolded again from scratch, so only the algorithm decides what is bold.
    box = make_box("reading", bold_starts=True)
    edit(root, box, lambda t: t.insert("1.2", "XXXXXXXX"))
    assert text_of(box) == "reXXXXXXXXading"
    assert_in_step(box)


# ---- deleting ----

def test_deleting_letters_one_at_a_time_keeps_up(root, make_box):
    box = make_box("interesting reading", bold_starts=True)
    while text_of(box):
        edit(root, box, lambda t: t.delete("end-2c", "end-1c"))
        assert_in_step(box)
    assert tagged(box) == []

def test_deleting_a_whole_line_leaves_the_others_alone(root, make_box):
    box = make_box("alpha beta\ngamma delta\nepsilon zeta", bold_starts=True)
    edit(root, box, lambda t: t.delete("2.0", "3.0"))
    assert text_of(box) == "alpha beta\nepsilon zeta"
    assert_in_step(box)

def test_deleting_a_range_across_lines_joins_them(root, make_box):
    box = make_box("alpha beta\ngamma delta\nepsilon zeta", bold_starts=True)
    edit(root, box, lambda t: t.delete("1.6", "2.3"))
    assert text_of(box) == "alpha ma delta\nepsilon zeta"
    assert_in_step(box)

def test_deleting_everything(root, make_box):
    box = make_box("alpha beta\ngamma delta", bold_starts=True)
    edit(root, box, lambda t: t.delete("1.0", "end"))
    assert text_of(box) == ""
    assert tagged(box) == []


# ---- lines joined, split, pasted ----

def test_a_line_break_in_the_middle_of_a_word_splits_it_into_two_words(root, make_box):
    box = make_box("transcript", bold_starts=True)
    edit(root, box, lambda t: t.insert("1.5", "\n"))
    assert text_of(box) == "trans\ncript"
    assert_in_step(box)

def test_deleting_a_line_break_joins_two_words_into_one(root, make_box):
    box = make_box("trans\ncript\nlast line", bold_starts=True)
    edit(root, box, lambda t: t.delete("1.5", "2.0"))
    assert text_of(box) == "transcript\nlast line"
    assert_in_step(box)

def test_pasting_several_lines_in_the_middle(root, make_box):
    box = make_box("top line\nbottom line", bold_starts=True)
    edit(root, box, lambda t: t.insert("1.3", "AA bb\ncc dddddddd\nee ff\n"))
    assert_in_step(box)
    assert pieces(box) == expected_pieces(text_of(box))

def test_replacing_the_whole_text(root, make_box):
    box = make_box("some old text\nmore of it", bold_starts=True)
    def replace(t):
        t.delete("1.0", "end")
        t.insert("1.0", "brand new words here\nand another line")
    edit(root, box, replace)
    assert_in_step(box)

def test_two_edits_before_the_event_runs_are_both_picked_up(root, make_box):
    box = make_box("one\ntwo\nthree\nfour\nfive", bold_starts=True)
    inner = inner_of(box)
    inner.insert("1.0", "first ")
    inner.insert("5.0", "last ")
    root.update()
    assert_in_step(box)


# ---- the cases a comparison of the text before and after gets wrong ----
#
# Tk keeps a tag with the characters it was put on. When new text pushes old
# text down, a line can read exactly as it did before while its tag has moved
# away with the old characters, and the new line is bare.

def test_a_line_pasted_above_an_identical_line(root, make_box):
    box = make_box("reading speed", bold_starts=True)
    edit(root, box, lambda t: t.insert("1.0", "reading speed\n"))
    assert text_of(box) == "reading speed\nreading speed"
    assert_in_step(box)
    assert len(tagged(box)) == 4

def test_a_line_break_pushing_an_identical_line_down(root, make_box):
    box = make_box("alpha beta\nalpha beta", bold_starts=True)
    edit(root, box, lambda t: t.insert("1.0", "alpha beta\n"))
    assert_in_step(box)

def test_pasting_the_same_text_over_a_selection_with_one_word_changed(root, make_box):
    original = "\n".join(f"line {n} has some words in it" for n in range(30))
    box = make_box(original, bold_starts=True)
    corrected = original.replace("line 17 has", "line 17 had")
    def select_all_and_paste(t):
        t.delete("1.0", "end")
        t.insert("1.0", corrected)
    edit(root, box, select_all_and_paste)
    assert_in_step(box)
    assert len(tagged(box)) == len(full_recompute(box))

def test_pasting_over_two_lines_with_a_text_that_repeats_the_last_one(root, make_box):
    box = make_box("A one\nB two\nC three", bold_starts=True)
    def replace_two_lines(t):
        t.delete("1.0", "2.5")
        t.insert("1.0", "A one\nB two\nB two")
    edit(root, box, replace_two_lines)
    assert text_of(box) == "A one\nB two\nB two\nC three"
    assert_in_step(box)

def test_text_typed_inside_a_bold_start_is_not_bold_by_inheritance(root, make_box):
    # Tk gives text typed between two bold characters the bold tag, and a paste
    # of several lines gets it on every line. The touched lines are bolded again
    # from nothing, so only the algorithm decides.
    box = make_box("reading", bold_starts=True)
    edit(root, box, lambda t: t.insert("1.2", "long words here\nand more words\nand a third"))
    assert_in_step(box)


# ---- typing, pasting and cutting the way Tk's key bindings do them ----

def tk_type(root, box, text):
    inner = inner_of(box)
    inner.tk.call("tk::TextInsert", inner, text)
    root.update()

def test_typing_through_tks_own_procedure_keeps_up(root, make_box):
    box = make_box("", bold_starts=True)
    for letter in "reading speed\ninteresting words":
        tk_type(root, box, letter)
        assert_in_step(box)
    assert text_of(box) == "reading speed\ninteresting words"

def test_a_line_break_typed_in_the_middle_of_a_line(root, make_box):
    box = make_box("reading speed", bold_starts=True)
    inner_of(box).mark_set("insert", "1.4")
    tk_type(root, box, "\n")
    assert text_of(box) == "read\ning speed"
    assert_in_step(box)

def test_typing_over_a_selection_replaces_it(root, make_box):
    box = make_box("alpha beta gamma", bold_starts=True)
    inner = inner_of(box)
    inner.tag_add("sel", "1.6", "1.10")
    inner.mark_set("insert", "1.6")
    tk_type(root, box, "X")
    assert text_of(box) == "alpha X gamma"
    assert_in_step(box)

def test_cutting_a_selection_that_spans_lines(root, make_box):
    box = make_box("alpha beta\ngamma delta\nepsilon zeta", bold_starts=True)
    inner = inner_of(box)
    inner.tag_add("sel", "1.6", "3.3")
    inner.tk.call("tk_textCut", inner)
    root.update()
    assert text_of(box) == "alpha ilon zeta"
    assert_in_step(box)

def test_pasting_several_lines_from_the_clipboard(root, make_box):
    box = make_box("top line\nbottom line", bold_starts=True)
    inner = inner_of(box)
    root.clipboard_clear()
    root.clipboard_append("first pasted\nsecond pasted line\nthird")
    inner.mark_set("insert", "1.4")
    inner.tk.call("tk_textPaste", inner)
    root.update()
    assert text_of(box).startswith("top first pasted\nsecond pasted line\nthird")
    assert_in_step(box)

def test_pasting_over_a_selection_from_the_clipboard(root, make_box):
    box = make_box("alpha beta\ngamma delta", bold_starts=True)
    inner = inner_of(box)
    root.clipboard_clear()
    root.clipboard_append("alpha beta\nalpha beta")
    inner.tag_add("sel", "1.0", "2.0 lineend")
    inner.tk.call("tk_textPaste", inner)
    root.update()
    # Whether the selection is replaced or the text goes in beside it depends on
    # the system (Windows replaces it, X11 does not), so only the bold is checked.
    assert "alpha beta\nalpha beta" in text_of(box)
    assert_in_step(box)


# ---- the forwarder itself ----

@pytest.fixture
def watched(root):
    """A bare _EditBox that records what it is told, destroyed afterwards."""
    from gui.components.transcript_input import _EditBox

    told = []
    box = _EditBox(root, on_edited=lambda first, last: told.append((first, last)))
    box.pack()
    root.update()
    yield box, told
    if box.winfo_exists():
        box.destroy()

def test_an_insert_reports_the_lines_it_covers(watched):
    box, told = watched
    inner = box._textbox
    inner.insert("1.0", "one\ntwo\nthree")
    assert told == [(1, 3)]
    told.clear()
    inner.insert("2.1", "A\nB")
    assert told == [(2, 3)]

def test_an_insert_with_tags_reports_its_lines(watched):
    box, told = watched
    box._textbox.insert("1.0", "one\ntwo", "sometag", "\nmore", "")
    assert told == [(1, 3)]

def test_a_delete_reports_the_line_the_rest_is_joined_on(watched):
    box, told = watched
    inner = box._textbox
    inner.insert("1.0", "one\ntwo\nthree\nfour")
    told.clear()
    inner.delete("1.2", "3.2")
    assert told == [(1, 1)]
    assert inner.get("1.0", "end-1c") == "onree\nfour"

def test_a_delete_of_a_single_character(watched):
    box, told = watched
    inner = box._textbox
    inner.insert("1.0", "one\ntwo")
    told.clear()
    inner.delete("2.1")
    assert told == [(2, 2)]

def test_a_replace_reports_the_lines_of_the_new_text(watched):
    box, told = watched
    inner = box._textbox
    inner.insert("1.0", "one\ntwo\nthree")
    told.clear()
    inner.replace("2.0", "2.3", "A\nB\nC")
    assert told == [(2, 4)]

def test_an_insert_at_end_counts_as_the_last_line(watched):
    box, told = watched
    inner = box._textbox
    inner.insert("1.0", "one\ntwo")
    told.clear()
    inner.insert("end", "X\nY")
    assert told == [(2, 3)]
    assert inner.get("1.0", "end-1c") == "one\ntwoX\nY"

def test_several_ranges_in_one_delete_say_that_anything_may_have_changed(watched):
    box, told = watched
    inner = box._textbox
    inner.insert("1.0", "one\ntwo\nthree")
    told.clear()
    # tkinter's own delete() takes one range, so this is the Tcl command itself.
    inner.tk.call(str(inner), "delete", "1.0", "1.1", "3.0", "3.1")
    assert told == [(None, None)]
    assert inner.get("1.0", "end-1c") == "ne\ntwo\nhree"

def test_undo_and_redo_are_reported_through_the_edits_they_carry_out(root):
    from gui.components.transcript_input import _EditBox

    told = []
    box = _EditBox(root, undo=True, on_edited=lambda first, last: told.append((first, last)))
    box.pack()
    try:
        inner = box._textbox
        inner.insert("1.0", "one\ntwo")
        inner.edit_separator()
        inner.insert("2.0", "new\nlines\n")
        inner.edit_separator()
        told.clear()
        inner.edit_undo()
        assert inner.get("1.0", "end-1c") == "one\ntwo"
        assert told and all(first is not None for first, last in told)
        told.clear()
        inner.edit_redo()
        assert inner.get("1.0", "end-1c") == "one\nnew\nlines\ntwo"
        assert told and all(first is not None for first, last in told)
    finally:
        box.destroy()

def test_when_the_lines_cannot_be_told_the_whole_text_is_bolded_again(root, make_box):
    box = make_box("alpha beta\ngamma delta\nepsilon zeta", bold_starts=True)
    inner = inner_of(box)
    # Several ranges in one delete: the edit box cannot say which lines changed.
    inner.tk.call(str(inner), "delete", "1.0", "1.3", "2.0", "2.3", "3.0", "3.3")
    root.update()
    assert text_of(box) == "ha beta\nma delta\nilon zeta"
    assert_in_step(box)
    assert tagged(box) != []

def test_calls_that_do_not_change_the_text_report_nothing(watched):
    box, told = watched
    inner = box._textbox
    inner.insert("1.0", "one two")
    told.clear()
    inner.get("1.0", "end")
    inner.index("1.2")
    inner.tag_add("t", "1.0", "1.3")
    inner.tag_remove("t", "1.0", "1.3")
    inner.mark_set("insert", "1.1")
    inner.search("two", "1.0")
    inner.count("1.0", "end", "chars")
    inner.edit_modified(False)
    assert told == []

def test_a_bad_index_still_raises_the_same_error_and_reports_nothing(watched):
    box, told = watched
    inner = box._textbox
    inner.insert("1.0", "one")
    told.clear()
    for call in (lambda: inner.insert("bogus", "x"), lambda: inner.delete("bogus"), lambda: inner.get("bogus"),
                 lambda: inner.index("1.0 + zz"), lambda: inner.replace("bogus", "1.1", "x")):
        with pytest.raises(tkinter.TclError):
            call()
    assert told == []
    assert inner.get("1.0", "end-1c") == "one"

def test_what_the_text_widget_returns_comes_back_unchanged(watched):
    box, told = watched
    inner = box._textbox
    inner.insert("1.0", "hello world\nsecond")
    inner.tag_add("t", "1.0", "1.3")
    assert inner.get("1.0", "end-1c") == "hello world\nsecond"
    assert inner.index("end-1c") == "2.6"
    assert [str(i) for i in inner.tag_ranges("t")] == ["1.0", "1.3"]
    assert inner.search("wor", "1.0") == "1.6"
    assert inner.count("1.0", "end", "chars") is not None
    assert inner.edit_modified() in (True, 1)
    assert isinstance(inner.yview(), tuple)

def test_an_edit_box_with_nobody_listening_still_works(root):
    from gui.components.transcript_input import _EditBox

    box = _EditBox(root)
    box.pack()
    try:
        box._textbox.insert("1.0", "one\ntwo")
        box._textbox.delete("1.0", "1.2")
        assert box._textbox.get("1.0", "end-1c") == "e\ntwo"
    finally:
        box.destroy()

def test_destroying_the_edit_box_gives_the_text_widget_its_own_command_back(root):
    from gui.components.transcript_input import _EditBox

    box = _EditBox(root)
    box.pack()
    name = str(box._textbox)
    assert root.tk.call("info", "commands", name + "_original")
    box.destroy()
    assert not root.tk.call("info", "commands", name)
    assert not root.tk.call("info", "commands", name + "_original")

def test_closing_the_window_around_the_edit_box_cleans_up_too(root):
    from gui.components.transcript_input import TranscriptInput

    top = ctk.CTkToplevel(root)
    box = TranscriptInput(top, on_submit=lambda t: None, initial_text="one two", bold_starts=True)
    box.pack()
    top.update()
    name = str(box.textbox._textbox)
    top.destroy()
    root.update()
    assert not root.tk.call("info", "commands", name)
    assert not root.tk.call("info", "commands", name + "_original")

def test_many_boxes_made_and_destroyed_leave_nothing_behind(root):
    from gui.components.transcript_input import TranscriptInput

    before = set(root.tk.splitlist(root.tk.call("info", "commands")))
    for _ in range(15):
        box = TranscriptInput(root, on_submit=lambda t: None, initial_text="one two", bold_starts=True)
        box.pack()
        root.update()
        box.destroy()
    root.update()
    leftover = {c for c in root.tk.splitlist(root.tk.call("info", "commands")) if c not in before and "_original" in c}
    assert leftover == set()


# ---- the bold is not worked out while the text is replaced in one go ----

def test_set_text_works_the_bold_out_once(root, make_box, monkeypatch):
    from gui.components import transcript_input

    box = make_box("some old text", bold_starts=True)
    calls = []
    real = transcript_input.tk_spans
    monkeypatch.setattr(transcript_input, "tk_spans", lambda *a, **k: calls.append(a[0]) or real(*a, **k))
    box.set_text("brand new\ntext here")
    assert calls == ["brand new\ntext here"]

def test_edits_after_set_text_are_live_again(root, make_box):
    box = make_box("some old text", bold_starts=True)
    box.set_text("brand new text")
    edit(root, box, lambda t: t.insert("end-1c", " and more"))
    assert_in_step(box)

def test_building_the_box_works_the_bold_out_once(root, monkeypatch):
    from gui.components import transcript_input
    from gui.components.transcript_input import TranscriptInput

    calls = []
    real = transcript_input.tk_spans
    monkeypatch.setattr(transcript_input, "tk_spans", lambda *a, **k: calls.append(a[0]) or real(*a, **k))
    box = TranscriptInput(root, on_submit=lambda t: None, initial_text="some text\nmore text", bold_starts=True)
    try:
        assert calls == ["some text\nmore text"]
    finally:
        box.destroy()

def test_turning_it_off_stops_the_live_work(root, make_box, monkeypatch):
    from gui.components import transcript_input

    box = make_box("some text", bold_starts=True)
    box.set_bold_starts(False)
    calls = []
    real = transcript_input.tk_spans
    monkeypatch.setattr(transcript_input, "tk_spans", lambda *a, **k: calls.append(1) or real(*a, **k))
    edit(root, box, lambda t: t.insert("1.0", "typed "))
    assert calls == []
    assert tagged(box) == []

def test_undo_in_the_box_brings_the_whole_bold_back_in_step(root):
    from gui.components.transcript_input import TranscriptInput

    # Undo is switched on in the Text underneath; the app itself does not use it.
    box = TranscriptInput(root, on_submit=lambda t: None, initial_text="reading speed", bold_starts=True)
    box.pack()
    try:
        box.textbox._textbox.configure(undo=True)
        inner = box.textbox._textbox
        inner.edit_reset()
        inner.insert("1.0", "interesting ")
        inner.edit_separator()
        root.update()
        inner.edit_undo()
        root.update()
        assert text_of(box) == "reading speed"
        assert_in_step(box)
    finally:
        box.destroy()

# ---- only the changed lines are redone ----

def test_only_the_edited_line_is_worked_out_again(root, make_box, monkeypatch):
    from gui.components import transcript_input

    text = "\n".join(f"line number {n} has some words" for n in range(100))
    box = make_box(text, bold_starts=True)
    seen = []
    real = transcript_input.tk_spans
    def spy(piece, astral_width=1, first_line=1, max_line=None):
        seen.append((piece, first_line))
        return real(piece, astral_width, first_line, max_line)
    monkeypatch.setattr(transcript_input, "tk_spans", spy)
    edit(root, box, lambda t: t.insert("51.0", "NEW "))
    assert seen == [("NEW line number 50 has some words", 51)]
    assert_in_step(box)

def test_lines_that_were_not_touched_keep_their_tag_untouched(root, make_box):
    box = make_box("alpha beta\ngamma delta\nepsilon zeta", bold_starts=True)
    before = tagged(box)
    edit(root, box, lambda t: t.insert("2.0", "x"))
    after = tagged(box)
    assert [s for s in after if s[0] == 1] == [s for s in before if s[0] == 1]
    assert [s for s in after if s[0] == 3] == [s for s in before if s[0] == 3]

def test_an_edit_works_out_only_the_lines_it_touched_when_it_is_a_paste(root, make_box, monkeypatch):
    from gui.components import transcript_input

    text = "\n".join(f"line number {n}" for n in range(50))
    box = make_box(text, bold_starts=True)
    seen = []
    real = transcript_input.tk_spans
    def spy(piece, astral_width=1, first_line=1, max_line=None):
        seen.append((piece, first_line))
        return real(piece, astral_width, first_line, max_line)
    monkeypatch.setattr(transcript_input, "tk_spans", spy)
    edit(root, box, lambda t: t.insert("10.5", "AAA\nBBB\nCCC"))
    # The paste starts in line 10 and ends in line 12, which is now the line
    # holding what was left of line 10. Nothing else is looked at.
    assert seen == [("line AAA\nBBB\nCCCnumber 9", 10)]
    assert_in_step(box)


# ---- off, on, and the other ways the text changes ----

def test_edits_while_off_add_no_bold(root, make_box):
    box = make_box("hello world")
    edit(root, box, lambda t: t.insert("end-1c", " and more words"))
    assert tagged(box) == []

def test_edits_made_while_off_are_picked_up_when_it_is_turned_on(root, make_box):
    box = make_box("hello world")
    edit(root, box, lambda t: t.insert("end-1c", "\nanother line here"))
    box.set_bold_starts(True)
    assert_in_step(box)

def test_edits_after_turning_it_off_and_on_again(root, make_box):
    box = make_box("hello world", bold_starts=True)
    box.set_bold_starts(False)
    edit(root, box, lambda t: t.insert("1.0", "first "))
    assert tagged(box) == []
    box.set_bold_starts(True)
    edit(root, box, lambda t: t.insert("end-1c", " last"))
    assert_in_step(box)

def test_an_edit_right_after_set_text_keeps_up(root, make_box):
    box = make_box("old text on one line\nand a second", bold_starts=True)
    box.set_text("completely different\nwords now\nthree lines")
    edit(root, box, lambda t: t.insert("2.0", "extra "))
    assert_in_step(box)

def test_an_edit_after_normalize_keeps_up(root, make_box):
    box = make_box("Hello,   reading\n\n\n\nwell-known  world", bold_starts=True)
    box.normalize_button.invoke()
    root.update()
    edit(root, box, lambda t: t.insert("1.0", "more "))
    assert_in_step(box)

def test_the_modified_flag_is_clear_after_the_bold_is_redone(root, make_box):
    box = make_box("hello world", bold_starts=True)
    edit(root, box, lambda t: t.insert("end-1c", " again"))
    assert not box.textbox.edit_modified()
    # ... so the next edit is heard too.
    edit(root, box, lambda t: t.insert("end-1c", " and again"))
    assert_in_step(box)

def test_the_normalize_icon_still_follows_the_text(root, make_box):
    box = make_box("hello   world", bold_starts=True)
    box.normalize_button.invoke()
    root.update()
    assert box.normalize_button.cget("image") is box._revert_image
    edit(root, box, lambda t: t.insert("end-1c", " changed"))
    assert box.normalize_button.cget("image") is box._normalize_image

def test_empty_text_then_typing(root, make_box):
    box = make_box("", bold_starts=True)
    edit(root, box, lambda t: t.insert("1.0", "hello world"))
    assert pieces(box) == ["hel", "wor"]


# ---- very long lines ----

def long_line(words):
    return " ".join(["reading"] * words)

def test_a_line_over_the_limit_stays_plain_and_the_others_are_bolded(root, make_box):
    from gui.components import transcript_input

    limit = transcript_input.MAX_BOLD_LINE
    text = "hello world\n" + "x" * (limit + 1) + "\nreading speed"
    box = make_box(text, bold_starts=True)
    assert {line for line, _, _ in tagged(box)} == {1, 3}
    assert text_of(box) == text

def test_a_line_exactly_at_the_limit_is_bolded(root, make_box):
    from gui.components import transcript_input

    limit = transcript_input.MAX_BOLD_LINE
    box = make_box(("word " * limit)[:limit], bold_starts=True)
    assert tagged(box) != []

def test_the_limit_the_widget_uses_is_the_one_in_core(root):
    from core.bold_spans import MAX_BOLD_LINE
    from gui.components import transcript_input

    assert transcript_input.MAX_BOLD_LINE == MAX_BOLD_LINE

def test_turning_it_on_with_a_long_line_says_so(root, make_box, monkeypatch):
    from gui.components import transcript_input

    monkeypatch.setattr(transcript_input, "MAX_BOLD_LINE", 30)
    box = make_box("short line\n" + long_line(10))
    assert box.feedback_label.cget("text") == ""
    box.bold_starts_button.invoke()
    assert box.feedback_label.cget("text") == transcript_input.LONG_LINES_NOTE
    box._clear_feedback()

def test_no_notice_when_every_line_is_short_enough(root, make_box):
    box = make_box("short line\nanother short line", bold_starts=True)
    assert box.feedback_label.cget("text") == ""

def test_no_notice_while_the_look_is_off(root, make_box, monkeypatch):
    from gui.components import transcript_input

    monkeypatch.setattr(transcript_input, "MAX_BOLD_LINE", 30)
    box = make_box(long_line(10))
    edit(root, box, lambda t: t.insert("end-1c", " more"))
    assert box.feedback_label.cget("text") == ""

def test_the_notice_is_the_right_size_for_the_label():
    from gui.components import transcript_input

    assert len(transcript_input.LONG_LINES_NOTE) <= 24

def test_pasting_a_long_line_says_so_and_leaves_it_plain(root, make_box, monkeypatch):
    from gui.components import transcript_input

    monkeypatch.setattr(transcript_input, "MAX_BOLD_LINE", 30)
    box = make_box("short line", bold_starts=True)
    edit(root, box, lambda t: t.insert("end-1c", "\n" + long_line(10)))
    assert box.feedback_label.cget("text") == transcript_input.LONG_LINES_NOTE
    assert {line for line, _, _ in tagged(box)} == {1}
    assert_in_step(box)
    box._clear_feedback()

def test_a_long_line_shortened_below_the_limit_is_bolded_again(root, make_box, monkeypatch):
    from gui.components import transcript_input

    monkeypatch.setattr(transcript_input, "MAX_BOLD_LINE", 30)
    box = make_box(long_line(10), bold_starts=True)
    assert tagged(box) == []
    edit(root, box, lambda t: t.delete("1.20", "1.end"))
    assert len(text_of(box)) <= 30
    assert tagged(box) != []
    assert_in_step(box)
    box._clear_feedback()

def test_a_short_line_made_too_long_by_typing_loses_its_bold(root, make_box, monkeypatch):
    from gui.components import transcript_input

    monkeypatch.setattr(transcript_input, "MAX_BOLD_LINE", 30)
    box = make_box("hello world", bold_starts=True)
    assert tagged(box) != []
    edit(root, box, lambda t: t.insert("end-1c", " and then a great deal more words"))
    assert tagged(box) == []
    box._clear_feedback()

def test_splitting_a_long_line_bolds_both_halves(root, make_box, monkeypatch):
    from gui.components import transcript_input

    monkeypatch.setattr(transcript_input, "MAX_BOLD_LINE", 40)
    box = make_box(long_line(10), bold_starts=True)
    assert tagged(box) == []
    # 79 characters, so 40 and 39 on either side of the new line break.
    edit(root, box, lambda t: t.insert("1.40", "\n"))
    assert [len(line) for line in text_of(box).split("\n")] == [40, 39]
    assert {line for line, _, _ in tagged(box)} == {1, 2}
    assert_in_step(box)
    box._clear_feedback()

@pytest.mark.parametrize("seed", range(4))
def test_random_edits_with_a_small_limit_match_a_full_recompute(root, make_box, monkeypatch, seed):
    from gui.components import transcript_input

    monkeypatch.setattr(transcript_input, "MAX_BOLD_LINE", 25)
    rng = random.Random(100 + seed)
    box = make_box("\n".join(random_chunk(rng) for _ in range(rng.randint(1, 5))), bold_starts=True)
    inner = inner_of(box)
    for step in range(100):
        line, col = random_place(rng, inner)
        if rng.random() < 0.6:
            inner.insert(f"{line}.{col}", random_chunk(rng))
        else:
            line2, col2 = random_place(rng, inner)
            a, b = sorted([(line, col), (line2, col2)])
            inner.delete(f"{a[0]}.{a[1]}", f"{b[0]}.{b[1]}")
        if rng.random() < 0.7 or step == 99:
            root.update()
            assert tagged(box) == full_recompute(box), f"seed {seed} step {step}"
    box._clear_feedback()


# ---- the Normalize icon does not read the whole text for nothing ----

def test_an_edit_does_not_read_the_whole_text_when_nothing_was_normalized(root, make_box, monkeypatch):
    box = make_box("hello world", bold_starts=True)
    reads = []
    real = box.get_text
    monkeypatch.setattr(box, "get_text", lambda: reads.append(1) or real())
    edit(root, box, lambda t: t.insert("end-1c", " more"))
    assert reads == []

def test_after_normalizing_an_edit_does_read_it_and_the_icon_follows(root, make_box):
    box = make_box("hello   world", bold_starts=True)
    box.normalize_button.invoke()
    root.update()
    assert box.normalize_button.cget("image") is box._revert_image
    edit(root, box, lambda t: t.insert("end-1c", " extra"))
    assert box.normalize_button.cget("image") is box._normalize_image


# ---- emoji ----

def test_editing_a_line_with_an_emoji_in_it(root, make_box):
    text = "hello \U0001F600 world \U0001F600\U0001F600 reading"
    box = make_box(text, bold_starts=True)
    edit(root, box, lambda t: t.insert("1.0", "first "))
    assert_in_step(box)
    assert pieces(box) == expected_pieces(text_of(box))
    edit(root, box, lambda t: t.insert("end-1c", " last words"))
    assert_in_step(box)
    assert pieces(box) == expected_pieces(text_of(box))

def test_a_new_line_with_an_emoji_after_ordinary_lines(root, make_box):
    box = make_box("plain line\nanother one", bold_starts=True)
    edit(root, box, lambda t: t.insert("end-1c", "\n\U0001F600 reading \U0001F600 speed"))
    assert pieces(box) == expected_pieces(text_of(box))


# ---- many random edits ----

WORDS = ["a", "of", "the", "hello", "reading", "well-known", "transcript", "interesting",
         "Charlie", "speed", "x", "привет", "κόσμε", "don't", "a1b2"]

def random_chunk(rng):
    pieces_ = []
    for _ in range(rng.randint(1, 4)):
        pieces_.append(rng.choice(WORDS))
        pieces_.append(rng.choice([" ", " ", " ", "\n", "  ", "\n\n", ""]))
    return "".join(pieces_)

def random_place(rng, inner):
    lines = inner.get("1.0", "end-1c").split("\n")
    line = rng.randint(1, len(lines))
    return line, rng.randint(0, len(lines[line - 1]))

@pytest.mark.parametrize("seed", range(8))
def test_many_random_edits_always_match_a_full_recompute(root, make_box, seed):
    rng = random.Random(seed)
    start = "\n".join(random_chunk(rng) for _ in range(rng.randint(0, 6)))
    box = make_box(start, bold_starts=True)
    inner = inner_of(box)
    pending = 0
    for step in range(120):
        kind = rng.choice(["insert", "insert", "delete", "delete", "replace"])
        line, col = random_place(rng, inner)
        if kind == "insert":
            inner.insert(f"{line}.{col}", random_chunk(rng))
        else:
            line2, col2 = random_place(rng, inner)
            a, b = sorted([(line, col), (line2, col2)])
            if kind == "delete":
                inner.delete(f"{a[0]}.{a[1]}", f"{b[0]}.{b[1]}")
            else:
                inner.delete(f"{a[0]}.{a[1]}", f"{b[0]}.{b[1]}")
                inner.insert(f"{a[0]}.{a[1]}", random_chunk(rng))
        pending += 1
        # Sometimes let several edits pile up before the event gets to run.
        if rng.random() < 0.65 or step == 119:
            root.update()
            pending = 0
            assert tagged(box) == full_recompute(box), f"seed {seed} step {step}"
            assert pieces(box) == expected_pieces(text_of(box))
    assert pending == 0

def test_a_big_text_edited_in_the_middle(root, make_box):
    text = "\n".join(f"line {n} with several ordinary words in it" for n in range(1500))
    box = make_box(text, bold_starts=True)
    edit(root, box, lambda t: t.insert("750.5", "inserted words "))
    assert_in_step(box)
    edit(root, box, lambda t: t.delete("100.0", "140.0"))
    assert_in_step(box)