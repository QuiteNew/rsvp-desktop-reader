import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, DUSK_BLUE, DUSK_BLUE_HOVER, FONT_BODY, apply_app_icon, center_over_parent


class ImportConfirmDialog(ctk.CTkToplevel):
    """Offers a choice of how to bring in an already-parsed import bundle
    (see core/data_bundle.py): Replace, Expand, or Cancel. Shown after
    gui/app.py has successfully parsed the chosen file; this dialog
    doesn't touch the file or the bundle itself, only the user's choice
    of what to do with it.

    Replace and Expand get visually distinct colors on purpose, on top
    of Cancel's usual ember accent: Replace reuses the same red
    DeleteTranscriptDialog uses for its own destructive action, since
    Replace is exactly that: it wipes what's here first. Expand uses
    DUSK_BLUE, a color defined in gui/theme.py's palette but not used
    anywhere else in the app yet, picked deliberately so the two choices
    don't read as "two shades of the same button" when they're two
    genuinely different, non-reversible actions.

    There's no separate on_cancel callback: Cancel is a plain
    self.destroy(), the same as every other dialog's Cancel button (see
    delete_transcript_dialog.py)."""

    def __init__(self, master, on_replace, on_expand):
        super().__init__(master)

        self.attributes("-alpha", 0)

        self.title("Import data")
        apply_app_icon(self)
        center_over_parent(self, 420, 280)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_replace = on_replace
        self.on_expand = on_expand

        message_font = ctk.CTkFont(family=FONT_BODY, size=13)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        ctk.CTkLabel(
            self,
            text=(
                "Replace wipes everything currently on this machine "
                "(transcripts, spaces, and settings) and replaces it with "
                "the imported file.\n\n"
                "Expand adds the imported transcripts and spaces to what's "
                "already here, without touching your current settings.\n\n"
                "Either way, RSVP Reader will close afterward so the change "
                "can take effect. Reopen it when you're ready."
            ),
            text_color=COCOA_INK, font=message_font,
            wraplength=370, justify="left",
        ).pack(padx=20, pady=(20, 15))

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            button_row, text="Cancel", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            button_row, text="Expand", width=90, corner_radius=10,
            fg_color=DUSK_BLUE, hover_color=DUSK_BLUE_HOVER, text_color="#FFFFFF",
            font=button_font, command=self._handle_expand,
        ).pack(side="left", padx=(10, 0))
        ctk.CTkButton(
            button_row, text="Replace", width=90, corner_radius=10,
            fg_color="#A33636", hover_color="#7E2929", text_color="#FFFFFF",
            font=button_font, command=self._handle_replace,
        ).pack(side="right")

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        self.update_idletasks()
        self.attributes("-alpha", 1)

    def _handle_replace(self) -> None:
        self.destroy()
        self.on_replace()

    def _handle_expand(self) -> None:
        self.destroy()
        self.on_expand()