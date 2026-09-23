import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY, apply_app_icon, center_over_parent


class DeleteTranscriptDialog(ctk.CTkToplevel):
    """Confirmation popup before permanently deleting a transcript. Names
    the transcript in its message -- same reasoning as DeleteSpaceDialog's
    class docstring: with several transcripts open across spaces, "are you
    sure you want to delete the transcript?" doesn't say WHICH one, which
    matters most right when the user is about to confirm something
    irreversible."""

    def __init__(self, master, transcript_title: str, on_confirm):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # end of __init__, and gui/components/settings_window.py for the
        # fuller explanation of why this uses -alpha rather than
        # withdraw()/deiconify()).
        self.attributes("-alpha", 0)

        self.title("Transcript deletion")
        apply_app_icon(self)
        center_over_parent(self, 360, 170)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_confirm = on_confirm

        message_font = ctk.CTkFont(family=FONT_BODY, size=13)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        ctk.CTkLabel(
            self, text=f"Are you sure you want to permanently delete \"{transcript_title}\"?",
            text_color=COCOA_INK, font=message_font,
            wraplength=320, justify="left",
        ).pack(padx=20, pady=(25, 20))

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            button_row, text="Cancel", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            button_row, text="Delete", width=90, corner_radius=10,
            fg_color="#A33636", hover_color="#7E2929", text_color="#FFFFFF",
            font=button_font, command=self._handle_delete,
        ).pack(side="right")

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

    def _handle_delete(self) -> None:
        self.on_confirm()
        self.destroy()