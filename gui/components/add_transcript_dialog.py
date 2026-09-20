import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY, apply_app_icon


class AddTranscriptDialog(ctk.CTkToplevel):
    """Popup for creating a new transcript: asks for a title and a space."""

    def __init__(self, master, spaces: list[str], default_space: str, on_submit):
        super().__init__(master)
        self.title("New Transcript")
        apply_app_icon(self)
        self.geometry("340x240")
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_submit = on_submit

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        entry_font = ctk.CTkFont(family=FONT_BODY, size=13)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        ctk.CTkLabel(self, text="Title", text_color=COCOA_INK, font=label_font).pack(anchor="w", padx=20, pady=(20, 4))
        self.title_entry = ctk.CTkEntry(
            self, placeholder_text="e.g. Lecture 3 notes",
            fg_color=WARM_TAUPE, border_color=WARM_LINE, border_width=1,
            text_color=COCOA_INK, font=entry_font,
        )
        self.title_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Space", text_color=COCOA_INK, font=label_font).pack(anchor="w", padx=20, pady=(16, 4))
        self.space_menu = ctk.CTkOptionMenu(
            self, values=spaces,
            fg_color=WARM_TAUPE, button_color=EMBER_GLOW, button_hover_color=EMBER_GLOW_HOVER,
            dropdown_fg_color=WARM_TAUPE, dropdown_hover_color=WARM_LINE, dropdown_text_color=COCOA_INK,
            text_color=COCOA_INK, font=entry_font,
        )
        self.space_menu.set(default_space)
        self.space_menu.pack(fill="x", padx=20)

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            button_row, text="Cancel", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            button_row, text="Create", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self._handle_create,
        ).pack(side="right")

    def _handle_create(self) -> None:
        title = self.title_entry.get().strip()
        space = self.space_menu.get()
        if not title:
            return
        self.on_submit(title, space)
        self.destroy()