import customtkinter as ctk
from core.reader import ReaderSession


class ReaderView(ctk.CTkFrame):
    """View that displays the flashing word and playback controls."""

    def __init__(self, master, on_back):
        super().__init__(master)
        self.on_back = on_back
        self.session: ReaderSession | None = None

        self.word_label = ctk.CTkLabel(self, text="", font=("Arial", 32))
        self.word_label.pack(expand=True)

        # Temporary manual control — replaced by the automatic timer next step
        self.next_button = ctk.CTkButton(self, text="Next word (test)", command=self._handle_next)
        self.next_button.pack(pady=(0, 10))

        self.back_button = ctk.CTkButton(self, text="Back", command=self._handle_back)
        self.back_button.pack(pady=(0, 20))

    def load_session(self, session: ReaderSession) -> None:
        """Attach a new reading session and display its first word."""
        self.session = session
        self._show_current_frame()

    def _show_current_frame(self) -> None:
        if self.session is None or self.session.is_finished:
            self.word_label.configure(text="(finished)")
            return
        frame = self.session.current_frame()
        # Plain-text placeholder — real ORP bold/alignment comes in a later step
        self.word_label.configure(text=f"{frame.before}{frame.focus}{frame.after}")

    def _handle_next(self) -> None:
        if self.session is None:
            return
        self.session.advance()
        self._show_current_frame()

    def _handle_back(self) -> None:
        self.session = None
        self.on_back()