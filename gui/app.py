import json
from pathlib import Path

import customtkinter as ctk

from gui.components.transcript_list_header import TranscriptListHeader
from gui.components.transcript_list_body import TranscriptListBody
from gui.components.header import Header
from gui.components.canvas import Canvas
from gui.components.divider import Divider
from gui.components.spaces import Spaces
from gui.components.footer import Footer
from gui.components.add_transcript_dialog import AddTranscriptDialog
from gui.components.add_space_dialog import AddSpaceDialog
from gui.components.settings_window import SettingsWindow
from gui.components.delete_transcript_dialog import DeleteTranscriptDialog
from gui.components.message_dialog import MessageDialog
from gui.components.import_confirm_dialog import ImportConfirmDialog
from gui.theme import (
    HEARTH_PAPER, unregister_fonts, CTK_APPEARANCE_MODE, apply_app_icon,
    DARK_READING_FONT_COLOR, DARK_READING_HIGHLIGHT_COLOR, DARK_READING_BACKGROUND_COLOR,
    LIGHT_READING_GUIDE_MARK_COLOR, DARK_READING_GUIDE_MARK_COLOR,
)
from core.transcript_store import TranscriptStore
from core.settings_store import SettingsStore, SIDEBAR_WIDTH_RANGE, BOTTOM_BAND_HEIGHT_RANGE
from core import data_bundle


class RSVPApp(ctk.CTk):
    """Main application window: sidebar | vertical divider | main content,
    across 5 rows (headers / divider / content / divider / bottom band)."""

    HEADER_HEIGHT = 80  # fixed — not user-configurable

    def __init__(self):
        super().__init__()
        self.title("RSVP Reader")
        apply_app_icon(self)
        self.configure(fg_color=HEARTH_PAPER)

        self.settings_store = SettingsStore()
        self.store = TranscriptStore(data_directory=self.settings_store.data_directory)
        self._resync_theme_default_colors()
        self._focus_mode = False
        self._current_transcript = None
        self._drag_start_value = None
        self._pending_value = None
        self._settings_window = None  # set whenever Settings is open -- see _open_settings_window()

        self.geometry(f"{self.settings_store.window_width}x{self.settings_store.window_height}")
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=0, minsize=self.HEADER_HEIGHT)
        self.grid_rowconfigure(1, weight=0, minsize=Divider.HIT_THICKNESS)
        self.grid_rowconfigure(3, weight=0, minsize=Divider.HIT_THICKNESS)
        self._apply_layout_sizes()

        self.list_header = TranscriptListHeader(self, on_add=self._open_add_transcript_dialog)
        self.list_header.grid(row=0, column=0, sticky="nsew")

        self.header = Header(self, on_settings=self._open_settings_window)
        self.header.grid(row=0, column=2, sticky="nsew")

        self.vertical_divider = Divider(
            self, orientation="vertical",
            on_drag_start=self._handle_sidebar_drag_start,
            on_drag=self._handle_sidebar_drag,
            on_drag_end=self._handle_sidebar_drag_end,
        )
        self.vertical_divider.grid(row=0, column=1, rowspan=5, sticky="nsew")

        self.top_divider_left = Divider(self, orientation="horizontal")
        self.top_divider_left.grid(row=1, column=0, sticky="nsew")

        self.top_divider_right = Divider(self, orientation="horizontal")
        self.top_divider_right.grid(row=1, column=2, sticky="nsew")

        self.list_body = TranscriptListBody(
            self,
            on_select=self._handle_open_transcript,
            on_delete_requested=self._handle_delete_requested,
        )
        self.list_body.grid(row=2, column=0, sticky="nsew")

        self.canvas = Canvas(
            self,
            on_text_submitted=self._handle_text_submitted,
            on_maximize_toggle=self._toggle_focus_mode,
            on_position_changed=self._handle_position_changed,
            on_pause_changed=self._handle_pause_changed,
            on_draft_changed=self._handle_draft_changed,
            on_stopped_changed=self._handle_stopped_changed,
            skip_word_count=self.settings_store.skip_word_count,
            pause_on_skip=self.settings_store.pause_on_skip,
            highlight_offset_px=self.settings_store.highlight_offset_px,
            guide_mark_horizontal_enabled=self.settings_store.guide_mark_horizontal_enabled,
            guide_mark_thickness_px=self.settings_store.guide_mark_thickness_px,
            guide_mark_length_percent=self.settings_store.guide_mark_length_percent,
            guide_mark_color=self.settings_store.guide_mark_color,
        )
        self.canvas.grid(row=2, column=2, sticky="nsew")

        self.bottom_divider_left = Divider(
            self, orientation="horizontal",
            on_drag_start=self._handle_bottom_band_drag_start,
            on_drag=self._handle_bottom_band_drag,
            on_drag_end=self._handle_bottom_band_drag_end,
        )
        self.bottom_divider_left.grid(row=3, column=0, sticky="nsew")

        self.bottom_divider_right = Divider(
            self, orientation="horizontal",
            on_drag_start=self._handle_bottom_band_drag_start,
            on_drag=self._handle_bottom_band_drag,
            on_drag_end=self._handle_bottom_band_drag_end,
        )
        self.bottom_divider_right.grid(row=3, column=2, sticky="nsew")

        self.spaces = Spaces(
            self,
            spaces=self.store.spaces,
            current_space=self.store.current_space,
            on_select=self._handle_space_selected,
            on_add=self._open_add_space_dialog,
        )
        self.spaces.grid(row=4, column=0, sticky="nsew")

        self.footer = Footer(
            self,
            on_wpm_changed=self._handle_wpm_changed,
            on_font_color_changed=self._handle_font_color_changed,
            on_highlight_color_changed=self._handle_highlight_color_changed,
            on_background_color_changed=self._handle_background_color_changed,
            on_skip_back=self.canvas.skip_backward,
            on_skip_forward=self.canvas.skip_forward,
            on_font_size_changed=self._handle_font_size_changed,
            font_size_step=self.settings_store.font_size_step,
        )
        self.footer.grid(row=4, column=2, sticky="nsew")

        self._apply_freeform_resize_state()
        self._refresh_transcript_list()

    def _apply_layout_sizes(self) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=self.settings_store.sidebar_width)
        self.grid_columnconfigure(1, weight=0, minsize=Divider.HIT_THICKNESS)
        self.grid_rowconfigure(4, weight=0, minsize=self.settings_store.bottom_band_height)

    def _apply_freeform_resize_state(self) -> None:
        enabled = self.settings_store.freeform_resize_enabled
        self.vertical_divider.set_resizable(enabled)
        self.bottom_divider_left.set_resizable(enabled)
        self.bottom_divider_right.set_resizable(enabled)

    def _handle_sidebar_drag_start(self) -> None:
        self._drag_start_value = self.settings_store.sidebar_width

    def _handle_sidebar_drag(self, delta: int) -> None:
        low, high = SIDEBAR_WIDTH_RANGE
        new_width = max(low, min(high, self._drag_start_value + delta))
        self.grid_columnconfigure(0, minsize=new_width)
        self._pending_value = new_width

    def _handle_sidebar_drag_end(self) -> None:
        self.settings_store.set_layout_sizes(self._pending_value, self.settings_store.bottom_band_height)

    def _handle_bottom_band_drag_start(self) -> None:
        self._drag_start_value = self.settings_store.bottom_band_height

    def _handle_bottom_band_drag(self, delta: int) -> None:
        low, high = BOTTOM_BAND_HEIGHT_RANGE
        new_height = max(low, min(high, self._drag_start_value - delta))
        self.grid_rowconfigure(4, minsize=new_height)
        self._pending_value = new_height

    def _handle_bottom_band_drag_end(self) -> None:
        self.settings_store.set_layout_sizes(self.settings_store.sidebar_width, self._pending_value)

    def _open_add_transcript_dialog(self) -> None:
        AddTranscriptDialog(
            self,
            spaces=self.store.spaces,
            default_space=self.store.current_space,
            on_submit=self._handle_new_transcript,
        )

    def _current_theme_reading_colors(self) -> tuple[str, str, str]:
        """The (font, highlight, background) reading colors that match the
        CURRENT appearance mode -- the dedicated dark-reading colors in
        Dark mode, the plain Settings -> Defaults values otherwise. Shared
        by both the new-transcript seed and the startup resync (see
        _handle_new_transcript() and _resync_theme_default_colors()) so the
        two can never drift apart. CTK_APPEARANCE_MODE is resolved once at
        app startup (see gui/theme.py), matching how Settings -> Appearance
        already documents itself as "takes effect on next launch, not
        live"."""
        if CTK_APPEARANCE_MODE == "Dark":
            return DARK_READING_FONT_COLOR, DARK_READING_HIGHLIGHT_COLOR, DARK_READING_BACKGROUND_COLOR
        return (
            self.settings_store.default_font_color,
            self.settings_store.default_highlight_color,
            self.settings_store.default_background_color,
        )

    def _resync_theme_default_colors(self) -> None:
        """Run once at startup, right after the stores are constructed and
        before any widget reads a color from them: bring every reading
        color that's still tracking the app-wide theme default -- each
        transcript's font/highlight/background, and the global guide-mark
        color -- in line with the CURRENT appearance mode. Anything that
        was manually picked by hand is left untouched; see
        TranscriptStore.resync_default_reading_colors() and
        SettingsStore.resync_guide_mark_color_default() for exactly how
        that distinction is tracked."""
        font_color, highlight_color, background_color = self._current_theme_reading_colors()
        self.store.resync_default_reading_colors(font_color, highlight_color, background_color)

        guide_mark_color = DARK_READING_GUIDE_MARK_COLOR if CTK_APPEARANCE_MODE == "Dark" else LIGHT_READING_GUIDE_MARK_COLOR
        self.settings_store.resync_guide_mark_color_default(guide_mark_color)

    def _handle_new_transcript(self, title: str, space: str) -> None:
        # A brand-new transcript's reading colors are seeded from whichever
        # set matches the current theme -- see _current_theme_reading_colors().
        # This only affects transcripts created from this point on; anything
        # that already exists is handled separately, once, at startup (see
        # _resync_theme_default_colors()).
        font_color, highlight_color, background_color = self._current_theme_reading_colors()

        self.store.add_transcript(
            title, space,
            wpm=self.settings_store.default_wpm,
            font_color=font_color,
            highlight_color=highlight_color,
            background_color=background_color,
            font_size=self.settings_store.default_font_size,
        )
        self._refresh_transcript_list()

    def _open_add_space_dialog(self) -> None:
        AddSpaceDialog(self, on_submit=self._handle_new_space)

    def _handle_new_space(self, name: str) -> None:
        current = self.store.add_space(name)
        self.spaces.update_spaces(self.store.spaces)
        self.spaces.set_current_space(current)
        self._refresh_transcript_list()

    def _handle_space_selected(self, name: str) -> None:
        current = self.store.switch_to_space(name)
        self.spaces.set_current_space(current)
        self._refresh_transcript_list()

    def _handle_open_transcript(self, transcript) -> None:
        self._current_transcript = transcript
        self.header.set_title(transcript.title)
        self.canvas.load_transcript(transcript)
        self.footer.load_transcript(transcript)

    def _handle_text_submitted(self, transcript, raw_text: str) -> None:
        self.store.set_transcript_text(transcript.id, raw_text)
        self.canvas.load_transcript(transcript)

    def _handle_position_changed(self, transcript, index: int) -> None:
        self.store.set_transcript_position(transcript.id, index)

    def _handle_pause_changed(self, transcript, is_paused: bool) -> None:
        self.store.set_transcript_paused(transcript.id, is_paused)

    def _handle_stopped_changed(self, transcript, is_stopped: bool) -> None:
        self.store.set_transcript_stopped(transcript.id, is_stopped)

    def _handle_draft_changed(self, transcript, text: str) -> None:
        if transcript.is_stopped:
            self.store.set_transcript_text(transcript.id, text)
        else:
            self.store.set_transcript_draft_text(transcript.id, text)

    def _handle_wpm_changed(self, wpm: int) -> None:
        if not self._current_transcript:
            return
        self.store.set_transcript_wpm(self._current_transcript.id, wpm)
        self.canvas.set_wpm(wpm)

    def _handle_font_color_changed(self, color: str) -> None:
        if not self._current_transcript:
            return
        self.store.set_transcript_font_color(self._current_transcript.id, color)
        self._apply_current_colors()

    def _handle_font_size_changed(self, size: int) -> None:
        if not self._current_transcript:
            return
        self.store.set_transcript_font_size(self._current_transcript.id, size)
        self.canvas.set_font_size(size)

    def _handle_highlight_color_changed(self, color: str) -> None:
        if not self._current_transcript:
            return
        self.store.set_transcript_highlight_color(self._current_transcript.id, color)
        self._apply_current_colors()

    def _handle_background_color_changed(self, color: str) -> None:
        if not self._current_transcript:
            return
        self.store.set_transcript_background_color(self._current_transcript.id, color)
        self._apply_current_colors()

    def _apply_current_colors(self) -> None:
        t = self._current_transcript
        self.canvas.set_colors(t.font_color, t.highlight_color, t.background_color)

    def _refresh_transcript_list(self) -> None:
        self.list_body.render_transcripts(self.store.transcripts_in_current_space)

    def _open_settings_window(self) -> None:
        # Stored on self, not just constructed inline, because the
        # Export/Import handlers below need a live reference to it: any
        # dialog THEY open (an error, the Replace/Expand/Cancel choice)
        # has to be parented to THIS window, not to the main app window,
        # or Windows has no ordering guarantee between the new dialog and
        # Settings, and the new one can end up drawn behind it -- see the
        # docstrings on _handle_export_requested() and
        # _handle_import_requested() below.
        self._settings_window = SettingsWindow(
            self,
            window_width=self.settings_store.window_width,
            window_height=self.settings_store.window_height,
            sidebar_width=self.settings_store.sidebar_width,
            bottom_band_height=self.settings_store.bottom_band_height,
            freeform_resize_enabled=self.settings_store.freeform_resize_enabled,
            default_wpm=self.settings_store.default_wpm,
            default_font_color=self.settings_store.default_font_color,
            default_highlight_color=self.settings_store.default_highlight_color,
            default_background_color=self.settings_store.default_background_color,
            default_font_size=(
                self._current_transcript.font_size if self._current_transcript
                else self.settings_store.default_font_size
            ),
            font_size_step=self.settings_store.font_size_step,
            highlight_offset_px=self.settings_store.highlight_offset_px,
            skip_word_count=self.settings_store.skip_word_count,
            pause_on_skip=self.settings_store.pause_on_skip,
            guide_mark_horizontal_enabled=self.settings_store.guide_mark_horizontal_enabled,
            guide_mark_thickness_px=self.settings_store.guide_mark_thickness_px,
            guide_mark_length_percent=self.settings_store.guide_mark_length_percent,
            guide_mark_color=self.settings_store.guide_mark_color,
            data_directory=self.settings_store.data_directory,
            on_apply=self._handle_settings_applied,
            on_export_requested=self._handle_export_requested,
            on_import_requested=self._handle_import_requested,
            on_skip_word_count_changed=self._handle_skip_word_count_live,
            on_pause_on_skip_changed=self._handle_pause_on_skip_live,
            appearance_mode=self.settings_store.appearance_mode,
        )

    def _handle_settings_applied(self, values: dict) -> None:
        self.settings_store.set_window_size(values["window_width"], values["window_height"])
        self.geometry(f"{values['window_width']}x{values['window_height']}")

        self.settings_store.set_layout_sizes(
            values["sidebar_width"], values["bottom_band_height"]
        )
        if not self._focus_mode:
            self._apply_layout_sizes()

        self.settings_store.set_freeform_resize_enabled(values["freeform_resize_enabled"])
        self._apply_freeform_resize_state()

        self.settings_store.set_defaults(
            values["default_wpm"], values["default_font_color"],
            values["default_highlight_color"], values["default_background_color"],
            values["default_font_size"],
        )

        if self._current_transcript:
            self.store.set_transcript_font_size(self._current_transcript.id, values["default_font_size"])
            self.canvas.set_font_size(values["default_font_size"])
            self.footer.set_font_size(values["default_font_size"])

        self.settings_store.set_font_size_step(values["font_size_step"])
        self.footer.set_font_size_step(values["font_size_step"])

        self.settings_store.set_highlight_offset_px(values["highlight_offset_px"])
        self.canvas.set_highlight_offset(values["highlight_offset_px"])

        self.settings_store.set_guide_mark_horizontal_enabled(values["guide_mark_horizontal_enabled"])
        self.canvas.set_guide_mark_horizontal_enabled(values["guide_mark_horizontal_enabled"])

        self.settings_store.set_guide_mark_thickness_px(values["guide_mark_thickness_px"])
        self.canvas.set_guide_mark_thickness(values["guide_mark_thickness_px"])

        self.settings_store.set_guide_mark_length_percent(values["guide_mark_length_percent"])
        self.canvas.set_guide_mark_length_percent(values["guide_mark_length_percent"])

        self.settings_store.set_guide_mark_color(values["guide_mark_color"])
        self.canvas.set_guide_mark_color(values["guide_mark_color"])

        self.settings_store.set_data_directory(values["data_directory"])
        self.store.set_data_directory(values["data_directory"])
        self.settings_store.set_skip_behavior(values["skip_word_count"], values["pause_on_skip"])
        self.canvas.set_skip_word_count(values["skip_word_count"])
        self.canvas.set_pause_on_skip(values["pause_on_skip"])

        self.settings_store.set_appearance_mode(values["appearance_mode"])

    def _handle_export_requested(self, path: str) -> None:
        """Builds a bundle from the two stores' CURRENT in-memory state
        (see core/data_bundle.py) and writes it to the path the user
        picked in the Storage tab's save dialog. File I/O deliberately
        lives here, not in core/data_bundle.py -- build_bundle() itself
        stays pure/path-free so it's testable on its own.

        Any dialog shown here is parented to self._settings_window, not
        self -- this was triggered from inside Settings, which is the
        window actually on screen, so a dialog parented to the (possibly
        hidden-behind-Settings) main window instead has no guaranteed
        stacking order above it."""
        bundle = data_bundle.build_bundle(self.store, self.settings_store)
        try:
            Path(path).write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        except OSError as e:
            MessageDialog(self._settings_window, "Export failed", f"Couldn't write the export file:\n\n{e}")
            return
        MessageDialog(self._settings_window, "Export complete", f"Your data was exported to:\n\n{path}")

    def _handle_import_requested(self, path: str) -> None:
        """Reads and validates the chosen file, then -- only if it's a
        genuinely valid bundle -- hands the user a Replace/Expand/Cancel
        choice. Nothing is applied yet at this point; see
        _apply_import(). See _handle_export_requested()'s docstring for
        why every dialog here is parented to self._settings_window."""
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            MessageDialog(self._settings_window, "Import failed", f"Couldn't read that file:\n\n{e}")
            return

        try:
            bundle = data_bundle.parse_bundle(text)
        except data_bundle.BundleFormatError as e:
            MessageDialog(self._settings_window, "Import failed", str(e))
            return

        ImportConfirmDialog(
            self._settings_window,
            on_replace=lambda: self._apply_import(bundle, expand=False),
            on_expand=lambda: self._apply_import(bundle, expand=True),
        )

    def _apply_import(self, bundle: dict, expand: bool) -> None:
        """Actually applies an already-confirmed import, then closes the
        app -- see core/data_bundle.py's module docstring and
        gui/components/message_dialog.py's class docstring for why a
        restart isn't optional here: this app has no live-reload path
        for a wholesale change to transcripts/spaces/settings, so
        continuing to run on stale in-memory state risks both a
        confusing UI and, worse, that stale state getting autosaved
        straight back over the data this import just wrote."""
        if expand:
            data_bundle.apply_bundle_expand(bundle, self.store)
        else:
            data_bundle.apply_bundle_replace(bundle, self.store, self.settings_store)

        MessageDialog(
            self._settings_window, "Import complete",
            "Your data was imported. RSVP Reader will now close -- reopen it to see the change.",
            on_close=self._handle_close,
        )

    def _handle_delete_requested(self, transcript) -> None:
        DeleteTranscriptDialog(self, on_confirm=lambda: self._handle_delete_confirmed(transcript))

    def _handle_delete_confirmed(self, transcript) -> None:
        was_current = self._current_transcript is not None and self._current_transcript.id == transcript.id

        self.canvas.handle_transcript_deleted(transcript.id)
        self.store.delete_transcript(transcript.id)
        self._refresh_transcript_list()

        if was_current:
            self._current_transcript = None
            self.header.set_title("No transcript selected")
            self.footer.set_enabled(False)

    def _handle_skip_word_count_live(self, count: int) -> None:
        self.settings_store.set_skip_word_count_live(count)
        self.canvas.set_skip_word_count(count)

    def _handle_pause_on_skip_live(self, enabled: bool) -> None:
        self.settings_store.set_skip_behavior(self.settings_store.skip_word_count, enabled)
        self.canvas.set_pause_on_skip(enabled)

    def _handle_close(self) -> None:
        self.canvas.save_pending_draft()
        # Position/WPM and skip-amount writes are throttled while their
        # sliders are actively being used (see core/transcript_store.py and
        # core/settings_store.py) -- this guarantees whatever was last
        # reached in memory is actually on disk before we quit, even if it
        # hasn't hit the throttle interval yet.
        self.store.flush()
        self.settings_store.flush()
        unregister_fonts()
        self.destroy()

    def _toggle_focus_mode(self) -> None:
        self._focus_mode = not self._focus_mode

        if self._focus_mode:
            self.list_header.grid_remove()
            self.list_body.grid_remove()
            self.header.grid_remove()
            self.vertical_divider.grid_remove()
            self.top_divider_left.grid_remove()
            self.top_divider_right.grid_remove()
            self.bottom_divider_left.grid_remove()
            self.bottom_divider_right.grid_remove()
            self.spaces.grid_remove()
            self.footer.grid_remove()
            self.grid_columnconfigure(0, minsize=0)
            self.grid_columnconfigure(1, minsize=0)
            self.grid_rowconfigure(0, minsize=0)
            self.grid_rowconfigure(1, minsize=0)
            self.grid_rowconfigure(3, minsize=0)
            self.grid_rowconfigure(4, minsize=0)
        else:
            self.list_header.grid()
            self.list_body.grid()
            self.header.grid()
            self.vertical_divider.grid()
            self.top_divider_left.grid()
            self.top_divider_right.grid()
            self.bottom_divider_left.grid()
            self.bottom_divider_right.grid()
            self.spaces.grid()
            self.footer.grid()
            self.grid_rowconfigure(0, minsize=self.HEADER_HEIGHT)
            self.grid_rowconfigure(1, minsize=Divider.HIT_THICKNESS)
            self.grid_rowconfigure(3, minsize=Divider.HIT_THICKNESS)
            self._apply_layout_sizes()