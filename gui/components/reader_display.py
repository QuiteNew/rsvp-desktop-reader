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

    An optional pair of horizontal ticks can also be shown, one at the
    outer tip of each vertical mark, forming a crosshair. They stay
    centered on the same fixed anchor x as everything else. Their
    LENGTH is constant regardless of the current word -- it's derived
    from the reading row's own width, shrunk by a fixed margin on each
    side so the ticks sit close to the row's left/right edges without
    touching them (see _guide_mark_horizontal_length()). Thickness and
    color are fixed constants (GUIDE_MARK_HORIZONTAL_*), not
    user-configurable; only whether they're shown at all is, via
    set_guide_mark_horizontal_enabled().
    """

    DEFAULT_FONT_COLOR = COCOA_INK
    DEFAULT_HIGHLIGHT_COLOR = EMBER_GLOW
    DEFAULT_FONT_SIZE = 32

    GUIDE_MARK_THICKNESS = 2        # px -- construction-time default only; the live value comes
                                     # from Settings via set_guide_mark_thickness(). This is a
                                     # plain logical-pixel constant (like a font size), not
                                     # derived from winfo_width(), so CTk's normal DPI
                                     # auto-scaling applies to it correctly -- it must NOT be
                                     # routed through _configure_physical_width().
    GUIDE_MARK_MIN_GAP_PX = 6       # px -- safely above HIGHLIGHT_OFFSET_RANGE's max
                                     # magnitude (3), so marks never touch the letter
                                     # even at the largest vertical offset setting
    GUIDE_MARK_LENGTH_RATIO = 0.35  # construction-time default only, as a fraction (not %) --
                                     # the live value comes from Settings via
                                     # set_guide_mark_length_percent(). Deliberately kept as a
                                     # ratio of the current font size (not a fixed px value like
                                     # GUIDE_MARK_THICKNESS), so the marks keep scaling with word
                                     # size -- see set_guide_mark_length_percent() docstring.

    GUIDE_MARK_HORIZONTAL_THICKNESS_PX = 2     # px -- fixed; TEMPORARY test value, was 1.
                                                # Debug output confirmed the 1px-tall guide_line
                                                # widgets were being correctly created, mapped,
                                                # sized and positioned by Tkinter (winfo_ismapped=1,
                                                # correct width/x/y, correct fg_color) even though
                                                # nothing was visible on screen -- the leading
                                                # hypothesis is that CTkFrame's canvas-based
                                                # rounded-rect draw routine doesn't paint a visible
                                                # fill at 1 physical pixel of thickness. This bumps
                                                # it to 2px (matching the vertical marks' known-
                                                # working GUIDE_MARK_THICKNESS) as a test -- not yet
                                                # confirmed as the fix.
    GUIDE_MARK_HORIZONTAL_EDGE_MARGIN_PX = 34  # px kept clear between each tick's end and the
                                                # reading row's left/right edge -- the "close
                                                # to the wall but not touching it" gap. This is
                                                # the one number worth tuning by eye -- re-tune
                                                # this after confirming the width-scaling fix
                                                # below, since the previously-visible size was
                                                # an artifact of that bug, not this margin.
    GUIDE_MARK_HORIZONTAL_MIN_LENGTH_PX = 20   # px floor, in case the row is ever narrower
                                                # than the margins (e.g. a very small detached
                                                # window)
    GUIDE_MARK_HORIZONTAL_COLOR = "#9A9A9A"    # fixed neutral grey -- deliberately outside
                                                # gui/theme.py's warm palette (which has no
                                                # neutral grey token). Not user-configurable:
                                                # these ticks are meant to stay visually
                                                # constant regardless of theme or per-transcript
                                                # colors, receding into the background rather
                                                # than drawing attention.

    def __init__(self, master, on_position_changed=None):
        super().__init__(master, fg_color="transparent")
        self.session: ReaderSession | None = None
        self._after_id: str | None = None
        self._is_paused = False
        self._highlight_offset_px = 0
        self._guide_mark_horizontal_enabled = False
        self._guide_mark_length_ratio = self.GUIDE_MARK_LENGTH_RATIO
        self.on_position_changed = on_position_changed

        # Anchor geometry from the most recent _position_word() call --
        # None until the row has been sized at least once. Guide marks
        # read these rather than recomputing, so they always match
        # exactly where the letter actually was last placed.
        self._anchor_x: float | None = None
        self._focus_y: float | None = None
        self._focus_half_height: float = 0
        self._row_width: float = 0

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

        # Fixed-style horizontal ticks -- a crosshair at the outer tip
        # of each vertical mark. Thickness and color are hardcoded
        # constants (see GUIDE_MARK_HORIZONTAL_* above); width is
        # recomputed on every resize/frame in _update_guide_marks() to
        # track the reading row's own width. The width given here is
        # just a placeholder until the first _update_guide_marks() call
        # reconfigures it.
        self.guide_line_above = ctk.CTkFrame(
            self.word_row, width=self.GUIDE_MARK_HORIZONTAL_MIN_LENGTH_PX, height=self.GUIDE_MARK_HORIZONTAL_THICKNESS_PX,
            fg_color=self.GUIDE_MARK_HORIZONTAL_COLOR, corner_radius=0,
        )
        self.guide_line_below = ctk.CTkFrame(
            self.word_row, width=self.GUIDE_MARK_HORIZONTAL_MIN_LENGTH_PX, height=self.GUIDE_MARK_HORIZONTAL_THICKNESS_PX,
            fg_color=self.GUIDE_MARK_HORIZONTAL_COLOR, corner_radius=0,
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
        # Vertical guide marks are NOT touched here -- their color is a
        # flat global value from Settings (see set_guide_mark_color()),
        # independent of the current transcript's font color, same as
        # the horizontal ticks are independent via a fixed constant.

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

    def set_guide_mark_horizontal_enabled(self, enabled: bool) -> None:
        """Show/hide the horizontal crosshair ticks. This is the only
        configurable property they have -- thickness and color are
        fixed constants, and length is a constant derived from the
        reading row's own width (see GUIDE_MARK_HORIZONTAL_* and
        _guide_mark_horizontal_length())."""
        self._guide_mark_horizontal_enabled = enabled
        self._update_guide_marks()

    def set_guide_mark_thickness(self, thickness_px: int) -> None:
        """Width of the two vertical guide marks (above/below the
        highlighted letter). A plain logical-pixel value -- see the
        GUIDE_MARK_THICKNESS comment above for why this is configured
        directly rather than through _configure_physical_width()."""
        self.guide_mark_above.configure(width=thickness_px)
        self.guide_mark_below.configure(width=thickness_px)
        self._update_guide_marks()

    def set_guide_mark_length_percent(self, percent: int) -> None:
        """Length of the two vertical guide marks, as a percentage of
        the current word-size font (e.g. 35 means 0.35 * font size).
        Kept as a ratio rather than a fixed px value -- unlike the
        horizontal ticks, which are deliberately fixed-style and
        window-relative, the vertical marks anchor the eye to the
        letter itself, so they're meant to keep growing and shrinking
        together with the Word Size setting."""
        self._guide_mark_length_ratio = percent / 100
        self._update_guide_marks()

    def set_guide_mark_color(self, color: str) -> None:
        """Color of the two vertical guide marks (above/below the
        highlighted letter). A flat global value from Settings --
        unlike before/after text and the highlight letter, these marks
        no longer follow the current transcript's font color (see
        set_colors())."""
        self.guide_mark_above.configure(fg_color=color)
        self.guide_mark_below.configure(fg_color=color)

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

    def _configure_physical_width(self, widget, width) -> None:
        """configure(width=...) on a CTk widget applies the exact same
        DPI auto-scaling that _place_physical() above has to cancel for
        x/y -- confirmed via debug output on the horizontal guide ticks:
        setting width=1412 (a physical-pixel value, computed from
        winfo_width()) rendered an actual on-screen width of 2824,
        exactly double, on this 200%-scaled display. Dividing by the
        same factor here cancels that out, the same way _place_physical
        does for position. Use this instead of widget.configure(width=)
        directly whenever the width being set was computed from
        winfo_width()/winfo_reqwidth() (i.e. is already physical) rather
        than being a plain logical constant like GUIDE_MARK_THICKNESS.
        """
        widget.configure(width=self._reverse_widget_scaling(width))

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

        anchor_x = row_width / 2
        center_y = row_height / 2
        # Positive offset = up = smaller y.
        focus_y = center_y - self._highlight_offset_px

        if self.session is not None and self.session.is_finished:
            # No ORP letter to anchor around here -- before_label holds
            # the whole "(finished)" message with focus/after emptied.
            # The normal anchor="e" placement below assumes an actual
            # focus_width to butt up against; with that width near 0 it
            # left the message sitting to the left of center instead of
            # centered on it. Center it directly instead.
            self.focus_label.place_forget()
            self.after_label.place_forget()
            self._place_physical(self.before_label, x=anchor_x, y=center_y, anchor="center")
            self._anchor_x = anchor_x
            self._focus_y = focus_y
            self._focus_half_height = 0
            self._row_width = row_width
            return

        focus_width = self.focus_label.winfo_reqwidth()
        focus_height = self.focus_label.winfo_reqheight()

        self._place_physical(self.before_label, x=anchor_x - focus_width / 2, y=center_y, anchor="e")
        self._place_physical(self.focus_label, x=anchor_x, y=focus_y, anchor="center")
        self._place_physical(self.after_label, x=anchor_x + focus_width / 2, y=center_y, anchor="w")

        self._anchor_x = anchor_x
        self._focus_y = focus_y
        self._focus_half_height = focus_height / 2
        self._row_width = row_width

    def _update_guide_marks(self) -> None:
        if not self._is_running() or self._anchor_x is None:
            self.guide_mark_above.place_forget()
            self.guide_mark_below.place_forget()
            self.guide_line_above.place_forget()
            self.guide_line_below.place_forget()
            return

        length = self._guide_mark_length()
        gap = self.GUIDE_MARK_MIN_GAP_PX
        self.guide_mark_above.configure(height=length)
        self.guide_mark_below.configure(height=length)

        # Inner edge = nearest the letter, where each vertical mark
        # starts. Outer edge = its far tip -- that's where the matching
        # horizontal tick sits, forming a crosshair.
        inner_top_y = self._focus_y - self._focus_half_height - gap
        inner_bottom_y = self._focus_y + self._focus_half_height + gap
        outer_top_y = inner_top_y - length
        outer_bottom_y = inner_bottom_y + length

        self._place_physical(self.guide_mark_above, x=self._anchor_x, y=inner_top_y, anchor="s")
        self._place_physical(self.guide_mark_below, x=self._anchor_x, y=inner_bottom_y, anchor="n")

        if self._guide_mark_horizontal_enabled:
            horizontal_length = self._guide_mark_horizontal_length()
            self._configure_physical_width(self.guide_line_above, horizontal_length)
            self._configure_physical_width(self.guide_line_below, horizontal_length)
            self._place_physical(self.guide_line_above, x=self._anchor_x, y=outer_top_y, anchor="center")
            self._place_physical(self.guide_line_below, x=self._anchor_x, y=outer_bottom_y, anchor="center")
        else:
            self.guide_line_above.place_forget()
            self.guide_line_below.place_forget()

    def _guide_mark_length(self) -> int:
        size = self.word_font.cget("size")
        return max(8, round(size * self._guide_mark_length_ratio))

    def _guide_mark_horizontal_length(self) -> int:
        """How wide the horizontal ticks should be: a constant length
        derived from the reading row's own current width, not from the
        word being shown. Shrinking row_width by a fixed margin on each
        side keeps the ticks close to the row's left/right edges without
        ever touching them; the MIN_LENGTH_PX floor only matters if the
        row is ever narrower than the two margins combined."""
        length = self._row_width - (2 * self.GUIDE_MARK_HORIZONTAL_EDGE_MARGIN_PX)
        return max(self.GUIDE_MARK_HORIZONTAL_MIN_LENGTH_PX, round(length))

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