import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay
from gui.components.canvas_toolbar import CanvasToolbar
from gui.components.stop_button import StopButton
from gui.components.detached_window import DetachedTranscriptWindow
from gui.theme import HEARTH_PAPER


class Canvas(ctk.CTkFrame):
    """Main reading area: stop button (top-left) and toolbar (top-right)
    above whichever content state applies."""

    def __init__(
        self, master,
        on_text_submitted=None, on_maximize_toggle=None,
        on_position_changed=None, on_pause_changed=None, on_draft_changed=None,
        skip_word_count: int = 10, pause_on_skip: bool = False,
    ):
        super().__init__(master, fg_color=HEARTH_PAPER, corner_radius=0)
        self.on_text_submitted = on_text_submitted
        self.on_maximize_toggle = on_maximize_toggle
        self.on_position_changed = on_position_changed
        self.on_pause_changed = on_pause_changed
        self.on_draft_changed = on_draft_changed
        self._skip_word_count = skip_word_count
        self._pause_on_skip = pause_on_skip
        self.current_transcript = None
        self._detached_transcript_id = None
        self._detached_transcript = None
        self._detached_window = None
        self._input_currently_shown = False
        self._stopped_transcript_ids: set[int] = set()

        self.button_row = ctk.CTkFrame(self, fg_color="transparent")
        self.button_row.grid_columnconfigure(0, weight=1)
        self.button_row.grid_columnconfigure(1, weight=0)

        self.stop_button = StopButton(self.button_row, on_stop=self._handle_stop)
        self.stop_button.grid(row=0, column=0, sticky="w")

        self.toolbar = CanvasToolbar(
            self.button_row,
            on_pause_toggle=self._handle_pause_toggle,
            on_restart=self._handle_restart,
            on_maximize_toggle=self._handle_maximize_toggle,
            on_detach=self._handle_detach,
        )
        self.toolbar.grid(row=0, column=1, sticky="e")

        self.content_area = ctk.CTkFrame(self, fg_color="transparent")

        self.empty_label = ctk.CTkLabel(self.content_area, text="Select or create a transcript to begin")
        self.input_view = TranscriptInput(self.content_area, on_submit=self._handle_text_submitted)
        self.reader_display = ReaderDisplay(self.content_area, on_position_changed=self._handle_position_changed)

        self.detached_placeholder = ctk.CTkFrame(self.content_area, fg_color="transparent")
        ctk.CTkLabel(
            self.detached_placeholder, text="Transcript window detached", text_color="gray60"
        ).pack(expand=True, pady=(0, 10))
        ctk.CTkButton(
            self.detached_placeholder, text="✕  Bring back", width=130, command=self._handle_reattach
        ).pack()

        self._show_empty()

    def load_transcript(self, transcript) -> None:
        self._capture_current_draft()
        self.reader_display.stop()
        self.current_transcript = transcript

        if transcript.id == self._detached_transcript_id:
            self._show_detached_placeholder()
        elif transcript.id in self._stopped_transcript_ids:
            self.input_view.set_text(transcript.raw_text)
            self._show_input()
        elif transcript.raw_text.strip():
            self._show_reader()
            self.toolbar.set_paused(transcript.is_paused)
            self.reader_display.set_colors(transcript.font_color, transcript.highlight_color, transcript.background_color)
            self.reader_display.load_session(
                ReaderSession(transcript.raw_text, wpm=transcript.wpm, start_index=transcript.position),
                start_paused=transcript.is_paused,
            )
        else:
            self.input_view.set_text(transcript.draft_text)
            self._show_input()

    def handle_transcript_deleted(self, transcript_id: int) -> None:
        was_current = self.current_transcript is not None and self.current_transcript.id == transcript_id
        was_detached = self._detached_transcript_id == transcript_id

        if was_current:
            self.current_transcript = None
            self.reader_display.stop()

        self._stopped_transcript_ids.discard(transcript_id)

        if was_detached:
            detached_window = self._detached_window
            self._detached_transcript_id = None
            self._detached_transcript = None
            self._detached_window = None
            if detached_window:
                detached_window.destroy()

        if was_current:
            self._show_empty()

    def set_maximized(self, is_maximized: bool) -> None:
        self.toolbar.set_maximized(is_maximized)

    def set_wpm(self, wpm: int) -> None:
        self.reader_display.set_wpm(wpm)
        if self._detached_window:
            self._detached_window.reader_display.set_wpm(wpm)

    def set_colors(self, font_color: str, highlight_color: str, background_color: str) -> None:
        self.reader_display.set_colors(font_color, highlight_color, background_color)
        if self._detached_window:
            self._detached_window.reader_display.set_colors(font_color, highlight_color, background_color)

    def skip_backward(self) -> None:
        self._skip(-self._skip_word_count)

    def skip_forward(self) -> None:
        self._skip(self._skip_word_count)

    def _skip(self, delta: int) -> None:
        """Skip whichever reader display is actually active — the
        detached popup's if this transcript is currently detached,
        otherwise the main canvas's own. Only that one result gets
        persisted: the main display sits inactive while detached, and
        using its (stale, always-unpaused) result instead would silently
        overwrite the real one from the detached side."""
        if self._detached_window:
            is_paused = self._detached_window.reader_display.skip(delta, force_pause=self._pause_on_skip)
            self._detached_window.toolbar.set_paused(is_paused)
        else:
            is_paused = self.reader_display.skip(delta, force_pause=self._pause_on_skip)
            self.toolbar.set_paused(is_paused)
        self._handle_pause_changed(is_paused)

    def set_skip_word_count(self, count: int) -> None:
        self._skip_word_count = count
        if self._detached_window:
            self._detached_window.set_skip_word_count(count)

    def set_pause_on_skip(self, enabled: bool) -> None:
        self._pause_on_skip = enabled
        if self._detached_window:
            self._detached_window.set_pause_on_skip(enabled)

    def save_pending_draft(self) -> None:
        self._capture_current_draft()

    def _capture_current_draft(self) -> None:
        if self._input_currently_shown and self.current_transcript:
            text = self.input_view.get_text().strip()
            self._report_draft_changed(self.current_transcript, text)

    def _report_draft_changed(self, transcript, text: str) -> None:
        if self.on_draft_changed:
            self.on_draft_changed(transcript, text)

    def _handle_text_submitted(self, raw_text: str) -> None:
        if self.current_transcript:
            self._stopped_transcript_ids.discard(self.current_transcript.id)
            self._report_draft_changed(self.current_transcript, "")
        if self.on_text_submitted and self.current_transcript:
            self.on_text_submitted(self.current_transcript, raw_text)

    def _handle_position_changed(self, index: int) -> None:
        if self.on_position_changed and self.current_transcript:
            self.on_position_changed(self.current_transcript, index)

    def _handle_pause_changed(self, is_paused: bool) -> None:
        if self.on_pause_changed and self.current_transcript:
            self.on_pause_changed(self.current_transcript, is_paused)

    def _handle_pause_toggle(self) -> None:
        is_paused = self.reader_display.toggle_pause()
        self.toolbar.set_paused(is_paused)
        self._handle_pause_changed(is_paused)

    def _handle_restart(self) -> None:
        self.reader_display.restart()
        self.toolbar.set_paused(False)
        self._handle_pause_changed(False)

    def _handle_stop(self) -> None:
        if not self.current_transcript:
            return
        self.reader_display.stop()
        self.toolbar.set_paused(False)
        self._stopped_transcript_ids.add(self.current_transcript.id)
        self._handle_position_changed(0)
        self._handle_pause_changed(False)
        self.input_view.set_text(self.current_transcript.raw_text)
        self._show_input()

    def _handle_maximize_toggle(self) -> None:
        if self.on_maximize_toggle:
            self.on_maximize_toggle()

    def _handle_detach(self) -> None:
        if not self.current_transcript:
            return
        self.reader_display.stop()  # the main display becomes inactive the moment this transcript detaches
        self._detached_transcript_id = self.current_transcript.id
        self._detached_transcript = self.current_transcript

        draft_text = ""
        if not self.current_transcript.raw_text.strip():
            draft_text = self.input_view.get_text().strip()
            self._report_draft_changed(self.current_transcript, draft_text)

        self._detached_window = DetachedTranscriptWindow(
            self,
            self.current_transcript,
            initial_draft_text=draft_text,
            on_text_submitted=self._handle_detached_text_submitted,
            on_closed=self._handle_detached_closed,
            on_position_changed=self.on_position_changed,
            on_pause_changed=self.on_pause_changed,
            skip_word_count=self._skip_word_count,
            pause_on_skip=self._pause_on_skip,
        )
        self._show_detached_placeholder()

    def _handle_detached_text_submitted(self, transcript, raw_text: str) -> None:
        self._stopped_transcript_ids.discard(transcript.id)
        self._report_draft_changed(transcript, "")
        if self.on_text_submitted:
            self.on_text_submitted(transcript, raw_text)

    def _handle_detached_closed(self, draft_text: str = "") -> None:
        detached_transcript = self._detached_transcript
        self._detached_transcript_id = None
        self._detached_transcript = None
        self._detached_window = None
        if detached_transcript and not detached_transcript.raw_text.strip():
            self._report_draft_changed(detached_transcript, draft_text)
        if self.current_transcript:
            self.load_transcript(self.current_transcript)

    def _handle_reattach(self) -> None:
        if self._detached_window:
            self._detached_window.close()

    def _layout(self, show_buttons: bool) -> None:
        self.button_row.pack_forget()
        self.content_area.pack_forget()
        if show_buttons:
            self.button_row.pack(fill="x", padx=10, pady=10)
        self.content_area.pack(fill="both", expand=True)

    def _show_content(self, widget) -> None:
        for other in (self.empty_label, self.input_view, self.reader_display, self.detached_placeholder):
            other.pack_forget()
        widget.pack(fill="both", expand=True)

    def _show_empty(self) -> None:
        self._input_currently_shown = False
        self._layout(show_buttons=False)
        self._show_content(self.empty_label)

    def _show_input(self) -> None:
        self._input_currently_shown = True
        self._layout(show_buttons=True)
        self._show_content(self.input_view)

    def _show_reader(self) -> None:
        self._input_currently_shown = False
        self._layout(show_buttons=True)
        self._show_content(self.reader_display)

    def _show_detached_placeholder(self) -> None:
        self._input_currently_shown = False
        self._layout(show_buttons=False)
        self._show_content(self.detached_placeholder)