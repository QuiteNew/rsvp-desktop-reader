import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay
from gui.components.canvas_toolbar import CanvasToolbar


class DetachedTranscriptWindow(ctk.CTkToplevel):
    """A standalone window showing one transcript, separate from the main app window."""

    def __init__(self, master, transcript, on_text_submitted, on_closed, on_position_changed=None, on_pause_changed=None, initial_draft_text=""):
        super().__init__(master)
        self.transcript = transcript
        self.on_text_submitted = on_text_submitted
        self.on_closed = on_closed
        self.on_position_changed = on_position_changed
        self.on_pause_changed = on_pause_changed

        self.title(transcript.title)
        self.geometry("500x350")
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.toolbar = CanvasToolbar(
            self,
            on_pause_toggle=self._handle_pause_toggle,
            on_restart=self._handle_restart,
            show_maximize=False,
            show_detach=False,
        )

        self.input_view = TranscriptInput(
            self, on_submit=self._handle_text_submitted, initial_text=initial_draft_text
        )
        self.reader_display = ReaderDisplay(self, on_position_changed=self._handle_position_changed)

        self._render_current_state()

    def get_draft_text(self) -> str:
        return self.input_view.get_text()

    def _render_current_state(self) -> None:
        self.toolbar.pack_forget()
        self.input_view.pack_forget()
        self.reader_display.pack_forget()

        if self.transcript.raw_text.strip():
            self.toolbar.pack(anchor="ne", padx=10, pady=10)
            self.toolbar.set_paused(self.transcript.is_paused)
            self.reader_display.set_colors(self.transcript.font_color, self.transcript.highlight_color, self.transcript.background_color)
            self.reader_display.pack(fill="both", expand=True)
            self.reader_display.load_session(
                ReaderSession(self.transcript.raw_text, wpm=self.transcript.wpm, start_index=self.transcript.position),
                start_paused=self.transcript.is_paused,
            )
        else:
            self.input_view.pack(fill="both", expand=True)

    def _handle_text_submitted(self, raw_text: str) -> None:
        self.on_text_submitted(self.transcript, raw_text)
        self._render_current_state()

    def _handle_position_changed(self, index: int) -> None:
        if self.on_position_changed:
            self.on_position_changed(self.transcript, index)

    def _handle_pause_changed(self, is_paused: bool) -> None:
        if self.on_pause_changed:
            self.on_pause_changed(self.transcript, is_paused)

    def _handle_pause_toggle(self) -> None:
        is_paused = self.reader_display.toggle_pause()
        self.toolbar.set_paused(is_paused)
        self._handle_pause_changed(is_paused)

    def _handle_restart(self) -> None:
        self.reader_display.restart()
        self.toolbar.set_paused(False)
        self._handle_pause_changed(False)

    def close(self) -> None:
        self.reader_display.stop()
        draft_text = ""
        if not self.transcript.raw_text.strip():
            draft_text = self.get_draft_text().strip()
        self.on_closed(draft_text)
        self.destroy()