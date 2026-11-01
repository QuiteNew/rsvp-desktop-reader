"""Small helpers for the tests of the edit box (gui/components/transcript_input.py),
the box a transcript's text is typed or pasted into.

Each of these used to be copied into the test files that needed it. A test file
imports them by name, the same way as tk_helpers.py (see the note at the top of
that file for why that works):

    from edit_box_helpers import bold_pieces, inner_of, is_on

Most of them reach into the box's inner Tk Text widget, so this is the one place
that has to change if the edit box is ever built differently.
"""


def inner_of(box):
    """The Tk Text widget inside the edit box, where the text and its tags are."""
    return box.textbox._textbox


def bold_pieces(box):
    """The stretches of text the box really shows in bold, read back out of the
    Text widget through the bold tag, in order."""
    from gui.components.transcript_input import BOLD_TAG

    inner = inner_of(box)
    ranges = inner.tag_ranges(BOLD_TAG)
    return [inner.get(str(ranges[i]), str(ranges[i + 1])) for i in range(0, len(ranges), 2)]


def is_on(box):
    """Whether the box shows the bold word starts, told by its text: "hello
    world" comes out with "hel" and "wor" in bold when they are on, and with
    nothing in bold when they are off. It replaces whatever the box held."""
    box.set_text("hello world")
    return bold_pieces(box) == ["hel", "wor"]


def run_mainloop(root, milliseconds=60):
    """Let Tk's real event loop run for a moment, the way the running app does.
    An error that an earlier call left behind is raised from here, which an
    update() would not do."""
    root.after(milliseconds, root.quit)
    root.mainloop()


def clipboard_holds(root, text):
    """Put text on the clipboard, in place of whatever was there."""
    root.clipboard_clear()
    root.clipboard_append(text)