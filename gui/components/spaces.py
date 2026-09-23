import customtkinter as ctk
from gui.theme import WARM_MOCHA, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_HEADING, FONT_BODY


class Spaces(ctk.CTkFrame):
    """Space switcher: 'v' button (left) opens a dialog to pick, rename, or
    delete a space, current name (center, large), '+' (right).

    Doesn't build SpaceSelectionDialog itself -- exactly like Header
    forwards its settings-gear click to gui/app.py's
    _open_settings_window() rather than owning SettingsWindow, the 'v'
    button here just forwards to on_open_spaces, and app.py owns creating
    (and holding a live reference to) the dialog. That reference is what
    lets app.py correctly parent any DeleteSpaceDialog/MessageDialog it
    opens FROM INSIDE that dialog to the dialog itself rather than to this
    (possibly hidden-behind-it) main window -- same reasoning as
    _handle_export_requested()'s docstring in app.py. Since this widget no
    longer builds the dialog, it also no longer needs to track the full
    list of space names -- just the current one, for the label."""

    def __init__(self, master, current_space: str, on_add=None, on_open_spaces=None):
        super().__init__(master, fg_color=WARM_MOCHA, corner_radius=0)
        self.on_add = on_add
        self.on_open_spaces = on_open_spaces
        self._current_space = current_space

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        menu_font = ctk.CTkFont(family=FONT_BODY, size=13, weight="bold")
        self.menu_button = ctk.CTkButton(
            self, text="v", width=32, corner_radius=8,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=menu_font, command=self._handle_open_spaces,
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

    def _handle_add(self) -> None:
        if self.on_add:
            self.on_add()

    def _handle_open_spaces(self) -> None:
        if self.on_open_spaces:
            self.on_open_spaces()