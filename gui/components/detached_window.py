import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay


class DetachedTranscriptWindow(ctk.CTkToplevel):
    """A standalone window showing one transcript, separate from the main app window."""

    def __init__(self, master, transcript, on_text_submitted, on_closed):
        super().__init__(master)
        self.title(transcript.title)
        self.geometry("500x350")
        self.on_closed = on_closed
        self.protocol("WM_DELETE_WINDOW", self.close)

        if transcript.raw_text.strip():
            display = ReaderDisplay(self)
            display.pack(fill="both", expand=True)
            display.load_session(ReaderSession(transcript.raw_text, wpm=transcript.wpm))
        else:
            TranscriptInput(
                self, on_submit=lambda text: on_text_submitted(transcript, text)
            ).pack(fill="both", expand=True)

    def close(self) -> None:
        """Public — called both by the window's own OS close button and the main
        window's 'Bring back' button, so both paths clean up state identically."""
        self.on_closed()
        self.destroy()