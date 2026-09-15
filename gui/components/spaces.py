import customtkinter as ctk
from gui.components.space_selection_dialog import SpaceSelectionDialog
from gui.theme import WARM_MOCHA, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_HEADING, FONT_BODY


class Spaces(ctk.CTkFrame):
    """Space switcher: 'v' button (left) opens a dialog to pick a space,
    current name (center, large), '+' (right)."""

    def __init__(self, master, spaces: list[str], current_space: str, on_select=None, on_add=None):
        super().__init__(master, fg_color=WARM_MOCHA, corner_radius=0)
        self.on_select = on_select
        self.on_add = on_add
        self._spaces = list(spaces)
        self._current_space = current_space

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        menu_font = ctk.CTkFont(family=FONT_BODY, size=13, weight="bold")
        self.menu_button = ctk.CTkButton(
            self, text="v", width=32, corner_radius=8,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=menu_font, command=self._open_space_dialog,
        )
        self.menu_button.grid(row=0, column=0, sticky="w", padx=10)

        name_font = ctk.CTkFont(family=FONT_HEADING, size=20)
        self.name_label = ctk.CTkLabel(self, text=current_space, font=name_font, text_color=COCOA_INK)
        self.name_label.grid(row=0, column=1)

        add_button = ctk.CTkButton(
            self, text="+", width=32, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            command=self._handle_add,
        )
        add_button.grid(row=0, column=2, sticky="e", padx=10)

    def set_current_space(self, name: str) -> None:
        self._current_space = name
        self.name_label.configure(text=name)

    def update_spaces(self, spaces: list[str]) -> None:
        self._spaces = list(spaces)

    def _open_space_dialog(self) -> None:
        SpaceSelectionDialog(self, spaces=self._spaces, current_space=self._current_space, on_select=self._handle_select)

    def _handle_select(self, selected_name: str) -> None:
        if self.on_select:
            self.on_select(selected_name)

    def _handle_add(self) -> None:
        if self.on_add:
            self.on_add()