import customtkinter as ctk

from gui.views.input_view import InputView
from gui.views.reader_view import ReaderView
from core.reader import ReaderSession


class RSVPApp(ctk.CTk):
    """Main application window for the RSVP reader."""

    def __init__(self):
        super().__init__()
        self.title("RSVP Reader")
        self.geometry("700x500")

        self.input_view = InputView(self, on_start=self._start_reading)
        self.reader_view = ReaderView(self, on_back=self._show_input)

        self._show_input()

    def _show_input(self) -> None:
        self.reader_view.pack_forget()
        self.input_view.pack(fill="both", expand=True)

    def _start_reading(self, raw_text: str) -> None:
        session = ReaderSession(raw_text, wpm=300)  # WPM slider comes in step 5
        self.input_view.pack_forget()
        self.reader_view.pack(fill="both", expand=True)
        self.reader_view.load_session(session)