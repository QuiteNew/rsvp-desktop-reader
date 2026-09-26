import time

import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, FONT_BODY, apply_app_icon, center_over_parent


class ImportingDialog(ctk.CTkToplevel):
    """A small, button-less "Importing…" placeholder shown for the
    duration of core/importers.py's import_file() call; see
    gui/app.py's _handle_add_from_file_requested(), its only caller.

    Tkinter is single-threaded: nothing on screen repaints, and no
    click or keypress gets handled anywhere in the app, for as long as
    import_file() is running. This dialog can't fix that: there's no
    way to keep something animating mid-call inside one blocking call to
    pypdf/docx without actually moving the work to a separate thread (a
    bigger change, deliberately not this one). What this does fix is
    that right now a slow import gives no acknowledgment at all that the
    click registered, which reads as a hang with no explanation, and on
    Windows, a window that goes long enough without processing its
    message queue gets marked "Not Responding" by the OS. This at least
    names what's happening before the freeze sets in.

    No button and no WM_DELETE_WINDOW override, unlike every other
    dialog in this app: there's nothing sensible to cancel here
    (import_file() isn't interruptible), and any click on its OS close
    button during the freeze wouldn't be processed until the freeze
    ends anyway, by which point finish() below has already torn it down.

    Reveal timing deliberately mirrors every other dialog's alpha=0 ->
    (wait out CustomTkinter's own internal Windows DWM titlebar dance)
    -> alpha=1 pattern (see e.g. AddSpaceDialog), but runs it eagerly
    instead of via self.after(80, ...): every other dialog can afford to
    let that reveal happen whenever the event loop gets around to it,
    because nothing after their construction blocks the event loop. This
    one is built specifically to be on screen before a blocking call, so
    if the reveal were merely scheduled 80ms out instead of forced to
    happen now, that scheduled callback would never actually run until
    after import_file() already returned, defeating the entire point."""

    def __init__(self, master, filename: str):
        super().__init__(master)
        self.attributes("-alpha", 0)

        self.title("Importing")
        apply_app_icon(self)
        center_over_parent(self, 340, 150)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)

        message_font = ctk.CTkFont(family=FONT_BODY, size=13)
        ctk.CTkLabel(
            self,
            text=(
                f"Importing \u201c{filename}\u201d\u2026\n\n"
                "This can take a moment for large files -- the app "
                "won't respond until it's done."
            ),
            text_color=COCOA_INK, font=message_font,
            wraplength=300, justify="left",
        ).pack(expand=True, padx=20, pady=20)

        self.lift()
        self.transient(master)

        # Eagerly wait out the same ~80ms every other dialog defers its
        # own reveal by (see class docstring), pumping the event loop
        # via update() the whole time so CustomTkinter's own internal
        # hide/DWM-set/reveal dance actually gets to run and settle
        # before this forces itself visible, rather than trusting
        # self.after(80, ...) to fire on its own, which needs control to
        # return to the event loop: exactly what the caller is about to
        # prevent for as long as the import takes.
        deadline = time.monotonic() + 0.08
        while time.monotonic() < deadline:
            self.update()
        self.attributes("-alpha", 1)
        self.update()

    def finish(self) -> None:
        self.destroy()