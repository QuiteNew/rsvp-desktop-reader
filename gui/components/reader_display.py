import customtkinter as ctk
from core.reader import ReaderSession


class ReaderDisplay(ctk.CTkFrame):
    """Displays the flashing word, with the ORP letter rendered in a distinct
    color and weight from the rest of the word."""

    DEFAULT_FONT_COLOR = "#FFFFFF"
    DEFAULT_HIGHLIGHT_COLOR = "#E74C3C"

    def __init__(self, master, on_position_changed=None):
        super().__init__(master, fg_color="transparent")
        self.session: ReaderSession | None = None
        self._after_id: str | None = None
        self._is_paused = False
        self.on_position_changed = on_position_changed

        self.word_row = ctk.CTkFrame(self, fg_color="transparent")
        self.word_row.pack(expand=True)

        plain_font = ctk.CTkFont(family="Arial", size=32)
        focus_font = ctk.CTkFont(family="Arial", size=32, weight="bold")

        self.before_label = ctk.CTkLabel(self.word_row, text="", font=plain_font, text_color=self.DEFAULT_FONT_COLOR)
        self.before_label.pack(side="left")

        self.focus_label = ctk.CTkLabel(self.word_row, text="", font=focus_font, text_color=self.DEFAULT_HIGHLIGHT_COLOR)
        self.focus_label.pack(side="left")

        self.after_label = ctk.CTkLabel(self.word_row, text="", font=plain_font, text_color=self.DEFAULT_FONT_COLOR)
        self.after_label.pack(side="left")

    def load_session(self, session: ReaderSession, start_paused: bool = False) -> None:
        self._cancel_pending()
        self.session = session
        self._is_paused = start_paused
        self._show_current_frame()
        self._schedule_next()

    def stop(self) -> None:
        self._cancel_pending()
        self.session = None
        self._is_paused = False

    def toggle_pause(self) -> bool:
        if self.session is None or self.session.is_finished:
            return self._is_paused
        self._is_paused = not self._is_paused
        if self._is_paused:
            self._cancel_pending()
        else:
            self._schedule_next()
        return self._is_paused

    def restart(self) -> None:
        if self.session is None:
            return
        self._cancel_pending()
        self.session.reset()
        self._is_paused = False
        self._show_current_frame()
        self._report_position()
        self._schedule_next()

    def set_wpm(self, wpm: int) -> None:
        if self.session:
            self.session.set_wpm(wpm)

    def set_colors(self, font_color: str, highlight_color: str, background_color: str) -> None:
        self.configure(fg_color=background_color)
        self.word_row.configure(fg_color=background_color)
        self.before_label.configure(text_color=font_color)
        self.after_label.configure(text_color=font_color)
        self.focus_label.configure(text_color=highlight_color)

    def _show_current_frame(self) -> None:
        if self.session is None:
            return
        if self.session.is_finished:
            self.before_label.configure(text="(finished)")
            self.focus_label.configure(text="")
            self.after_label.configure(text="")
            return
        frame = self.session.current_frame()
        self.before_label.configure(text=frame.before)
        self.focus_label.configure(text=frame.focus)
        self.after_label.configure(text=frame.after)

    def _schedule_next(self) -> None:
        if self.session is None or self.session.is_finished or self._is_paused:
            self._after_id = None
            return
        delay = self.session.current_delay_ms()
        self._after_id = self.after(delay, self._advance)

    def _advance(self) -> None:
        if self.session is None:
            return
        self.session.advance()
        self._show_current_frame()
        self._report_position()
        self._schedule_next()

    def _report_position(self) -> None:
        if self.on_position_changed and self.session:
            self.on_position_changed(self.session.index)

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None