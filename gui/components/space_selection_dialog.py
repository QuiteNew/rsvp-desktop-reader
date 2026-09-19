import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_HEADING, FONT_BODY


class SpaceSelectionDialog(ctk.CTkToplevel):
    """Popup listing every space — the active one shown at full color and
    unclickable, the others shown grey-toned and clickable to switch."""

    def __init__(self, master, spaces: list[str], current_space: str, on_select):
        super().__init__(master)
        self.title("Select Space")
        self.geometry("280x320")
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_select = on_select

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        title_font = ctk.CTkFont(family=FONT_HEADING, size=15)
        ctk.CTkLabel(self, text="Spaces", text_color=COCOA_INK, font=title_font).pack(anchor="w", padx=20, pady=(20, 10))

        list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=(20, 3), pady=(0, 10))

        active_font = ctk.CTkFont(family=FONT_HEADING, size=15)
        inactive_font = ctk.CTkFont(family=FONT_BODY, size=13)

        for space_name in spaces:
            if space_name == current_space:
                # A plain label, not a button — full color, not clickable,
                # and can't pick up any washed-out "disabled" button styling.
                ctk.CTkLabel(
                    list_frame, text=space_name, anchor="w",
                    text_color=COCOA_INK, font=active_font,
                ).pack(fill="x", pady=5, padx=4)
            else:
                ctk.CTkButton(
                    list_frame, text=space_name, anchor="w",
                    fg_color="transparent", hover_color=WARM_TAUPE,
                    text_color=WARM_LINE, font=inactive_font,
                    command=lambda s=space_name: self._handle_select(s),
                ).pack(fill="x", pady=3)

        close_font = ctk.CTkFont(family=FONT_BODY, size=13)
        ctk.CTkButton(
            self, text="Close", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=close_font, command=self.destroy,
        ).pack(pady=(0, 20))

    def _handle_select(self, space_name: str) -> None:
        self.on_select(space_name)
        self.destroy()