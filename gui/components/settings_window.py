import customtkinter as ctk
from tkinter import colorchooser, filedialog


class SettingsWindow(ctk.CTkToplevel):
    """App-wide settings: new-transcript defaults, layout sizing, and
    where transcript data is stored. Appearance (day/night mode) is a
    placeholder tab, deliberately deferred to a later session."""

    MIN_WINDOW_WIDTH, MAX_WINDOW_WIDTH = 500, 2000
    MIN_WINDOW_HEIGHT, MAX_WINDOW_HEIGHT = 400, 1400
    MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH = 120, 500
    MIN_HEADER_HEIGHT, MAX_HEADER_HEIGHT = 30, 120
    MIN_BOTTOM_BAND_HEIGHT, MAX_BOTTOM_BAND_HEIGHT = 80, 400
    MIN_WPM, MAX_WPM = 100, 1000

    def __init__(
        self, master,
        window_width, window_height,
        sidebar_width, header_height, bottom_band_height,
        default_wpm, default_font_color, default_highlight_color, default_background_color,
        data_directory,
        on_apply,
    ):
        super().__init__(master)
        self.title("Settings")
        self.geometry("480x430")
        self.on_apply = on_apply
        self._data_directory = data_directory

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(15, 5))

        defaults_tab = self.tabview.add("Defaults")
        layout_tab = self.tabview.add("Layout")
        storage_tab = self.tabview.add("Storage")
        appearance_tab = self.tabview.add("Appearance")

        self._build_defaults_tab(defaults_tab, default_wpm, default_font_color, default_highlight_color, default_background_color)
        self._build_layout_tab(layout_tab, window_width, window_height, sidebar_width, header_height, bottom_band_height)
        self._build_storage_tab(storage_tab, data_directory)
        self._build_appearance_tab(appearance_tab)

        self.error_label = ctk.CTkLabel(self, text="", text_color="#E74C3C")
        self.error_label.pack(padx=15, pady=(0, 5), anchor="w")

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(button_row, text="Close", command=self.destroy).pack(side="left")
        ctk.CTkButton(button_row, text="Apply", command=self._handle_apply).pack(side="right")

    def _open_native_dialog(self, dialog_fn, **kwargs):
        """Run any native OS dialog (color picker, folder browser, etc.)
        safely from inside this modally-grabbed window. Native dialogs
        live outside Tk's own window management — if this window's
        grab_set() is still active when the OS dialog closes, Windows can
        lose track of which window should regain focus, freezing the
        entire app. Releasing the grab first, and re-establishing it
        immediately after, avoids that regardless of the outcome."""
        self.grab_release()
        result = dialog_fn(parent=self, **kwargs)
        self.grab_set()
        return result

    # ---- Defaults tab ----

    def _build_defaults_tab(self, tab, wpm, font_color, highlight_color, background_color) -> None:
        ctk.CTkLabel(tab, text="Applied to newly created transcripts only", text_color="gray60").pack(anchor="w", pady=(5, 15))

        wpm_row = ctk.CTkFrame(tab, fg_color="transparent")
        wpm_row.pack(fill="x", pady=6)
        ctk.CTkLabel(wpm_row, text="Speed", width=90, anchor="w").pack(side="left")
        self.default_wpm_label = ctk.CTkLabel(wpm_row, text=f"{wpm} WPM", width=70)
        self.default_wpm_label.pack(side="right")
        self.default_wpm_slider = ctk.CTkSlider(
            tab, from_=self.MIN_WPM, to=self.MAX_WPM, number_of_steps=90,
            command=lambda v: self.default_wpm_label.configure(text=f"{int(v)} WPM"),
        )
        self.default_wpm_slider.set(wpm)
        self.default_wpm_slider.pack(fill="x", pady=(0, 10))

        self.default_font_color = font_color
        self.default_font_swatch = self._color_row(tab, "Font colour", font_color, self._pick_default_font_color)

        self.default_highlight_color = highlight_color
        self.default_highlight_swatch = self._color_row(tab, "Highlight colour", highlight_color, self._pick_default_highlight_color)

        self.default_background_color = background_color
        self.default_background_swatch = self._color_row(tab, "Background colour", background_color, self._pick_default_background_color)

    def _color_row(self, tab, label, color, command) -> ctk.CTkButton:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkLabel(row, text=label, width=90, anchor="w").pack(side="left")
        swatch = ctk.CTkButton(row, text="", width=28, height=28, corner_radius=6, fg_color=color, command=command)
        swatch.pack(side="left")
        return swatch

    def _pick_default_font_color(self) -> None:
        color = self._open_native_dialog(colorchooser.askcolor, color=self.default_font_color)[1]
        if color:
            self.default_font_color = color
            self.default_font_swatch.configure(fg_color=color)

    def _pick_default_highlight_color(self) -> None:
        color = self._open_native_dialog(colorchooser.askcolor, color=self.default_highlight_color)[1]
        if color:
            self.default_highlight_color = color
            self.default_highlight_swatch.configure(fg_color=color)

    def _pick_default_background_color(self) -> None:
        color = self._open_native_dialog(colorchooser.askcolor, color=self.default_background_color)[1]
        if color:
            self.default_background_color = color
            self.default_background_swatch.configure(fg_color=color)

    # ---- Layout tab ----

    def _build_layout_tab(self, tab, window_width, window_height, sidebar_width, header_height, bottom_band_height) -> None:
        self.window_width_entry = self._number_row(tab, "Window width", window_width)
        self.window_height_entry = self._number_row(tab, "Window height", window_height)
        self.sidebar_width_entry = self._number_row(tab, "Sidebar width", sidebar_width)
        self.header_height_entry = self._number_row(tab, "Header height", header_height)
        self.bottom_band_height_entry = self._number_row(tab, "Bottom band height", bottom_band_height)

    def _number_row(self, tab, label, value) -> ctk.CTkEntry:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=label, width=140, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row)
        entry.insert(0, str(value))
        entry.pack(side="left", fill="x", expand=True)
        return entry

    # ---- Storage tab ----

    def _build_storage_tab(self, tab, data_directory) -> None:
        ctk.CTkLabel(tab, text="Transcripts are saved as a JSON file in this folder:", text_color="gray60").pack(anchor="w", pady=(5, 10))
        self.data_directory_label = ctk.CTkLabel(tab, text=data_directory, wraplength=380, justify="left")
        self.data_directory_label.pack(anchor="w", pady=(0, 10))
        ctk.CTkButton(tab, text="Choose folder…", command=self._pick_data_directory).pack(anchor="w")

    def _pick_data_directory(self) -> None:
        chosen = self._open_native_dialog(filedialog.askdirectory, initialdir=self._data_directory)
        if chosen:
            self._data_directory = chosen
            self.data_directory_label.configure(text=chosen)

    # ---- Appearance tab ----

    def _build_appearance_tab(self, tab) -> None:
        ctk.CTkLabel(tab, text="Day / night mode is coming in a later session.", text_color="gray60").pack(pady=20)

    # ---- Apply ----

    def _handle_apply(self) -> None:
        entries = {
            "window_width": (self.window_width_entry, self.MIN_WINDOW_WIDTH, self.MAX_WINDOW_WIDTH),
            "window_height": (self.window_height_entry, self.MIN_WINDOW_HEIGHT, self.MAX_WINDOW_HEIGHT),
            "sidebar_width": (self.sidebar_width_entry, self.MIN_SIDEBAR_WIDTH, self.MAX_SIDEBAR_WIDTH),
            "header_height": (self.header_height_entry, self.MIN_HEADER_HEIGHT, self.MAX_HEADER_HEIGHT),
            "bottom_band_height": (self.bottom_band_height_entry, self.MIN_BOTTOM_BAND_HEIGHT, self.MAX_BOTTOM_BAND_HEIGHT),
        }

        values = {}
        for key, (entry, low, high) in entries.items():
            text = entry.get().strip()
            label = key.replace("_", " ").title()
            if not text.isdigit():
                self.error_label.configure(text=f"{label} must be a whole number.")
                return
            number = int(text)
            if not (low <= number <= high):
                self.error_label.configure(text=f"{label} must be between {low} and {high}.")
                return
            values[key] = number

        values["default_wpm"] = int(self.default_wpm_slider.get())
        values["default_font_color"] = self.default_font_color
        values["default_highlight_color"] = self.default_highlight_color
        values["default_background_color"] = self.default_background_color
        values["data_directory"] = self._data_directory

        self.error_label.configure(text="")
        self.on_apply(values)