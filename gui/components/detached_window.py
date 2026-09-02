import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay


class DetachedTranscriptWindow(ctk.CTkToplevel):
    """A standalone window showing one transcript, separate from the main app window."""

    def __init__(self, master, transcript, on_text_submitted, on_closed, initial_draft_text=""):
        super().__init__(master)
        self.transcript = transcript
        self.on_text_submitted = on_text_submitted
        self.on_closed = on_closed

        self.title(transcript.title)
        self.geometry("500x350")
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.input_view = TranscriptInput(
            self, on_submit=self._handle_text_submitted, initial_text=initial_draft_text
        )
        self.reader_display = ReaderDisplay(self)

        self._render_current_state()

    def get_draft_text(self) -> str:
        """Whatever's currently typed in this window's paste box, submitted or not."""
        return self.input_view.get_text()

    def _render_current_state(self) -> None:
        if self.transcript.raw_text.strip():
            self.input_view.pack_forget()
            self.reader_display.pack(fill="both", expand=True)
            self.reader_display.load_session(
                ReaderSession(self.transcript.raw_text, wpm=self.transcript.wpm)
            )
        else:
            self.reader_display.pack_forget()
            self.input_view.pack(fill="both", expand=True)

    def _handle_text_submitted(self, raw_text: str) -> None:
        self.on_text_submitted(self.transcript, raw_text)
        self._render_current_state()

    def close(self) -> None:
        draft_text = ""
        if not self.transcript.raw_text.strip():
            draft_text = self.get_draft_text().strip()
        self.on_closed(draft_text)
        self.destroy()