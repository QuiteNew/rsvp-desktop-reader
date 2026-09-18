import customtkinter as ctk
from tkinter import colorchooser, filedialog

from core.settings_store import (
    AppSettings,
    WINDOW_WIDTH_RANGE, WINDOW_HEIGHT_RANGE,
    SIDEBAR_WIDTH_RANGE, BOTTOM_BAND_HEIGHT_RANGE,
    WPM_RANGE, SKIP_WORD_COUNT_RANGE, FONT_SIZE_RANGE, FONT_SIZE_STEP_RANGE,
    HIGHLIGHT_OFFSET_RANGE,
)
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_HEADING, FONT_BODY


class SettingsWindow(ctk.CTkToplevel):
    """App-wide settings: new-transcript defaults, layout sizing (including
    free-form drag-resize), where transcript data is stored, and colour
    theme. Header height is a fixed constant, not user-configurable —
    see gui/app.py. Theme changes take effect on next launch, not live —
    every widget's color is set explicitly at creation, so a live switch
    would mean reconfiguring the entire widget tree at once."""

    def __init__(
        self, master,
        window_width, window_height,
        sidebar_width, bottom_band_height,
        freeform_resize_enabled,
        default_wpm, default_font_color, default_highlight_color, default_background_color,
        default_font_size, font_size_step, highlight_offset_px,
        skip_word_count, pause_on_skip,
        data_directory,
        appearance_mode,
        on_apply,
        on_skip_word_count_changed=None,
        on_pause_on_skip_changed=None,
    ):
        super().__init__(master)
        self.title("Settings")
        self.geometry("500x650")
        self.minsize(420, 420)
        self.resizable(True, True)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_apply = on_apply
        self.on_skip_word_count_changed = on_skip_word_count_changed
        self.on_pause_on_skip_changed = on_pause_on_skip_changed
        self._data_directory = data_directory
        self._defaults_scroll = None  # set once the Defaults tab's scrollable frame exists

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        self.label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        self.small_font = ctk.CTkFont(family=FONT_BODY, size=11)
        self.button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        self.tabview = ctk.CTkTabview(
            self,
            fg_color=HEARTH_PAPER,
            segmented_button_fg_color=WARM_TAUPE,
            segmented_button_selected_color=EMBER_GLOW,
            segmented_button_selected_hover_color=EMBER_GLOW_HOVER,
            segmented_button_unselected_color=WARM_TAUPE,
            segmented_button_unselected_hover_color=WARM_LINE,
            text_color=COCOA_INK,
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(15, 5))

        defaults_tab = self.tabview.add("Defaults")
        layout_tab = self.tabview.add("Layout")
        storage_tab = self.tabview.add("Storage")
        appearance_tab = self.tabview.add("Appearance")

        self._build_defaults_tab(
            defaults_tab, default_wpm, default_font_color, default_highlight_color,
            default_background_color, default_font_size, font_size_step, highlight_offset_px,
            skip_word_count, pause_on_skip,
        )
        self._build_layout_tab(layout_tab, window_width, window_height, sidebar_width, bottom_band_height, freeform_resize_enabled)
        self._build_storage_tab(storage_tab, data_directory)
        self._build_appearance_tab(appearance_tab, appearance_mode)

        self.error_label = ctk.CTkLabel(self, text="", text_color="#E74C3C", font=self.small_font)
        self.error_label.pack(padx=15, pady=(0, 5), anchor="w")

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(
            button_row, text="Close", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.button_font, command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            button_row, text="Apply", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.button_font, command=self._handle_apply,
        ).pack(side="right")

    def _open_native_dialog(self, dialog_fn, **kwargs):
        self.grab_release()
        result = dialog_fn(parent=self, **kwargs)
        self.after(50, self._regrab_if_still_open)
        return result

    def _regrab_if_still_open(self) -> None:
        if self.winfo_exists():
            self.grab_set()

    def _set_entry_value(self, entry: ctk.CTkEntry, value) -> None:
        entry.delete(0, "end")
        entry.insert(0, str(value))

    def _styled_entry(self, master) -> ctk.CTkEntry:
        return ctk.CTkEntry(
            master, fg_color=WARM_TAUPE, border_color=WARM_LINE, border_width=1,
            text_color=COCOA_INK, font=self.label_font,
        )

    def _redirect_scroll_to_defaults_frame(self, event) -> str:
        """Prevents this slider from changing its own value when the
        mouse wheel scrolls over it — CTkSlider is drawn on a Tkinter
        Canvas internally, and Canvas widgets on Windows have a built-in
        default where the wheel adjusts the canvas's own content, unrelated
        to CustomTkinter. This stops that and manually forwards the same
        scroll to the enclosing CTkScrollableFrame instead, so hovering a
        slider scrolls the page, same as hovering anywhere else in this tab.

        Reaches into CTkScrollableFrame's `_parent_canvas` — there's no
        public API for this in the installed CustomTkinter version. Wrapped
        defensively: if that attribute name differs on your exact version,
        scrolling over a slider will simply do nothing (rather than crash
        or keep changing the value) — worth telling me if that happens, so
        we can find the correct attribute name for your version."""
        try:
            self._defaults_scroll._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except AttributeError:
            pass
        return "break"

    def _styled_slider(self, master, from_, to, steps, command) -> ctk.CTkSlider:
        slider = ctk.CTkSlider(
            master, from_=from_, to=to, number_of_steps=steps,
            progress_color=EMBER_GLOW, button_color=EMBER_GLOW, button_hover_color=EMBER_GLOW_HOVER,
            fg_color=WARM_LINE, command=command,
        )
        slider._canvas.unbind("<MouseWheel>")
        slider._canvas.bind("<MouseWheel>", self._redirect_scroll_to_defaults_frame)
        return slider

    def _styled_switch(self, master, text, command=None) -> ctk.CTkSwitch:
        return ctk.CTkSwitch(
            master, text=text, font=self.label_font, text_color=COCOA_INK,
            progress_color=EMBER_GLOW, fg_color=WARM_LINE,
            button_color=COCOA_INK, button_hover_color=COCOA_INK,
            command=command,
        )

    def _styled_button(self, master, text, command, width=140) -> ctk.CTkButton:
        return ctk.CTkButton(
            master, text=text, width=width, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.button_font, command=command,
        )

    # ---- Defaults tab ----

    def _build_defaults_tab(self, tab, wpm, font_color, highlight_color, background_color, font_size, font_size_step, highlight_offset_px, skip_word_count, pause_on_skip) -> None:
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._defaults_scroll = scroll

        ctk.CTkLabel(scroll, text="Applied to newly created transcripts only", text_color=COCOA_INK, font=self.small_font).pack(anchor="w", pady=(5, 15))

        wpm_row = ctk.CTkFrame(scroll, fg_color="transparent")
        wpm_row.pack(fill="x", pady=6)
        ctk.CTkLabel(wpm_row, text="Speed", width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.default_wpm_label = ctk.CTkLabel(wpm_row, text=f"{wpm} WPM", width=70, text_color=COCOA_INK, font=self.label_font)
        self.default_wpm_label.pack(side="right")
        self.default_wpm_slider = self._styled_slider(
            scroll, WPM_RANGE[0], WPM_RANGE[1], 90,
            lambda v: self.default_wpm_label.configure(text=f"{int(v)} WPM"),
        )
        self.default_wpm_slider.set(wpm)
        self.default_wpm_slider.pack(fill="x", pady=(0, 10))

        self.default_font_color = font_color
        self.default_font_swatch = self._color_row(scroll, "Font colour", font_color, self._pick_default_font_color)

        self.default_highlight_color = highlight_color
        self.default_highlight_swatch = self._color_row(scroll, "Highlight colour", highlight_color, self._pick_default_highlight_color)

        self.default_background_color = background_color
        self.default_background_swatch = self._color_row(scroll, "Background colour", background_color, self._pick_default_background_color)

        self.default_font_size = font_size
        size_row = ctk.CTkFrame(scroll, fg_color="transparent")
        size_row.pack(fill="x", pady=6)
        ctk.CTkLabel(size_row, text="Word size", width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.default_font_size_label = ctk.CTkLabel(size_row, text=f"{font_size} px", width=70, text_color=COCOA_INK, font=self.label_font)
        self.default_font_size_label.pack(side="right")
        self.default_font_size_slider = self._styled_slider(
            scroll, FONT_SIZE_RANGE[0], FONT_SIZE_RANGE[1], FONT_SIZE_RANGE[1] - FONT_SIZE_RANGE[0],
            lambda v: (self.default_font_size_label.configure(text=f"{int(v)} px"), setattr(self, "default_font_size", int(v))),
        )
        self.default_font_size_slider.set(font_size)
        self.default_font_size_slider.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            scroll, text="Changes for the WPM slider take effect after clicking Apply.",
            text_color=COCOA_INK, font=self.small_font,
        ).pack(anchor="w", pady=(0, 20))

        step_row = ctk.CTkFrame(scroll, fg_color="transparent")
        step_row.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(
            step_row, text="Increase the word size by this many pixels each time +/- is clicked:",
            text_color=COCOA_INK, font=self.label_font, wraplength=300, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self.font_size_step_entry = self._styled_entry(step_row)
        self.font_size_step_entry.configure(width=40)
        self.font_size_step_entry.insert(0, str(font_size_step))
        self.font_size_step_entry.pack(side="left", padx=(8, 0))

        offset_row = ctk.CTkFrame(scroll, fg_color="transparent")
        offset_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            offset_row, text="Shift the highlighted letter vertically by this many pixels (positive = up, negative = down):",
            text_color=COCOA_INK, font=self.label_font, wraplength=300, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self.highlight_offset_entry = self._styled_entry(offset_row)
        self.highlight_offset_entry.configure(width=40)
        self.highlight_offset_entry.insert(0, str(highlight_offset_px))
        self.highlight_offset_entry.pack(side="left", padx=(8, 0))

        low, high = HIGHLIGHT_OFFSET_RANGE
        ctk.CTkLabel(
            scroll, text=f"Applies globally, to every transcript. Allowed range: {low} to {high}.",
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(0, 20))

        ctk.CTkLabel(
            scroll, text="Skip controls below apply immediately, to the current transcript and all future ones",
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        skip_row = ctk.CTkFrame(scroll, fg_color="transparent")
        skip_row.pack(fill="x", pady=6)
        ctk.CTkLabel(skip_row, text="Skip amount", width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.skip_word_count_label = ctk.CTkLabel(skip_row, text=f"{skip_word_count} words", width=70, text_color=COCOA_INK, font=self.label_font)
        self.skip_word_count_label.pack(side="right")
        self.skip_word_count_slider = self._styled_slider(
            scroll, SKIP_WORD_COUNT_RANGE[0], SKIP_WORD_COUNT_RANGE[1], SKIP_WORD_COUNT_RANGE[1] - SKIP_WORD_COUNT_RANGE[0],
            self._handle_skip_word_count_slide,
        )
        self.skip_word_count_slider.set(skip_word_count)
        self.skip_word_count_slider.pack(fill="x", pady=(0, 10))

        self.pause_on_skip_switch = self._styled_switch(scroll, "Pause playback when skipping", self._handle_pause_on_skip_toggle)
        (self.pause_on_skip_switch.select() if pause_on_skip else self.pause_on_skip_switch.deselect())
        self.pause_on_skip_switch.pack(anchor="w", pady=(5, 15))

        self._reset_row(scroll, self._handle_reset_defaults)

    def _reset_row(self, tab, command) -> None:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=(20, 0))
        self._styled_button(row, "Reset to Original Defaults", command, width=200).pack(anchor="w")

    def _color_row(self, tab, label, color, command) -> ctk.CTkButton:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkLabel(row, text=label, width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        swatch = ctk.CTkButton(
            row, text="", width=28, height=28, corner_radius=8,
            border_width=2, border_color=WARM_LINE, fg_color=color, command=command,
        )
        swatch.pack(side="left", padx=(12, 0))
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

    def _handle_skip_word_count_slide(self, value) -> None:
        count = int(value)
        self.skip_word_count_label.configure(text=f"{count} words")
        if self.on_skip_word_count_changed:
            self.on_skip_word_count_changed(count)

    def _handle_pause_on_skip_toggle(self) -> None:
        enabled = bool(self.pause_on_skip_switch.get())
        if self.on_pause_on_skip_changed:
            self.on_pause_on_skip_changed(enabled)

    def _handle_reset_defaults(self) -> None:
        original = AppSettings()

        self.default_wpm_slider.set(original.default_wpm)
        self.default_wpm_label.configure(text=f"{original.default_wpm} WPM")

        self.default_font_color = original.default_font_color
        self.default_font_swatch.configure(fg_color=original.default_font_color)

        self.default_highlight_color = original.default_highlight_color
        self.default_highlight_swatch.configure(fg_color=original.default_highlight_color)

        self.default_background_color = original.default_background_color
        self.default_background_swatch.configure(fg_color=original.default_background_color)

        self.default_font_size = original.default_font_size
        self.default_font_size_slider.set(original.default_font_size)
        self.default_font_size_label.configure(text=f"{original.default_font_size} px")

        self._set_entry_value(self.font_size_step_entry, original.font_size_step)
        self._set_entry_value(self.highlight_offset_entry, original.highlight_offset_px)

        self.skip_word_count_slider.set(original.skip_word_count)
        self.skip_word_count_label.configure(text=f"{original.skip_word_count} words")
        if self.on_skip_word_count_changed:
            self.on_skip_word_count_changed(original.skip_word_count)

        (self.pause_on_skip_switch.select() if original.pause_on_skip else self.pause_on_skip_switch.deselect())
        if self.on_pause_on_skip_changed:
            self.on_pause_on_skip_changed(original.pause_on_skip)

    # ---- Layout tab ----

    def _build_layout_tab(self, tab, window_width, window_height, sidebar_width, bottom_band_height, freeform_resize_enabled) -> None:
        self.freeform_switch = self._styled_switch(tab, "Free-form resize (drag borders in the main window)")
        (self.freeform_switch.select() if freeform_resize_enabled else self.freeform_switch.deselect())
        self.freeform_switch.pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(
            tab, text="When on, hover over the sidebar or bottom-band border in the main window and drag it directly.",
            text_color=COCOA_INK, font=self.small_font, wraplength=400, justify="left",
        ).pack(anchor="w", pady=(0, 15))

        self.window_width_entry = self._number_row(tab, "Window width", window_width)
        self.window_height_entry = self._number_row(tab, "Window height", window_height)
        self.sidebar_width_entry = self._number_row(tab, "Sidebar width", sidebar_width)
        self.bottom_band_height_entry = self._number_row(tab, "Bottom band height", bottom_band_height)

        self._reset_row(tab, self._handle_reset_layout)

    def _number_row(self, tab, label, value) -> ctk.CTkEntry:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=label, width=140, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        entry = self._styled_entry(row)
        entry.insert(0, str(value))
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _handle_reset_layout(self) -> None:
        original = AppSettings()

        (self.freeform_switch.select() if original.freeform_resize_enabled else self.freeform_switch.deselect())
        self._set_entry_value(self.window_width_entry, original.window_width)
        self._set_entry_value(self.window_height_entry, original.window_height)
        self._set_entry_value(self.sidebar_width_entry, original.sidebar_width)
        self._set_entry_value(self.bottom_band_height_entry, original.bottom_band_height)

    # ---- Storage tab ----

    def _build_storage_tab(self, tab, data_directory) -> None:
        ctk.CTkLabel(
            tab, text="Transcripts are saved as a JSON file in this folder:",
            text_color=COCOA_INK, font=self.small_font,
        ).pack(anchor="w", pady=(5, 10))
        self.data_directory_label = ctk.CTkLabel(
            tab, text=data_directory, text_color=COCOA_INK, font=self.small_font,
            wraplength=380, justify="left",
        )
        self.data_directory_label.pack(anchor="w", pady=(0, 10))
        self._styled_button(tab, "Choose folder…", self._pick_data_directory, width=140).pack(anchor="w")

        self._reset_row(tab, self._handle_reset_storage)

    def _pick_data_directory(self) -> None:
        chosen = self._open_native_dialog(filedialog.askdirectory, initialdir=self._data_directory)
        if chosen:
            self._data_directory = chosen
            self.data_directory_label.configure(text=chosen)

    def _handle_reset_storage(self) -> None:
        original = AppSettings()
        self._data_directory = original.data_directory
        self.data_directory_label.configure(text=original.data_directory)

    # ---- Appearance tab ----

    def _build_appearance_tab(self, tab, appearance_mode: str) -> None:
        ctk.CTkLabel(
            tab, text="Colour theme", text_color=COCOA_INK, font=self.label_font,
        ).pack(anchor="w", pady=(10, 8))

        self.appearance_mode_selector = ctk.CTkSegmentedButton(
            tab, values=["Light", "Dark", "System"],
            fg_color=WARM_TAUPE, selected_color=EMBER_GLOW, selected_hover_color=EMBER_GLOW_HOVER,
            unselected_color=WARM_TAUPE, unselected_hover_color=WARM_LINE,
            text_color=COCOA_INK, font=self.label_font,
        )
        self.appearance_mode_selector.set(appearance_mode.capitalize())
        self.appearance_mode_selector.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            tab,
            text="Takes effect the next time you launch the app.",
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(
            tab,
            text=(
                "Note: a new transcript's reading colours (font, highlight, "
                "background) come from the Defaults tab, not from this theme "
                "setting — they won't automatically match Light or Dark. "
                "Adjust them under Defaults, or per-transcript from the "
                "control band at the bottom of the main window, if you'd "
                "like the reading canvas itself to match."
            ),
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(0, 10))

    # ---- Apply ----

    def _handle_apply(self) -> None:
        entries = {
            "window_width": (self.window_width_entry, *WINDOW_WIDTH_RANGE),
            "window_height": (self.window_height_entry, *WINDOW_HEIGHT_RANGE),
            "sidebar_width": (self.sidebar_width_entry, *SIDEBAR_WIDTH_RANGE),
            "bottom_band_height": (self.bottom_band_height_entry, *BOTTOM_BAND_HEIGHT_RANGE),
            "font_size_step": (self.font_size_step_entry, *FONT_SIZE_STEP_RANGE),
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

        offset_text = self.highlight_offset_entry.get().strip()
        digits = offset_text[1:] if offset_text.startswith("-") else offset_text
        offset_value = int(offset_text) if digits and digits.isdigit() else None
        low, high = HIGHLIGHT_OFFSET_RANGE
        if offset_value is None:
            self.error_label.configure(text="Highlight Position must be a whole number.")
            return
        if not (low <= offset_value <= high):
            self.error_label.configure(text=f"Highlight Position must be between {low} and {high}.")
            return
        values["highlight_offset_px"] = offset_value

        values["freeform_resize_enabled"] = bool(self.freeform_switch.get())
        values["default_wpm"] = int(self.default_wpm_slider.get())
        values["default_font_color"] = self.default_font_color
        values["default_highlight_color"] = self.default_highlight_color
        values["default_background_color"] = self.default_background_color
        values["default_font_size"] = self.default_font_size
        values["skip_word_count"] = int(self.skip_word_count_slider.get())
        values["pause_on_skip"] = bool(self.pause_on_skip_switch.get())
        values["data_directory"] = self._data_directory
        values["appearance_mode"] = self.appearance_mode_selector.get().lower()

        self.error_label.configure(text="")
        self.on_apply(values)