import customtkinter as ctk
from core.reader import ReaderSession
from gui.theme import FONT_HEADING, COCOA_INK, EMBER_GLOW


class ReaderDisplay(ctk.CTkFrame):
    """Displays the flashing word, with the ORP letter rendered in a
    distinct color from the rest of the word.

    The ORP letter's horizontal center is pinned to one fixed x
    position (the row's own center) for every word, regardless of
    word length -- this is the actual point of RSVP: the eye rests at
    one spot and never has to relocate itself between words. Words are
    positioned with .place() rather than .pack(), since pack only
    knows how to center the word as a whole block, not anchor one
    specific letter inside it at a fixed point.

    Two short guide marks (fixed at that same x) are shown above and
    below the letter, but only while a session is actively flashing --
    paused, stopped, or finished states hide them, since there's
    nothing to anchor the eye to when nothing is advancing.
    """

    DEFAULT_FONT_COLOR = COCOA_INK
    DEFAULT_HIGHLIGHT_COLOR = EMBER_GLOW
    DEFAULT_FONT_SIZE = 32

    GUIDE_MARK_THICKNESS = 2        # px -- fixed until Settings makes it configurable
    GUIDE_MARK_MIN_GAP_PX = 6       # px -- safely above HIGHLIGHT_OFFSET_RANGE's max
                                     # magnitude (3), so marks never touch the letter
                                     # even at the largest vertical offset setting
    GUIDE_MARK_LENGTH_RATIO = 0.35  # mark length as a fraction of the current word size

    def __init__(self, master, on_position_changed=None):
        super().__init__(master, fg_color="transparent")
        self.session: ReaderSession | None = None
        self._after_id: str | None = None
        self._is_paused = False
        self._highlight_offset_px = 0
        self.on_position_changed = on_position_changed

        # Anchor geometry from the most recent _position_word() call --
        # None until the row has been sized at least once. Guide marks
        # read these rather than recomputing, so they always match
        # exactly where the letter actually was last placed.
        self._anchor_x: float | None = None
        self._focus_y: float | None = None
        self._focus_half_height: float = 0

        self.word_row = ctk.CTkFrame(self, fg_color="transparent")
        self.word_row.pack(fill="both", expand=True)
        self.word_row.bind("<Configure>", self._handle_row_resized)

        self.word_font = ctk.CTkFont(family=FONT_HEADING, size=self.DEFAULT_FONT_SIZE)

        # Positioned with .place() in _position_word(), not .pack() --
        # see the class docstring for why.
        self.before_label = ctk.CTkLabel(self.word_row, text="", font=self.word_font, text_color=self.DEFAULT_FONT_COLOR)
        self.focus_label = ctk.CTkLabel(self.word_row, text="", font=self.word_font, text_color=self.DEFAULT_HIGHLIGHT_COLOR)
        self.after_label = ctk.CTkLabel(self.word_row, text="", font=self.word_font, text_color=self.DEFAULT_FONT_COLOR)

        # Not placed yet -- _update_guide_marks() shows/positions them
        # only while a session is actively running.
        self.guide_mark_above = ctk.CTkFrame(
            self.word_row, width=self.GUIDE_MARK_THICKNESS, height=8,
            fg_color=self.DEFAULT_FONT_COLOR, corner_radius=0,
        )
        self.guide_mark_below = ctk.CTkFrame(
            self.word_row, width=self.GUIDE_MARK_THICKNESS, height=8,
            fg_color=self.DEFAULT_FONT_COLOR, corner_radius=0,
        )

    def load_session(self, session: ReaderSession, start_paused: bool = False) -> None:
        self._cancel_pending()
        self.session = session
        self._is_paused = start_paused
        self._show_current_frame()
        self._schedule_next()
        self._update_guide_marks()

    def stop(self) -> None:
        self._cancel_pending()
        self.session = None
        self._is_paused = False
        self._update_guide_marks()

    def toggle_pause(self) -> bool:
        if self.session is None or self.session.is_finished:
            return self._is_paused
        self._is_paused = not self._is_paused
        if self._is_paused:
            self._cancel_pending()
        else:
            self._schedule_next()
        self._update_guide_marks()
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
        self._update_guide_marks()

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
        self._update_guide_marks()
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
        # Guide marks default to the regular text color -- a subtle
        # reference line, not an attention-grabbing one. Settings will
        # make this its own choice later.
        self.guide_mark_above.configure(fg_color=font_color)
        self.guide_mark_below.configure(fg_color=font_color)

    def set_font_size(self, size: int) -> None:
        self.word_font.configure(size=size)
        self._position_word()
        self._update_guide_marks()

    def set_highlight_offset(self, offset_px: int) -> None:
        """Shift only the highlighted (focus) letter vertically, relative
        to before/after which stay at the row's normal vertical center.
        Positive = up, negative = down, 0 = default.

        Guide marks track this too -- their gap is measured from the
        letter's actual current top/bottom edge, so they keep a
        constant clearance from wherever the letter ends up rather
        than staying fixed at the un-offset center."""
        self._highlight_offset_px = offset_px
        self._position_word()
        self._update_guide_marks()

    def _show_current_frame(self) -> None:
        if self.session is None:
            return
        if self.session.is_finished:
            self.before_label.configure(text="(finished)")
            self.focus_label.configure(text="")
            self.after_label.configure(text="")
        else:
            frame = self.session.current_frame()
            self.before_label.configure(text=frame.before)
            self.focus_label.configure(text=frame.focus)
            self.after_label.configure(text=frame.after)
        self._position_word()

    def _place_physical(self, widget, *, x, y, anchor) -> None:
        """place() a child of word_row at a position expressed in real
        on-screen pixels -- the same space winfo_width()/winfo_height()
        report, which is what all our anchor math is computed in.

        CustomTkinter's CTkBaseClass.place() silently multiplies x/y by
        the widget's DPI scaling factor before handing them to real
        Tkinter (see customtkinter's ctk_base_class.py place() and
        scaling_base_class.py's _apply_argument_scaling()). Since our
        x/y here are already real physical pixels (derived from
        winfo_width()/winfo_reqwidth(), which report post-scaling
        sizes), passing them to .place() directly gets them scaled a
        SECOND time -- on a 200%-scaled display that pushes every word
        roughly twice as far right/down as intended, off the visible
        edge. This is the confirmed cause of the corner-squeeze bug.

        Dividing by that same factor here via CTk's own
        _reverse_widget_scaling() (the exact inverse it uses
        internally) cancels the doubling out, so the widget lands at
        the physical position we actually computed. Every place() call
        in this file must go through this method -- calling
        .place(x=, y=) directly on a child of word_row will reintroduce
        this bug on any non-100%-scaled display.
        """
        widget.place(
            x=self._reverse_widget_scaling(x),
            y=self._reverse_widget_scaling(y),
            anchor=anchor,
        )

    def _position_word(self) -> None:
        """Places before/focus/after so the focus letter's horizontal
        center always lands at the row's fixed center x. Recomputed on
        every frame -- both the word's text and the font size can
        change the letter's rendered width -- and on resize."""
        self.word_row.update_idletasks()
        row_width = self.word_row.winfo_width()
        row_height = self.word_row.winfo_height()
        if row_width <= 1 or row_height <= 1:
            return  # not yet mapped/sized -- nothing sensible to compute

        focus_width = self.focus_label.winfo_reqwidth()
        focus_height = self.focus_label.winfo_reqheight()

        anchor_x = row_width / 2
        center_y = row_height / 2
        # Positive offset = up = smaller y.
        focus_y = center_y - self._highlight_offset_px

        self._place_physical(self.before_label, x=anchor_x - focus_width / 2, y=center_y, anchor="e")
        self._place_physical(self.focus_label, x=anchor_x, y=focus_y, anchor="center")
        self._place_physical(self.after_label, x=anchor_x + focus_width / 2, y=center_y, anchor="w")

        self._anchor_x = anchor_x
        self._focus_y = focus_y
        self._focus_half_height = focus_height / 2

    def _update_guide_marks(self) -> None:
        if not self._is_running() or self._anchor_x is None:
            self.guide_mark_above.place_forget()
            self.guide_mark_below.place_forget()
            return

        length = self._guide_mark_length()
        gap = self.GUIDE_MARK_MIN_GAP_PX
        self.guide_mark_above.configure(height=length)
        self.guide_mark_below.configure(height=length)

        self._place_physical(
            self.guide_mark_above,
            x=self._anchor_x, y=self._focus_y - self._focus_half_height - gap, anchor="s",
        )
        self._place_physical(
            self.guide_mark_below,
            x=self._anchor_x, y=self._focus_y + self._focus_half_height + gap, anchor="n",
        )

    def _guide_mark_length(self) -> int:
        size = self.word_font.cget("size")
        return max(8, round(size * self.GUIDE_MARK_LENGTH_RATIO))

    def _is_running(self) -> bool:
        return self.session is not None and not self.session.is_finished and not self._is_paused

    def _handle_row_resized(self, event=None) -> None:
        self._position_word()
        self._update_guide_marks()

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
        self._update_guide_marks()

    def _report_position(self) -> None:
        if self.on_position_changed and self.session:
            self.on_position_changed(self.session.index)

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None