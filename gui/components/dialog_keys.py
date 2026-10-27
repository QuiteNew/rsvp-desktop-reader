"""Enter and Esc for the app's small popups.

Each popup says what the two keys do, and leaves out the ones it shouldn't
have. Esc always does what the popup's Cancel or close button does. Enter only
does something where the popup has one safe, obvious answer, like creating a
space from the name just typed. A popup that deletes or replaces something gets
no Enter at all, so a stray key press can never confirm it.

The keys are bound on the popup itself, not on a single widget inside it. Tk
passes a key to the window it happens in after the widget with the focus, so
they work wherever the cursor is in the popup. They never reach the main
window, because every popup is a window of its own, so Esc in a popup doesn't
also stop the reading behind it."""


def bind_dialog_keys(dialog, on_enter=None, on_escape=None) -> None:
    """Make Enter (both Enter keys) run on_enter and Esc run on_escape in this
    popup. Leave either out to give the popup no such key."""
    if on_enter is not None:
        dialog.bind("<Return>", lambda _event: on_enter())
        dialog.bind("<KP_Enter>", lambda _event: on_enter())
    if on_escape is not None:
        dialog.bind("<Escape>", lambda _event: on_escape())


# How long after a popup is revealed the cursor is put in its text box. See
# focus_for_typing() for why it waits at all.
FOCUS_DELAY_MS = 20


def focus_for_typing(entry, select=False) -> None:
    """Put the cursor in a text box, ready to type, a moment from now. With
    select, any text already there is selected, so typing replaces it. The
    popups call this when they are revealed.

    On Windows a new popup hides and shows itself while its title bar is
    coloured, twice, and each time CustomTkinter hands the keyboard back 10 ms
    later to whatever had it just before (see
    customtkinter/windows/ctk_toplevel.py). For a brand new popup that is the
    window behind it. On a busy machine the second hand-back can come after
    the popup is revealed, and it took the cursor back to the main window. It
    is always set going before the reveal runs, so it is always due within
    10 ms of the reveal, and waiting FOCUS_DELAY_MS lets it go first.

    focus_force(), not focus(): it also brings the keyboard back to this
    popup's window."""
    def place() -> None:
        if not entry.winfo_exists():
            return
        entry.focus_force()
        if select:
            entry.select_range(0, "end")
            entry.icursor("end")

    entry.after(FOCUS_DELAY_MS, place)