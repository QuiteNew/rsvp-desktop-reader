import customtkinter as ctk
from core.reader import ReaderSession


class ReaderDisplay(ctk.CTkFrame):
    """Displays the flashing word for a loaded ReaderSession."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.session: ReaderSession | None = None
        self._after_id: str | None = None

        self.word_label = ctk.CTkLabel(self, text="", font=("Arial", 32))
        self.word_label.pack(expand=True)

    def load_session(self, session: ReaderSession) -> None:
        self._cancel_pending()
        self.session = session
        self._show_current_frame()
        self._schedule_next()

    def stop(self) -> None:
        """Cancel any pending timer without destroying the widget — call before navigating away."""
        self._cancel_pending()
        self.session = None

    def _show_current_frame(self) -> None:
        if self.session is None:
            return
        if self.session.is_finished:
            self.word_label.configure(text="(finished)")
            return
        frame = self.session.current_frame()
        self.word_label.configure(text=f"{frame.before}{frame.focus}{frame.after}")

    def _schedule_next(self) -> None:
        if self.session is None or self.session.is_finished:
            self._after_id = None  # nothing genuinely pending once finished — keep this honest
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