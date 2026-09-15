import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY


class DeleteTranscriptDialog(ctk.CTkToplevel):
    """Confirmation popup before permanently deleting a transcript."""

    def __init__(self, master, on_confirm):
        super().__init__(master)
        self.title("Transcript deletion")
        self.geometry("360x170")
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_confirm = on_confirm

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        message_font = ctk.CTkFont(family=FONT_BODY, size=13)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        ctk.CTkLabel(
            self, text="Are you sure you want to permanently delete the transcript?",
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

    def _handle_delete(self) -> None:
        self.on_confirm()
        self.destroy()