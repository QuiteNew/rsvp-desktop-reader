import customtkinter as ctk
from gui.theme import WARM_TAUPE, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_HEADING


class TranscriptListHeader(ctk.CTkFrame):
    """Top of the sidebar: 'List of Transcripts' title and a '+' button."""

    def __init__(self, master, on_add=None):
        super().__init__(master, fg_color=WARM_TAUPE, corner_radius=0)
        self.on_add = on_add

        title_font = ctk.CTkFont(family=FONT_HEADING, size=15)
        ctk.CTkLabel(self, text="List of Transcripts", text_color=COCOA_INK, font=title_font).pack(side="left", padx=12)

        ctk.CTkButton(
            self, text="+", width=28, height=28, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            command=self._handle_add,
        ).pack(side="right", padx=12)

    def _handle_add(self) -> None:
        if self.on_add:
            self.on_add()