import customtkinter as ctk
from core.reader import ReaderSession
from gui.theme import FONT_HEADING, COCOA_INK, EMBER_GLOW


class ReaderDisplay(ctk.CTkFrame):
    """Displays the flashing word, with the ORP letter rendered in a
    distinct color from the rest of the word."""

    DEFAULT_FONT_COLOR = COCOA_INK
    DEFAULT_HIGHLIGHT_COLOR = EMBER_GLOW
    DEFAULT_FONT_SIZE = 32

    def __init__(self, master, on_position_changed=None):
        super().__init__(master, fg_color="transparent")
        self.session: ReaderSession | None = None
        self._after_id: str | None = None
        self._is_paused = False
        self.on_position_changed = on_position_changed

        self.word_row = ctk.CTkFrame(self, fg_color="transparent")
        self.word_row.pack(expand=True)

        self.word_font = ctk.CTkFont(family=FONT_HEADING, size=self.DEFAULT_FONT_SIZE)

        self.before_label = ctk.CTkLabel(self.word_row, text="", font=self.word_font, text_color=self.DEFAULT_FONT_COLOR)
        self.before_label.pack(side="left")

        self.focus_label = ctk.CTkLabel(self.word_row, text="", font=self.word_font, text_color=self.DEFAULT_HIGHLIGHT_COLOR)
        self.focus_label.pack(side="left")

        self.after_label = ctk.CTkLabel(self.word_row, text="", font=self.word_font, text_color=self.DEFAULT_FONT_COLOR)
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

    def skip(self, delta: int, force_pause: bool = False) -> bool:
        if self.session is None:
            return self._is_paused
        self._cancel_pending()
        self.session.seek(delta)
        self._show_current_frame()
        self._report_position()
        if force_pause:
            self._is_paused = True
        if not self._is_paused:
            self._schedule_next()
        return self._is_paused

    def set_wpm(self, wpm: int) -> None:
        if self.session:
            self.session.set_wpm(wpm)

    def set_colors(self, font_color: str, highlight_color: str, background_color: str) -> None:
        self.configure(fg_color=background_color)
        self.word_row.configure(fg_color=background_color)
        self.before_label.configure(text_color=font_color)
        self.after_label.configure(text_color=font_color)
        self.focus_label.configure(text_color=highlight_color)

    def set_font_size(self, size: int) -> None:
        self.word_font.configure(size=size)

    def set_highlight_offset(self, offset_px: int) -> None:
        """Shift only the highlighted (focus) letter vertically, relative
        to before/after which stay in their normal centered position.
        Positive = up, negative = down, 0 = default.

        Tkinter's pack() centers a widget's padded box within its cell —
        so asymmetric padding on one side alone doesn't shift the widget
        by that full amount, only by HALF the difference between the two
        sides. Doubling the requested offset and applying it to a single
        side compensates for that exactly, giving a precise N-pixel shift
        rather than an approximate one.
        """
        if offset_px >= 0:
            pady = (0, offset_px * 2)   # more padding below -> shifts up
        else:
            pady = (abs(offset_px) * 2, 0)  # more padding above -> shifts down
        # Re-calling pack() on an already-managed widget (no pack_forget
        # first) updates its options in place without moving it in the
        # packing order — before/focus/after stay in the correct
        # left-to-right sequence.
        self.focus_label.pack(side="left", pady=pady)

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