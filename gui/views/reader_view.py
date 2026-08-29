import customtkinter as ctk
from core.reader import ReaderSession


class ReaderView(ctk.CTkFrame):
    """View that displays the flashing word and playback controls."""

    def __init__(self, master, on_back):
        super().__init__(master)
        self.on_back = on_back
        self.session: ReaderSession | None = None
        self._after_id: str | None = None

        self.word_label = ctk.CTkLabel(self, text="", font=("Arial", 32))
        self.word_label.pack(expand=True)

        self.back_button = ctk.CTkButton(self, text="Back", command=self._handle_back)
        self.back_button.pack(pady=(0, 20))

    def load_session(self, session: ReaderSession) -> None:
        """Attach a new session, cancel any previous timer, and start flashing."""
        self._cancel_pending()
        self.session = session
        self._show_current_frame()
        self._schedule_next()

    def _show_current_frame(self) -> None:
        if self.session is None:
            return
        if self.session.is_finished:
            self.word_label.configure(text="(finished)")
            return
        frame = self.session.current_frame()
        # Plain-text placeholder — real ORP bold/alignment comes in a later step
        self.word_label.configure(text=f"{frame.before}{frame.focus}{frame.after}")

    def _schedule_next(self) -> None:
        if self.session is None or self.session.is_finished:
            return
        delay = self.session.current_delay_ms()
        self._after_id = self.after(delay, self._advance)

    def _advance(self) -> None:
        if self.session is None:
            return
        self.session.advance()
        self._show_current_frame()
        self._schedule_next()

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _handle_back(self) -> None:
        self._cancel_pending()
        self.session = None
        self.on_back()