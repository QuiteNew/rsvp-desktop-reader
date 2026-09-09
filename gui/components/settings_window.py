import customtkinter as ctk
from tkinter import colorchooser, filedialog

from core.settings_store import (
    AppSettings,
    WINDOW_WIDTH_RANGE, WINDOW_HEIGHT_RANGE,
    SIDEBAR_WIDTH_RANGE, HEADER_HEIGHT_RANGE, BOTTOM_BAND_HEIGHT_RANGE,
    WPM_RANGE,
)


class SettingsWindow(ctk.CTkToplevel):
    """App-wide settings: new-transcript defaults, layout sizing (including
    free-form drag-resize), and where transcript data is stored. Appearance
    (day/night mode) is a placeholder tab, deliberately deferred."""

    def __init__(
        self, master,
        window_width, window_height,
        sidebar_width, header_height, bottom_band_height,
        freeform_resize_enabled,
        default_wpm, default_font_color, default_highlight_color, default_background_color,
        data_directory,
        on_apply,
    ):
        super().__init__(master)
        self.title("Settings")
        self.geometry("480x480")
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
        self._build_layout_tab(layout_tab, window_width, window_height, sidebar_width, header_height, bottom_band_height, freeform_resize_enabled)
        self._build_storage_tab(storage_tab, data_directory)
        self._build_appearance_tab(appearance_tab)

        self.error_label = ctk.CTkLabel(self, text="", text_color="#E74C3C")
        self.error_label.pack(padx=15, pady=(0, 5), anchor="w")

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(button_row, text="Close", command=self.destroy).pack(side="left")
        ctk.CTkButton(button_row, text="Apply", command=self._handle_apply).pack(side="right")

    def _open_native_dialog(self, dialog_fn, **kwargs):
        """Run any native OS dialog safely from inside this modally-grabbed
        window — release/re-grab avoids the earlier Windows freeze bug."""
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
            tab, from_=WPM_RANGE[0], to=WPM_RANGE[1], number_of_steps=90,
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

        reset_row = ctk.CTkFrame(tab, fg_color="transparent")
        reset_row.pack(fill="x", pady=(20, 0))
        ctk.CTkButton(reset_row, text="Reset to Original Defaults", command=self._handle_reset_defaults).pack(anchor="w")

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

    def _handle_reset_defaults(self) -> None:
        """Reset just this dialog's fields back to the app's original,
        hand-picked defaults — a fresh AppSettings() instance already
        carries those exact values, so nothing is duplicated as separate
        literals. Apply is still required afterward to actually save
        and propagate the reset, same as any other change here."""
        original = AppSettings()

        self.default_wpm_slider.set(original.default_wpm)
        self.default_wpm_label.configure(text=f"{original.default_wpm} WPM")

        self.default_font_color = original.default_font_color
        self.default_font_swatch.configure(fg_color=original.default_font_color)

        self.default_highlight_color = original.default_highlight_color
        self.default_highlight_swatch.configure(fg_color=original.default_highlight_color)

        self.default_background_color = original.default_background_color
        self.default_background_swatch.configure(fg_color=original.default_background_color)

    # ---- Layout tab ----

    def _build_layout_tab(self, tab, window_width, window_height, sidebar_width, header_height, bottom_band_height, freeform_resize_enabled) -> None:
        self.freeform_switch = ctk.CTkSwitch(tab, text="Free-form resize (drag borders in the main window)")
        (self.freeform_switch.select() if freeform_resize_enabled else self.freeform_switch.deselect())
        self.freeform_switch.pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(
            tab, text="When on, hover over any border in the main window and drag it directly.",
            text_color="gray60", wraplength=400, justify="left",
        ).pack(anchor="w", pady=(0, 15))

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
            "window_width": (self.window_width_entry, *WINDOW_WIDTH_RANGE),
            "window_height": (self.window_height_entry, *WINDOW_HEIGHT_RANGE),
            "sidebar_width": (self.sidebar_width_entry, *SIDEBAR_WIDTH_RANGE),
            "header_height": (self.header_height_entry, *HEADER_HEIGHT_RANGE),
            "bottom_band_height": (self.bottom_band_height_entry, *BOTTOM_BAND_HEIGHT_RANGE),
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

        values["freeform_resize_enabled"] = bool(self.freeform_switch.get())
        values["default_wpm"] = int(self.default_wpm_slider.get())
        values["default_font_color"] = self.default_font_color
        values["default_highlight_color"] = self.default_highlight_color
        values["default_background_color"] = self.default_background_color
        values["data_directory"] = self._data_directory

        self.error_label.configure(text="")
        self.on_apply(values)