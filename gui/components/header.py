import customtkinter as ctk
from gui.theme import WARM_TAUPE, COCOA_INK, WARM_LINE, FONT_HEADING, FONT_BODY


class Header(ctk.CTkFrame):
    """Slim top row: active transcript name (left) and a settings button (right)."""

    def __init__(self, master, on_settings=None):
        super().__init__(master, fg_color=WARM_TAUPE, corner_radius=0)
        self.on_settings = on_settings

        title_font = ctk.CTkFont(family=FONT_HEADING, size=16)
        self.title_label = ctk.CTkLabel(self, text="No transcript selected", text_color=COCOA_INK, font=title_font)
        self.title_label.pack(side="left", padx=15)

        button_font = ctk.CTkFont(family=FONT_BODY, size=12)
        ctk.CTkButton(
            self, text="Settings", width=80, corner_radius=10,
            fg_color="transparent", border_width=1, border_color=WARM_LINE,
            text_color=COCOA_INK, hover_color=WARM_LINE, font=button_font,
            command=self._handle_settings,
        ).pack(side="right", padx=15)

    def set_title(self, title: str) -> None:
        self.title_label.configure(text=title)

    def _handle_settings(self) -> None:
        if self.on_settings:
            self.on_settings()