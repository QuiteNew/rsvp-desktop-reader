import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay


class Canvas(ctk.CTkFrame):
    """Main reading area: paste-in prompt for empty transcripts, flashing display once text exists."""

    def __init__(self, master, on_text_submitted=None):
        super().__init__(master, fg_color="#2ECC71", corner_radius=0)
        self.on_text_submitted = on_text_submitted
        self.current_transcript = None

        self.empty_label = ctk.CTkLabel(self, text="Select or create a transcript to begin")
        self.input_view = TranscriptInput(self, on_submit=self._handle_text_submitted)
        self.reader_display = ReaderDisplay(self)

        self._show_empty()

    def load_transcript(self, transcript) -> None:
        """Show the right state — paste-in or reading — for the given transcript."""
        self.reader_display.stop()
        self.current_transcript = transcript

        if transcript.raw_text.strip():
            self._show_reader()
            session = ReaderSession(transcript.raw_text, wpm=transcript.wpm)
            self.reader_display.load_session(session)
        else:
            self._show_input()

    def _handle_text_submitted(self, raw_text: str) -> None:
        if self.on_text_submitted and self.current_transcript:
            self.on_text_submitted(self.current_transcript, raw_text)

    def _show_empty(self) -> None:
        self.input_view.pack_forget()
        self.reader_display.pack_forget()
        self.empty_label.pack(expand=True)

    def _show_input(self) -> None:
        self.empty_label.pack_forget()
        self.reader_display.pack_forget()
        self.input_view.pack(fill="both", expand=True)

    def _show_reader(self) -> None:
        self.empty_label.pack_forget()
        self.input_view.pack_forget()
        self.reader_display.pack(fill="both", expand=True)