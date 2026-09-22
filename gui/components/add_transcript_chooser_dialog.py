import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY, apply_app_icon, center_over_parent


class AddTranscriptChooserDialog(ctk.CTkToplevel):
    """Small popup offering the two ways to add a transcript: a blank one,
    or one imported from a file. Replaces the sidebar "+" button's old
    plain tkinter.Menu -- that rendered with the OS's own native menu
    styling, which never picks up HEARTH_PAPER/COCOA_INK/etc, so it
    looked visually disconnected from every other dialog in the app
    (starkly so in Dark mode). This is a CTkToplevel built from the same
    theme constants as AddTranscriptDialog/AddSpaceDialog/
    DeleteTranscriptDialog, so it automatically matches whichever
    appearance mode the app is currently running in, same as they do."""

    def __init__(self, master, on_choose_blank, on_choose_file):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # end of __init__, and gui/components/settings_window.py for the
        # fuller explanation of why this uses -alpha rather than
        # withdraw()/deiconify()).
        self.attributes("-alpha", 0)

        self.title("Add Transcript")
        apply_app_icon(self)
        center_over_parent(self, 300, 220)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_choose_blank = on_choose_blank
        self.on_choose_file = on_choose_file

        label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        ctk.CTkLabel(
            self, text="How would you like to add a transcript?",
            text_color=COCOA_INK, font=label_font,
            wraplength=260, justify="left",
        ).pack(padx=20, pady=(25, 20))

        ctk.CTkButton(
            self, text="Blank transcript", height=36, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self._handle_choose_blank,
        ).pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkButton(
            self, text="Add from file…", height=36, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self._handle_choose_file,
        ).pack(fill="x", padx=20, pady=(0, 20))

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # Reveal now that everything above is built, colored, and
        # comfortably past CustomTkinter's own internal titlebar dance
        # (see the alpha note near the top of __init__). update_idletasks()
        # right before flipping alpha forces any still-queued layout/redraw
        # work (including CTk widgets that defer their own first paint via
        # their own internal after() calls) to actually finish first --
        # otherwise the reveal can catch some of that mid-flight, showing
        # pieces of the window popping in over a white background instead
        # of one clean paint.
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        self.update_idletasks()
        self.attributes("-alpha", 1)

    def _handle_choose_blank(self) -> None:
        # destroy() BEFORE invoking the callback, deliberately the
        # reverse of AddTranscriptDialog/AddSpaceDialog's callback-then-
        # destroy order: this dialog holds its own grab_set() like every
        # other dialog here, and _handle_choose_file's callback opens a
        # native file dialog followed by another CTkToplevel -- if this
        # dialog were still alive (and still holding its grab) when
        # those open, that's the same grab-race class of bug
        # settings_window.py's _open_native_dialog()/
        # _regrab_if_still_open() exist to work around. destroy() first
        # guarantees the grab is fully gone before anything else opens.
        # Applied to both handlers for symmetry, even though the blank
        # path doesn't strictly need it.
        self.destroy()
        self.on_choose_blank()

    def _handle_choose_file(self) -> None:
        self.destroy()
        self.on_choose_file()