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
from gui.theme import HEARTH_PAPER, unregister_fonts
from core.transcript_store import TranscriptStore
from core.settings_store import SettingsStore, SIDEBAR_WIDTH_RANGE, HEADER_HEIGHT_RANGE, BOTTOM_BAND_HEIGHT_RANGE


class RSVPApp(ctk.CTk):
    """Main application window: sidebar | vertical divider | main content,
    across 5 rows (headers / divider / content / divider / bottom band)."""

    DIVIDER_THICKNESS = 2

    def __init__(self):
        super().__init__()
        self.title("RSVP Reader")
        self.configure(fg_color=HEARTH_PAPER)

        self.settings_store = SettingsStore()
        self.store = TranscriptStore(data_directory=self.settings_store.data_directory)
        self._focus_mode = False
        self._current_transcript = None
        self._drag_start_value = None
        self._pending_value = None

        self.geometry(f"{self.settings_store.window_width}x{self.settings_store.window_height}")
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(2, weight=1)
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

        self.top_divider_left = Divider(
            self, orientation="horizontal",
            on_drag_start=self._handle_header_drag_start,
            on_drag=self._handle_header_drag,
            on_drag_end=self._handle_header_drag_end,
        )
        self.top_divider_left.grid(row=1, column=0, sticky="nsew")

        self.top_divider_right = Divider(
            self, orientation="horizontal",
            on_drag_start=self._handle_header_drag_start,
            on_drag=self._handle_header_drag,
            on_drag_end=self._handle_header_drag_end,
        )
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
        )

        self.footer.grid(row=4, column=2, sticky="nsew")

        self._apply_freeform_resize_state()
        self._refresh_transcript_list()

    def _apply_layout_sizes(self) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=self.settings_store.sidebar_width)
        self.grid_columnconfigure(1, weight=0, minsize=self.DIVIDER_THICKNESS)
        self.grid_rowconfigure(0, weight=0, minsize=self.settings_store.header_height)
        self.grid_rowconfigure(1, weight=0, minsize=self.DIVIDER_THICKNESS)
        self.grid_rowconfigure(3, weight=0, minsize=self.DIVIDER_THICKNESS)
        self.grid_rowconfigure(4, weight=0, minsize=self.settings_store.bottom_band_height)

    def _apply_freeform_resize_state(self) -> None:
        enabled = self.settings_store.freeform_resize_enabled
        self.vertical_divider.set_resizable(enabled)
        self.top_divider_left.set_resizable(enabled)
        self.top_divider_right.set_resizable(enabled)
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
        self.settings_store.set_layout_sizes(
            self._pending_value, self.settings_store.header_height, self.settings_store.bottom_band_height
        )

    def _handle_header_drag_start(self) -> None:
        self._drag_start_value = self.settings_store.header_height

    def _handle_header_drag(self, delta: int) -> None:
        low, high = HEADER_HEIGHT_RANGE
        new_height = max(low, min(high, self._drag_start_value + delta))
        self.grid_rowconfigure(0, minsize=new_height)
        self._pending_value = new_height

    def _handle_header_drag_end(self) -> None:
        self.settings_store.set_layout_sizes(
            self.settings_store.sidebar_width, self._pending_value, self.settings_store.bottom_band_height
        )

    def _handle_bottom_band_drag_start(self) -> None:
        self._drag_start_value = self.settings_store.bottom_band_height

    def _handle_bottom_band_drag(self, delta: int) -> None:
        low, high = BOTTOM_BAND_HEIGHT_RANGE
        new_height = max(low, min(high, self._drag_start_value - delta))
        self.grid_rowconfigure(4, minsize=new_height)
        self._pending_value = new_height

    def _handle_bottom_band_drag_end(self) -> None:
        self.settings_store.set_layout_sizes(
            self.settings_store.sidebar_width, self.settings_store.header_height, self._pending_value
        )

    def _open_add_transcript_dialog(self) -> None:
        AddTranscriptDialog(
            self,
            spaces=self.store.spaces,
            default_space=self.store.current_space,
            on_submit=self._handle_new_transcript,
        )

    def _handle_new_transcript(self, title: str, space: str) -> None:
        self.store.add_transcript(
            title, space,
            wpm=self.settings_store.default_wpm,
            font_color=self.settings_store.default_font_color,
            highlight_color=self.settings_store.default_highlight_color,
            background_color=self.settings_store.default_background_color,
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

    def _handle_draft_changed(self, transcript, text: str) -> None:
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
        SettingsWindow(
            self,
            window_width=self.settings_store.window_width,
            window_height=self.settings_store.window_height,
            sidebar_width=self.settings_store.sidebar_width,
            header_height=self.settings_store.header_height,
            bottom_band_height=self.settings_store.bottom_band_height,
            freeform_resize_enabled=self.settings_store.freeform_resize_enabled,
            default_wpm=self.settings_store.default_wpm,
            default_font_color=self.settings_store.default_font_color,
            default_highlight_color=self.settings_store.default_highlight_color,
            default_background_color=self.settings_store.default_background_color,
            data_directory=self.settings_store.data_directory,
            on_apply=self._handle_settings_applied,
        )

    def _handle_settings_applied(self, values: dict) -> None:
        self.settings_store.set_window_size(values["window_width"], values["window_height"])
        self.geometry(f"{values['window_width']}x{values['window_height']}")

        self.settings_store.set_layout_sizes(
            values["sidebar_width"], values["header_height"], values["bottom_band_height"]
        )
        if not self._focus_mode:
            self._apply_layout_sizes()

        self.settings_store.set_freeform_resize_enabled(values["freeform_resize_enabled"])
        self._apply_freeform_resize_state()

        self.settings_store.set_defaults(
            values["default_wpm"], values["default_font_color"],
            values["default_highlight_color"], values["default_background_color"],
        )

        self.settings_store.set_data_directory(values["data_directory"])
        self.store.set_data_directory(values["data_directory"])

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

    def _handle_close(self) -> None:
        self.canvas.save_pending_draft()
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
            self._apply_layout_sizes()

        self.canvas.set_maximized(self._focus_mode)