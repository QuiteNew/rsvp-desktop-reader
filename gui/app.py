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
from core.transcript_store import TranscriptStore
from core.settings_store import SettingsStore


class RSVPApp(ctk.CTk):
    """Main application window, laid out as a single 2-column, 5-row grid."""

    DIVIDER_HEIGHT = 2  # fixed — not user-adjustable, unlike the other regions

    def __init__(self):
        super().__init__()
        self.title("RSVP Reader")

        self.settings_store = SettingsStore()
        self.store = TranscriptStore(data_directory=self.settings_store.data_directory)
        self._focus_mode = False
        self._current_transcript = None

        self.geometry(f"{self.settings_store.window_width}x{self.settings_store.window_height}")
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=0, minsize=self.DIVIDER_HEIGHT)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0, minsize=self.DIVIDER_HEIGHT)
        self._apply_layout_sizes()

        self.list_header = TranscriptListHeader(self, on_add=self._open_add_transcript_dialog)
        self.list_header.grid(row=0, column=0, sticky="nsew")

        self.header = Header(self, on_settings=self._open_settings_window)
        self.header.grid(row=0, column=1, sticky="nsew")

        self.top_divider = Divider(self)
        self.top_divider.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.list_body = TranscriptListBody(self, on_select=self._handle_open_transcript)
        self.list_body.grid(row=2, column=0, sticky="nsew")

        self.canvas = Canvas(
            self,
            on_text_submitted=self._handle_text_submitted,
            on_maximize_toggle=self._toggle_focus_mode,
            on_position_changed=self._handle_position_changed,
            on_pause_changed=self._handle_pause_changed,
            on_draft_changed=self._handle_draft_changed,
        )
        self.canvas.grid(row=2, column=1, sticky="nsew")

        self.bottom_divider = Divider(self)
        self.bottom_divider.grid(row=3, column=0, columnspan=2, sticky="nsew")

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
        )
        self.footer.grid(row=4, column=1, sticky="nsew")

        self._refresh_transcript_list()

    def _apply_layout_sizes(self) -> None:
        """Apply the sidebar/header/bottom-band sizes currently held in
        settings. Reused for initial setup, after a Settings Apply, and
        when restoring from focus mode — one source of truth for these
        three region sizes."""
        self.grid_columnconfigure(0, weight=0, minsize=self.settings_store.sidebar_width)
        self.grid_rowconfigure(0, weight=0, minsize=self.settings_store.header_height)
        self.grid_rowconfigure(4, weight=0, minsize=self.settings_store.bottom_band_height)

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

        self.settings_store.set_defaults(
            values["default_wpm"], values["default_font_color"],
            values["default_highlight_color"], values["default_background_color"],
        )

        self.settings_store.set_data_directory(values["data_directory"])
        self.store.set_data_directory(values["data_directory"])

    def _handle_close(self) -> None:
        self.canvas.save_pending_draft()
        self.destroy()

    def _toggle_focus_mode(self) -> None:
        self._focus_mode = not self._focus_mode

        if self._focus_mode:
            self.list_header.grid_remove()
            self.list_body.grid_remove()
            self.header.grid_remove()
            self.top_divider.grid_remove()
            self.bottom_divider.grid_remove()
            self.spaces.grid_remove()
            self.footer.grid_remove()
            self.grid_columnconfigure(0, minsize=0)
            self.grid_rowconfigure(0, minsize=0)
            self.grid_rowconfigure(1, minsize=0)
            self.grid_rowconfigure(3, minsize=0)
            self.grid_rowconfigure(4, minsize=0)
        else:
            self.list_header.grid()
            self.list_body.grid()
            self.header.grid()
            self.top_divider.grid()
            self.bottom_divider.grid()
            self.spaces.grid()
            self.footer.grid()
            self._apply_layout_sizes()
            self.grid_rowconfigure(1, minsize=self.DIVIDER_HEIGHT)
            self.grid_rowconfigure(3, minsize=self.DIVIDER_HEIGHT)

        self.canvas.set_maximized(self._focus_mode)