import sys

import customtkinter as ctk
from tkinter import colorchooser, filedialog

from core.settings_store import (
    AppSettings,
    WINDOW_WIDTH_RANGE, WINDOW_HEIGHT_RANGE,
    SIDEBAR_WIDTH_RANGE, BOTTOM_BAND_HEIGHT_RANGE,
    WPM_RANGE, SKIP_WORD_COUNT_RANGE, FONT_SIZE_RANGE, FONT_SIZE_STEP_RANGE,
    HIGHLIGHT_OFFSET_RANGE, GUIDE_MARK_THICKNESS_RANGE, GUIDE_MARK_LENGTH_PERCENT_RANGE,
)
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_HEADING, FONT_BODY, apply_app_icon, center_over_parent


class SettingsWindow(ctk.CTkToplevel):
    """App-wide settings: new-transcript defaults, layout sizing (including
    free-form drag-resize), where transcript data is stored, colour
    theme, and per-transcript reading stats. Header height is a fixed
    constant, not user-configurable; see gui/app.py. Theme changes take
    effect on next launch, not live: every widget's color is set
    explicitly at creation, so a live switch would mean reconfiguring the
    entire widget tree at once."""

    def __init__(
        self, master,
        window_width, window_height,
        sidebar_width, bottom_band_height,
        freeform_resize_enabled,
        default_wpm, default_font_color, default_highlight_color, default_background_color,
        default_font_size, font_size_step, highlight_offset_px,
        skip_word_count, pause_on_skip,
        length_pacing_enabled,
        guide_mark_horizontal_enabled,
        guide_mark_thickness_px,
        guide_mark_length_percent,
        guide_mark_color,
        data_directory,
        appearance_mode,
        transcripts,
        on_apply,
        on_export_requested,
        on_import_requested,
        on_skip_word_count_changed=None,
        on_pause_on_skip_changed=None,
    ):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # very end of __init__). CustomTkinter's own CTkToplevel.__init__,
        # which super().__init__() above just ran, withdraws this window
        # itself for a moment to apply Windows' native dark/light title
        # bar (DWM's DWMWA_USE_IMMERSIVE_DARK_MODE), then schedules its
        # own deiconify() ~5ms later. CTkToplevel.resizable(), called a
        # few lines down, independently triggers that same hide/DWM-set/
        # reveal dance a second time via its own delayed callback (see
        # customtkinter/windows/ctk_toplevel.py), so a plain withdraw()-
        # flag cooperation only covers the first cycle and the window
        # would still visibly flash a second time when resizable() fires.
        # Making the window fully transparent instead sidesteps the whole
        # mechanism: it doesn't touch Tk's own map/withdraw state machine
        # at all, so CustomTkinter's internal hide-and-reshow cycles can
        # run their course invisibly however many times they fire (this
        # also happens again if the appearance mode changes later),
        # without us needing to track their timing.
        self.attributes("-alpha", 0)

        self.title("Settings")
        apply_app_icon(self)
        center_over_parent(self, 500, 650)
        self.minsize(420, 420)
        self.resizable(True, True)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_apply = on_apply
        self.on_export_requested = on_export_requested
        self.on_import_requested = on_import_requested
        self.on_skip_word_count_changed = on_skip_word_count_changed
        self.on_pause_on_skip_changed = on_pause_on_skip_changed
        self._data_directory = data_directory
        self._defaults_scroll = None  # set once the Defaults tab's scrollable frame exists

        self.label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        self.small_font = ctk.CTkFont(family=FONT_BODY, size=11)
        self.button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=1,
            fg_color=HEARTH_PAPER,
            segmented_button_fg_color=WARM_TAUPE,
            segmented_button_selected_color=EMBER_GLOW,
            segmented_button_selected_hover_color=EMBER_GLOW_HOVER,
            segmented_button_unselected_color=WARM_TAUPE,
            segmented_button_unselected_hover_color=WARM_LINE,
            text_color=COCOA_INK,
        )

        self.tabview.pack(fill="both", expand=True, padx=(15, 0), pady=(15, 5))

        defaults_tab = self.tabview.add("Defaults")
        layout_tab = self.tabview.add("Layout")
        storage_tab = self.tabview.add("Storage")
        appearance_tab = self.tabview.add("Appearance")
        stats_tab = self.tabview.add("Stats")

        self._build_defaults_tab(
            defaults_tab, default_wpm, default_font_color, default_highlight_color,
            default_background_color, default_font_size, font_size_step, highlight_offset_px,
            skip_word_count, pause_on_skip, length_pacing_enabled, guide_mark_horizontal_enabled,
            guide_mark_thickness_px, guide_mark_length_percent, guide_mark_color,
        )
        self._build_layout_tab(layout_tab, window_width, window_height, sidebar_width, bottom_band_height, freeform_resize_enabled)
        self._build_storage_tab(storage_tab, data_directory)
        self._build_appearance_tab(appearance_tab, appearance_mode)
        self._build_stats_tab(stats_tab, transcripts)

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

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # Reveal only now, once everything above is built and colored
        # and comfortably after CustomTkinter's own internal Windows
        # titlebar dance has had time to finish (its slowest leg,
        # triggered by resizable() above, can take up to ~15ms to
        # settle; see the alpha note near the top of __init__). 80ms
        # leaves a wide margin while staying well under what's
        # perceptible as a delay. update_idletasks() right before flipping
        # alpha forces any still-queued layout/redraw work (including CTk
        # widgets, and there are a lot of them on this window's tabs, that
        # defer their own first paint via their own internal after() calls)
        # to actually finish first, rather than letting the reveal catch
        # some of that mid-flight and show pieces of the window popping in
        # over a white background instead of one clean paint.
        self.after(80, self._reveal_now)


    def _reveal_now(self) -> None:
        # Every CTk widget redraws itself on a real <Configure> event once
        # its size actually changes (core_widget_classes/ctk_base_class.py,
        # _update_dimensions_event); update_idletasks() doesn't dispatch
        # those, only update() does (same root cause as the
        # CTkScrollableFrame fix on Space Selection).
        #
        # _parent_canvas.bbox("all") is CustomTkinter's own computed
        # bounding box of everything inside the Defaults tab's scrollable
        # area (see ctk_scrollable_frame.py), the deepest, most
        # widget-dense part of this window, and the same private attribute
        # _redirect_scroll_to_defaults_frame() above already reaches into.
        # Looping until it's identical two passes in a row is a genuine
        # "is it finished" signal rather than a guessed pass count,
        # capped so this can never hang if that attribute name ever
        # changes across a CustomTkinter version. This loop itself
        # typically finishes in under 1ms; the visible delay before this
        # window appears is construction time in __init__ above, not this
        # loop.
        last_bbox = None
        for _ in range(30):
            self.update()
            try:
                current_bbox = self._defaults_scroll._parent_canvas.bbox("all")
            except AttributeError:
                break
            if current_bbox == last_bbox:
                break
            last_bbox = current_bbox
        self.attributes("-alpha", 1)


    def _open_native_dialog(self, dialog_fn, **kwargs):
        self.grab_release()
        result = dialog_fn(parent=self, **kwargs)
        self.after(50, self._regrab_if_still_open)
        return result

    def _regrab_if_still_open(self) -> None:
        # Only re-grab if nothing else currently holds the grab. Without
        # this check, this races any dialog Export/Import opens right
        # after the native file dialog closes (the success/failure
        # MessageDialog on export, ImportConfirmDialog on a valid
        # import): that new dialog sets its own grab ~10ms after it's
        # constructed, but this callback was already scheduled 50ms
        # earlier, at the moment the native dialog closed, before the new
        # dialog even existed. Both fire; this one fires second and
        # silently steals the grab back. The new dialog stays visually on
        # top (nothing here affects stacking, a separate concern; see
        # gui/app.py's _settings_window handling) but stops receiving
        # clicks, since Tk only delivers input to whichever window
        # currently holds the grab.
        if self.winfo_exists() and self.grab_current() is None:
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
        mouse wheel scrolls over it. CTkSlider is drawn on a Tkinter
        Canvas internally, and Canvas widgets have a built-in default
        where the wheel adjusts the canvas's own content, unrelated to
        CustomTkinter. This stops that and manually forwards the same
        scroll to the enclosing CTkScrollableFrame instead, so hovering a
        slider scrolls the page, same as hovering anywhere else in this tab.

        Handles both of CustomTkinter's own two wheel-event conventions,
        not just one: CTkSlider binds its own value-changing scroll
        handler to <MouseWheel> on Windows/macOS, but to <Button-4> and
        <Button-5> on Linux instead, since X11 reports the wheel as
        button presses rather than a MouseWheel event at all. event.num
        is used for the Linux buttons; event.delta (Windows/macOS) is
        used otherwise, the same discrimination CustomTkinter's own
        _mouse_scroll_event() uses internally, so this mirrors an
        already-proven-safe pattern rather than inventing a new one.

        Reaches into CTkScrollableFrame's `_parent_canvas`; there's no
        public API for this in the installed CustomTkinter version.
        Wrapped defensively: if that attribute name differs on your exact
        version, scrolling over a slider will simply do nothing rather
        than crash or keep changing the value."""
        try:
            canvas = self._defaults_scroll._parent_canvas
            if event.num == 4:      # Linux scroll up
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:    # Linux scroll down
                canvas.yview_scroll(1, "units")
            else:                    # Windows/macOS <MouseWheel>
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except AttributeError:
            pass
        return "break"

    def _styled_slider(self, master, from_, to, steps, command) -> ctk.CTkSlider:
        slider = ctk.CTkSlider(
            master, from_=from_, to=to, number_of_steps=steps,
            progress_color=EMBER_GLOW, button_color=EMBER_GLOW, button_hover_color=EMBER_GLOW_HOVER,
            fg_color=WARM_LINE, command=command,
        )
        # See _redirect_scroll_to_defaults_frame()'s docstring: which
        # event name to intercept is platform-dependent, matching
        # whichever one the installed CTkSlider itself actually binds.
        if "linux" in sys.platform:
            slider._canvas.unbind("<Button-4>")
            slider._canvas.unbind("<Button-5>")
            slider._canvas.bind("<Button-4>", self._redirect_scroll_to_defaults_frame)
            slider._canvas.bind("<Button-5>", self._redirect_scroll_to_defaults_frame)
        else:
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

    def _build_defaults_tab(self, tab, wpm, font_color, highlight_color, background_color, font_size, font_size_step, highlight_offset_px, skip_word_count, pause_on_skip, length_pacing_enabled, guide_mark_horizontal_enabled, guide_mark_thickness_px, guide_mark_length_percent, guide_mark_color) -> None:
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=(0, 0))

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

        thickness_row = ctk.CTkFrame(scroll, fg_color="transparent")
        thickness_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            thickness_row, text="Thickness of the vertical guide marks, in pixels:",
            text_color=COCOA_INK, font=self.label_font, wraplength=300, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self.guide_mark_thickness_entry = self._styled_entry(thickness_row)
        self.guide_mark_thickness_entry.configure(width=40)
        self.guide_mark_thickness_entry.insert(0, str(guide_mark_thickness_px))
        self.guide_mark_thickness_entry.pack(side="left", padx=(8, 0))

        low, high = GUIDE_MARK_THICKNESS_RANGE
        ctk.CTkLabel(
            scroll, text=f"Applies globally, to every transcript. Allowed range: {low} to {high}.",
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(0, 20))

        length_row = ctk.CTkFrame(scroll, fg_color="transparent")
        length_row.pack(fill="x", pady=6)
        ctk.CTkLabel(length_row, text="Mark length", width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.guide_mark_length_label = ctk.CTkLabel(length_row, text=f"{guide_mark_length_percent}%", width=70, text_color=COCOA_INK, font=self.label_font)
        self.guide_mark_length_label.pack(side="right")
        self.default_guide_mark_length_percent = guide_mark_length_percent
        self.guide_mark_length_slider = self._styled_slider(
            scroll, GUIDE_MARK_LENGTH_PERCENT_RANGE[0], GUIDE_MARK_LENGTH_PERCENT_RANGE[1],
            GUIDE_MARK_LENGTH_PERCENT_RANGE[1] - GUIDE_MARK_LENGTH_PERCENT_RANGE[0],
            lambda v: (self.guide_mark_length_label.configure(text=f"{int(v)}%"), setattr(self, "default_guide_mark_length_percent", int(v))),
        )
        self.guide_mark_length_slider.set(guide_mark_length_percent)
        self.guide_mark_length_slider.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            scroll,
            text="Length of the vertical guide marks, as a percentage of the current word so they keep scaling with the Word Size setting above. Applies globally.",
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(0, 20))

        self.default_guide_mark_color = guide_mark_color
        self.guide_mark_color_swatch = self._color_row(scroll, "Mark colour", guide_mark_color, self._pick_guide_mark_color)
        ctk.CTkLabel(
            scroll,
            text="Colour of the vertical guide marks above and below the highlighted letter. Applies globally, to every transcript.",
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(0, 20))

        self.guide_mark_horizontal_switch = self._styled_switch(scroll, "Show horizontal guide lines")
        (self.guide_mark_horizontal_switch.select() if guide_mark_horizontal_enabled else self.guide_mark_horizontal_switch.deselect())
        self.guide_mark_horizontal_switch.pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(
            scroll,
            text="Adds a fixed grey line above and below the vertical guide marks, sized close to the width of the reading area, to help keep your eyes centered while reading.",
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(0, 20))

        self.length_pacing_switch = self._styled_switch(scroll, "Slow down for long words")
        (self.length_pacing_switch.select() if length_pacing_enabled else self.length_pacing_switch.deselect())
        self.length_pacing_switch.pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(
            scroll,
            text="Gives longer words a bit more time on screen, in three steps based on length (short words are unaffected). If a word is both long and ends a sentence or clause, only the longer of the two pauses applies, since they don't stack. Applies globally, takes effect after clicking Apply.",
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

    def _pick_guide_mark_color(self) -> None:
        color = self._open_native_dialog(colorchooser.askcolor, color=self.default_guide_mark_color)[1]
        if color:
            self.default_guide_mark_color = color
            self.guide_mark_color_swatch.configure(fg_color=color)

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
        self._set_entry_value(self.guide_mark_thickness_entry, original.guide_mark_thickness_px)

        self.default_guide_mark_length_percent = original.guide_mark_length_percent
        self.guide_mark_length_slider.set(original.guide_mark_length_percent)
        self.guide_mark_length_label.configure(text=f"{original.guide_mark_length_percent}%")

        self.default_guide_mark_color = original.guide_mark_color
        self.guide_mark_color_swatch.configure(fg_color=original.guide_mark_color)

        (self.guide_mark_horizontal_switch.select() if original.guide_mark_horizontal_enabled else self.guide_mark_horizontal_switch.deselect())

        (self.length_pacing_switch.select() if original.length_pacing_enabled else self.length_pacing_switch.deselect())

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

        ctk.CTkLabel(
            tab, text="Move your transcripts, spaces, and settings to or from another machine:",
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(20, 10))
        export_import_row = ctk.CTkFrame(tab, fg_color="transparent")
        export_import_row.pack(fill="x", pady=(0, 10))
        self._styled_button(export_import_row, "Export Data…", self._handle_export_data, width=140).pack(side="left")
        self._styled_button(export_import_row, "Import Data…", self._handle_import_data, width=140).pack(side="left", padx=(10, 0))

        self._reset_row(tab, self._handle_reset_storage)

    def _pick_data_directory(self) -> None:
        chosen = self._open_native_dialog(filedialog.askdirectory, initialdir=self._data_directory)
        if chosen:
            self._data_directory = chosen
            self.data_directory_label.configure(text=chosen)

    def _handle_export_data(self) -> None:
        """Collects a destination path via a native save dialog and hands
        it straight to on_export_requested. Unlike "Choose folder…" above,
        which only stages a value the Apply button submits later, Export
        and Import are immediate, one-shot actions with real side effects
        of their own (writing a file; overwriting stored data), so they
        bubble straight up to gui/app.py instead of going through
        _handle_apply()'s values dict."""
        path = self._open_native_dialog(
            filedialog.asksaveasfilename,
            title="Export Data",
            defaultextension=".json",
            filetypes=[("RSVP Reader export", "*.json")],
            initialfile="rsvp-reader-export.json",
        )
        if path:
            self.on_export_requested(path)

    def _handle_import_data(self) -> None:
        path = self._open_native_dialog(
            filedialog.askopenfilename,
            title="Import Data",
            filetypes=[("RSVP Reader export", "*.json")],
        )
        if path:
            self.on_import_requested(path)

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
                "setting, so they won't automatically match Light or Dark. "
                "Adjust them under Defaults, or per-transcript from the "
                "control band at the bottom of the main window, if you'd "
                "like the reading canvas itself to match."
            ),
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(0, 10))

    # ---- Stats tab ----

    def _build_stats_tab(self, tab, transcripts) -> None:
        """Read-only overview of per-transcript reading stats (see
        core/models.py's times_read / total_words_read /
        total_time_spent_seconds, and TranscriptStore.add_session_stats()).
        Deliberately shows every transcript across every space, not just
        the currently selected one: this window has no notion of "the
        current space" anywhere else, so silently filtering here would
        look like missing data rather than a deliberate scope. Sorted by
        time spent, descending, so what's actually been read surfaces
        first and untouched transcripts (all zeros) settle to the bottom.

        The explanatory label at the top exists because these numbers are
        not live: they're only reported to the store when a reading
        session actually ends (gui/components/canvas.py calls
        reader_display.stop(), which reports them, from the Stop button,
        switching transcripts, detaching, or deleting, plus a direct
        finalize_session() call on app close). Pausing only stops the
        active-time clock; it does not report anything, so pausing
        mid-read and opening Settings shows stale numbers, hence spelling
        that out here instead of leaving it to look like a bug."""
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=(0, 0))

        ctk.CTkLabel(
            scroll,
            text=(
                "These totals update once a reading session ends, by "
                "clicking Stop, switching to another transcript, detaching "
                "the window, or closing the app, not while it's simply "
                "paused. If you've been reading and want the latest "
                "numbers, stop or switch away from the transcript first, "
                "then reopen Settings."
            ),
            text_color=COCOA_INK, font=self.small_font, wraplength=420, justify="left",
        ).pack(anchor="w", pady=(5, 15))

        if not transcripts:
            ctk.CTkLabel(
                scroll, text="No transcripts yet.",
                text_color=COCOA_INK, font=self.label_font,
            ).pack(anchor="w", pady=(10, 0))
            return

        ordered = sorted(transcripts, key=lambda t: (-t.total_time_spent_seconds, t.title.lower()))

        for t in ordered:
            row = ctk.CTkFrame(scroll, fg_color=WARM_TAUPE, corner_radius=8)
            row.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(
                row, text=f"{t.title}  ·  {t.space}",
                text_color=COCOA_INK, font=self.label_font,
                anchor="w", wraplength=380, justify="left",
            ).pack(fill="x", padx=12, pady=(10, 2))

            reads_word = "read" if t.times_read == 1 else "reads"
            stats_text = (
                f"{t.times_read} {reads_word}  ·  "
                f"{t.total_words_read:,} words read  ·  "
                f"{self._format_duration(t.total_time_spent_seconds)} total"
            )
            ctk.CTkLabel(
                row, text=stats_text,
                text_color=COCOA_INK, font=self.small_font,
                anchor="w", wraplength=380, justify="left",
            ).pack(fill="x", padx=12, pady=(0, 10))

    @staticmethod
    def _format_duration(total_seconds: int) -> str:
        """Formats a whole number of seconds as a short, human-readable
        duration ("0s", "45s", "12m 34s", or "1h 05m"), switching units
        only once each threshold is crossed, so a short read doesn't show
        a misleading "0h 00m" and a long one doesn't show a wall of
        seconds."""
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes, seconds = divmod(total_seconds, 60)
        if minutes < 60:
            return f"{minutes}m {seconds:02d}s"
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h {minutes:02d}m"

    # ---- Apply ----

    def _handle_apply(self) -> None:
        entries = {
            "window_width": (self.window_width_entry, *WINDOW_WIDTH_RANGE),
            "window_height": (self.window_height_entry, *WINDOW_HEIGHT_RANGE),
            "sidebar_width": (self.sidebar_width_entry, *SIDEBAR_WIDTH_RANGE),
            "bottom_band_height": (self.bottom_band_height_entry, *BOTTOM_BAND_HEIGHT_RANGE),
            "font_size_step": (self.font_size_step_entry, *FONT_SIZE_STEP_RANGE),
            "guide_mark_thickness_px": (self.guide_mark_thickness_entry, *GUIDE_MARK_THICKNESS_RANGE),
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
        values["guide_mark_horizontal_enabled"] = bool(self.guide_mark_horizontal_switch.get())
        values["length_pacing_enabled"] = bool(self.length_pacing_switch.get())
        values["guide_mark_length_percent"] = self.default_guide_mark_length_percent
        values["guide_mark_color"] = self.default_guide_mark_color
        values["data_directory"] = self._data_directory
        values["appearance_mode"] = self.appearance_mode_selector.get().lower()

        self.error_label.configure(text="")
        self.on_apply(values)