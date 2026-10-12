import time

import customtkinter as ctk
from core.reader import ReaderSession, assemble_chunk_text
from core.colors import blend_colors
from core.scroll import scrollbar_fractions, pan_from_fraction, clamp_pan
from gui.theme import FONT_HEADING, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, HEARTH_PAPER

class ReaderDisplay(ctk.CTkFrame):
    """Displays the flashing word, with the ORP letter rendered in a
    distinct color from the rest of the word.

    The ORP letter's horizontal center is pinned to one fixed x
    position (the row's own center) for every word, regardless of word
    length. This is the actual point of RSVP: the eye rests at one spot
    and never has to relocate itself between words. Words are positioned
    with .place() rather than .pack(), since pack only knows how to
    center the word as a whole block, not anchor one specific letter
    inside it at a fixed point.

    Two short guide marks (fixed at that same x) are shown above and
    below the letter, but only while a session is actively flashing:
    paused, stopped, or finished states hide them, since there's nothing
    to anchor the eye to when nothing is advancing.

    An optional pair of horizontal ticks can also be shown, one at the
    outer tip of each vertical mark, forming a crosshair. They stay
    centered on the same fixed anchor x as everything else. Their length
    is constant regardless of the current word: it's derived from the
    reading row's own width, shrunk by a fixed margin on each side so
    the ticks sit close to the row's left/right edges without touching
    them (see _guide_mark_horizontal_length()). Thickness and color are
    fixed constants (GUIDE_MARK_HORIZONTAL_*), not user-configurable;
    only whether they're shown at all is, via
    set_guide_mark_horizontal_enabled().

    An optional peripheral context ribbon can be shown below the focal
    word: the current word centred under the same anchor x, dimmed, with
    a few previous words to its left and upcoming words to its right, so
    peripheral vision keeps the thread of the sentence. Off by default;
    see set_peripheral_context() and _update_peripheral_context().
    """

    DEFAULT_FONT_COLOR = COCOA_INK
    DEFAULT_HIGHLIGHT_COLOR = EMBER_GLOW
    DEFAULT_FONT_SIZE = 32

    GUIDE_MARK_THICKNESS = 2        # px, construction-time default only; the live value comes
                                     # from Settings via set_guide_mark_thickness(). This is a
                                     # plain logical-pixel constant (like a font size), not
                                     # derived from winfo_width(), so CTk's normal DPI
                                     # auto-scaling applies to it correctly. It must not be
                                     # routed through _configure_physical_width().
    GUIDE_MARK_MIN_GAP_PX = 6       # px, safely above HIGHLIGHT_OFFSET_RANGE's max
                                     # magnitude (3), so marks never touch the letter
                                     # even at the largest vertical offset setting
    GUIDE_MARK_LENGTH_RATIO = 0.35  # construction-time default only, as a fraction (not %).
                                     # The live value comes from Settings via
                                     # set_guide_mark_length_percent(). Deliberately kept as a
                                     # ratio of the current font size (not a fixed px value like
                                     # GUIDE_MARK_THICKNESS), so the marks keep scaling with word
                                     # size; see set_guide_mark_length_percent() docstring.

    GUIDE_MARK_HORIZONTAL_THICKNESS_PX = 2     # px, fixed. Kept at 2 rather than 1: CTkFrame's
                                                # canvas-based rounded-rect draw routine doesn't
                                                # reliably paint a visible fill at 1 physical
                                                # pixel of thickness.
    GUIDE_MARK_HORIZONTAL_EDGE_MARGIN_PX = 34  # px kept clear between each tick's end and the
                                                # reading row's left/right edge: the "close to
                                                # the wall but not touching it" gap. The one
                                                # number worth tuning by eye.
    GUIDE_MARK_HORIZONTAL_MIN_LENGTH_PX = 20   # px floor, in case the row is ever narrower
                                                # than the margins (e.g. a very small detached
                                                # window)
    GUIDE_MARK_HORIZONTAL_COLOR = "#9A9A9A"    # fixed neutral grey, deliberately outside
                                                # gui/theme.py's warm palette (which has no
                                                # neutral grey token). Not user-configurable:
                                                # these ticks are meant to stay visually
                                                # constant regardless of theme or per-transcript
                                                # colors, receding into the background rather
                                                # than drawing attention.

    PERIPHERAL_CONTEXT_SIZE_RATIO = 0.5    # ribbon font size as a fraction of the word font size
    PERIPHERAL_CONTEXT_DIM = 0.55          # blend fraction toward the background (0 = full font colour, 1 = background)
    PERIPHERAL_CONTEXT_WORD_GAP_PX = 10    # gap between the current word and each flanking side
    PERIPHERAL_CONTEXT_TOP_MARGIN_PX = 8   # breathing space below the lowest guide-mark tip

    FIT_FLOOR_RATIO = 0.6          # auto-fit shrinks the rendered font no smaller than this
                                    # fraction of the chosen Word size; anything that still
                                    # overflows past the floor is the scrollbar's job (later)
    FIT_SIDE_MARGIN_PX = 8         # px kept clear on each side of the reading row, so a fitted
                                    # flash sits just inside the edges rather than flush to them
    FIT_WIDEST_CANDIDATES = 12     # how many of the longest chunks (by character length) to
                                    # measure in real pixels when finding the widest one
    SCROLL_UNIT_PX = 24            # how far one scrollbar "unit" (an arrow click or a wheel
                                    # notch) slides the flash; a trough click pans a full row

    def __init__(self, master, on_position_changed=None, on_session_stats=None, on_progress=None):
        super().__init__(master, fg_color="transparent")
        self.session: ReaderSession | None = None
        self._after_id: str | None = None
        self._is_paused = False
        self._resume_rewind_enabled = False
        self._resume_rewind_words = 3
        self._scrub_pause_enabled = True
        # Peripheral context ribbon (dim words around the current one),
        # off by default
        self._peripheral_context_enabled = False
        self._peripheral_context_before = 1
        self._peripheral_context_after = 2
        # Scrubber drag state (see scrub_move/scrub_end). _scrubbing is True
        # between the first move of a drag and its release; _scrub_was_playing
        # records whether reading was playing when that drag began, so
        # scrub_end knows whether to resume.
        self._scrubbing = False
        self._scrub_was_playing = False
        self._highlight_offset_px = 0
        self._guide_mark_horizontal_enabled = False
        self._guide_mark_length_ratio = self.GUIDE_MARK_LENGTH_RATIO
        self._guide_mark_thickness_px = self.GUIDE_MARK_THICKNESS
        # The current transcript's reading colours, kept so the context
        # ribbon can dim the font toward the background. Updated by
        # set_colors(); the defaults match the label defaults below.
        self._font_color = self.DEFAULT_FONT_COLOR
        self._background_color = HEARTH_PAPER
        self.on_position_changed = on_position_changed
        self.on_session_stats = on_session_stats
        self.on_progress = on_progress

        # Per-session stats tracking: see load_session(),
        # finalize_session(), _start_active_span()/_end_active_span(),
        # and _advance(). words/active-seconds accumulate for whatever
        # session is currently loaded and are reset at the start of the
        # next load_session() call, right after being reported by
        # finalize_session(). _active_span_start is None whenever
        # nothing is actively playing right now (paused, finished, or no
        # session at all); while it's set, it's the time.monotonic()
        # moment the current unpaused stretch began.
        self._session_words_read = 0
        self._session_active_seconds = 0.0
        self._active_span_start: float | None = None

        # Anchor geometry from the most recent _position_word() call.
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

        # Positioned with .place() in _position_word(), not .pack();
        # see the class docstring for why.
        self.before_label = ctk.CTkLabel(self.word_row, text="", font=self.word_font, text_color=self.DEFAULT_FONT_COLOR)
        self.focus_label = ctk.CTkLabel(self.word_row, text="", font=self.word_font, text_color=self.DEFAULT_HIGHLIGHT_COLOR)
        self.after_label = ctk.CTkLabel(self.word_row, text="", font=self.word_font, text_color=self.DEFAULT_FONT_COLOR)

        # Auto-fit state. The chosen Word size is what the user set; the font is
        # rendered at a size <= it so the widest chunk still fits the reading
        # row. Only the render size ever changes, the chosen size is never
        # written back. _fit_widest is the (before, focus, after) of the widest
        # chunk and _fit_required_per_size its required width per unit of font
        # size; _fit_left_reach_per_size / _fit_right_reach_per_size are how far
        # that chunk reaches each side of the centre anchor, also per unit of
        # font size, which the scrollbar uses to size its travel. All are
        # recomputed only when the chunks change (a load or a re-group).
        # _fit_measure_label is an off-screen label used only to size a chunk in
        # real pixels (winfo_reqwidth); it is never placed, so it never disturbs
        # the three visible labels.
        self._chosen_font_size = self.DEFAULT_FONT_SIZE
        self._fit_widest: tuple[str, str, str] | None = None
        self._fit_required_per_size: float | None = None
        self._fit_left_reach_per_size: float | None = None
        self._fit_right_reach_per_size: float | None = None
        self._fit_measure_font = ctk.CTkFont(family=FONT_HEADING, size=self.DEFAULT_FONT_SIZE)
        self._fit_measure_label = ctk.CTkLabel(self.word_row, text="", font=self._fit_measure_font)

        # Horizontal pan. When the widest chunk still spills past the reading
        # row even after the font has been shrunk to its floor, this pixel
        # offset is added to the centre anchor so the flash can be slid left or
        # right to bring the hidden part into view. Reset to centred (0) on each
        # load. The scrollbar below drives it and is packed in only while a
        # flash actually overflows; its travel is sized to the widest chunk, so
        # a position set once comfortably holds for the whole session.
        self._pan_offset_px = 0.0
        self._scrollbar_visible = False
        self._scrollbar = ctk.CTkScrollbar(
            self, orientation="horizontal", command=self._handle_scroll,
            button_color=EMBER_GLOW, button_hover_color=EMBER_GLOW_HOVER,
            fg_color="transparent",
        )

        # Not placed yet: _update_guide_marks() shows/positions them
        # only while a session is actively running.
        self.guide_mark_above = ctk.CTkFrame(
            self.word_row, width=self.GUIDE_MARK_THICKNESS, height=8,
            fg_color=self.DEFAULT_FONT_COLOR, corner_radius=0,
        )
        self.guide_mark_below = ctk.CTkFrame(
            self.word_row, width=self.GUIDE_MARK_THICKNESS, height=8,
            fg_color=self.DEFAULT_FONT_COLOR, corner_radius=0,
        )

        # Fixed-style horizontal ticks: a crosshair at the outer tip of
        # each vertical mark. Thickness and color are hardcoded constants
        # (see GUIDE_MARK_HORIZONTAL_* above); width is recomputed on
        # every resize/frame in _update_guide_marks() to track the
        # reading row's own width. The width given here is just a
        # placeholder until the first _update_guide_marks() call
        # reconfigures it.
        self.guide_line_above = ctk.CTkFrame(
            self.word_row, width=self.GUIDE_MARK_HORIZONTAL_MIN_LENGTH_PX, height=self.GUIDE_MARK_HORIZONTAL_THICKNESS_PX,
            fg_color=self.GUIDE_MARK_HORIZONTAL_COLOR, corner_radius=0,
        )
        self.guide_line_below = ctk.CTkFrame(
            self.word_row, width=self.GUIDE_MARK_HORIZONTAL_MIN_LENGTH_PX, height=self.GUIDE_MARK_HORIZONTAL_THICKNESS_PX,
            fg_color=self.GUIDE_MARK_HORIZONTAL_COLOR, corner_radius=0,
        )

        # Peripheral context ribbon labels: the current word centred under
        # the same anchor x as the focal word, flanked by dim previous and
        # upcoming words. Placed (or hidden) by _update_peripheral_context();
        # not shown at all until enabled. Uses a smaller font than the
        # reading word, sized as a fraction of it at update time.
        self.context_font = ctk.CTkFont(
            family=FONT_HEADING,
            size=max(8, round(self.DEFAULT_FONT_SIZE * self.PERIPHERAL_CONTEXT_SIZE_RATIO)),
        )
        self.context_before = ctk.CTkLabel(self.word_row, text="", font=self.context_font, text_color=self.DEFAULT_FONT_COLOR)
        self.context_current = ctk.CTkLabel(self.word_row, text="", font=self.context_font, text_color=self.DEFAULT_FONT_COLOR)
        self.context_after = ctk.CTkLabel(self.word_row, text="", font=self.context_font, text_color=self.DEFAULT_FONT_COLOR)

    def load_session(self, session: ReaderSession, start_paused: bool = False) -> None:
        self._cancel_pending()
        self.session = session
        self._is_paused = start_paused
        self._scrubbing = False
        self._session_words_read = 0
        self._session_active_seconds = 0.0
        self._active_span_start = None
        if not start_paused:
            self._start_active_span()
        self._pan_offset_px = 0.0
        self._recompute_fit_widest()
        self._apply_fit()
        self._update_scrollbar()
        self._show_current_frame()
        self._schedule_next()
        self._update_guide_marks()
        self._report_progress()

    def stop(self) -> None:
        self.finalize_session()
        self._cancel_pending()
        self.session = None
        self._is_paused = False
        self._scrubbing = False
        self._update_guide_marks()
        # Session is gone, so the ribbon (if it was showing) must clear too.
        self._update_peripheral_context()

    def finalize_session(self) -> None:
        """Report this session's accumulated words-read/active-time via
        on_session_stats (ultimately reaching
        core/transcript_store.py's add_session_stats(), through
        gui/app.py), then reset the per-session counters so a later
        call, whether from stop() below or from an external caller,
        never double-reports what's already been sent.

        Safe to call when nothing is loaded (self.session is None): a
        no-op, since Canvas.load_transcript() unconditionally calls
        stop() even before anything has ever been loaded. Also safe to
        call while a session is still actively playing: closes out
        whatever active span is currently open first (see
        _end_active_span()).

        This is split out from stop() specifically because gui/app.py's
        WM_DELETE_WINDOW close handler is the one real exit path that
        does not go through stop(), since quitting mid-read never
        explicitly stops playback first, the app is about to close
        anyway, so without a way to call just this part, closing the app
        while a transcript is actively running would silently lose that
        tail end of the session's stats."""
        if self.session is None:
            return
        self._end_active_span()
        if self.on_session_stats:
            self.on_session_stats(self._session_words_read, self._session_active_seconds)
        self._session_words_read = 0
        self._session_active_seconds = 0.0

    def toggle_pause(self) -> bool:
        if self.session is None or self.session.is_finished:
            return self._is_paused
        self._is_paused = not self._is_paused
        if self._is_paused:
            self._cancel_pending()
            self._end_active_span()
        else:
            # Resuming. If resume-rewind is on, step back a few words first
            # so reading re-enters with a little context rather than exactly
            # where it left off. seek() clamps at the first word, and the
            # top-of-method guard already ruled out a finished session, so
            # stepping back can never land past the end. The re-rendered
            # position is reported so the saved position matches where
            # reading actually resumed.
            if self._resume_rewind_enabled:
                self.session.seek(-self._resume_rewind_words)
                self._show_current_frame()
                self._report_position()
            self._schedule_next()
            self._start_active_span()
        self._update_guide_marks()
        return self._is_paused

    def restart(self) -> None:
        if self.session is None:
            return
        self._cancel_pending()
        self.session.reset()
        self._is_paused = False
        # restart() always leaves playback unpaused, whatever state it
        # was in before (playing, paused, or finished), so it always
        # needs an open active span afterward. _end_active_span() is a
        # no-op if one wasn't already open (the paused/finished cases);
        # for the already-playing case this is a same-instant close and
        # reopen, losing no real time.
        self._end_active_span()
        self._start_active_span()
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
        if force_pause and not self._is_paused:
            # Only an actual not-paused -> paused transition needs the
            # active span closed: if it was already paused, skip()
            # forcing "paused" again isn't a new transition, and the
            # span (if any) is already closed. This bypasses
            # toggle_pause() entirely (force_pause sets _is_paused
            # directly), so it needs this same bookkeeping on its own.
            self._is_paused = True
            self._end_active_span()
        if not self._is_paused:
            self._schedule_next()
        self._update_guide_marks()
        return self._is_paused

    def scrub_move(self, index: int) -> bool:
        """Live scrub to an absolute word index while the user drags the
        progress bar. Playback is held for the whole drag: the first move
        remembers whether reading was playing and closes the active span,
        and every move cancels any pending advance and shows the landed
        word, so the reader never advances under the moving thumb. The new
        position is reported so it's saved. Always returns paused (True)
        while dragging; scrub_end() decides the final state on release.
        Safe to call many times per drag."""
        if self.session is None:
            return self._is_paused
        if not self._scrubbing:
            self._scrubbing = True
            self._scrub_was_playing = not self._is_paused
            if not self._is_paused:
                self._is_paused = True
                self._end_active_span()
        self._cancel_pending()
        self.session.seek_to(index)
        self._show_current_frame()
        self._report_position()
        self._update_guide_marks()
        return self._is_paused

    def scrub_end(self) -> bool:
        """Called when the user lets go of the progress bar. If the
        "pause after scrubbing" setting is on, or reading wasn't playing
        when the drag began, it stays paused on the landed word; otherwise
        it resumes playing from there. A release with no preceding move
        (self._scrubbing still False, e.g. a click that didn't change the
        value) is a no-op. Returns the resulting paused state so the
        caller can sync its toolbar's play/pause button."""
        if self.session is None or not self._scrubbing:
            return self._is_paused
        self._scrubbing = False
        if self._scrub_pause_enabled or not self._scrub_was_playing or self.session.is_finished:
            self._is_paused = True
        else:
            self._is_paused = False
            self._start_active_span()
            self._schedule_next()
        self._update_guide_marks()
        return self._is_paused

    def jump_to(self, index: int) -> bool:
        """Jump the reader to an absolute word index and land paused there,
        used by bookmarks. Mirrors how a scrub release that pauses behaves:
        any pending advance is cancelled, the active-time span is closed if
        reading was playing, and the landed word is shown and its position
        reported. Returns the resulting paused state (always True) so the
        caller can sync its toolbar and persist the pause, the same shape
        as skip() and scrub_end()."""
        if self.session is None:
            return self._is_paused
        self._cancel_pending()
        if not self._is_paused:
            self._is_paused = True
            self._end_active_span()
        self.session.seek_to(index)
        self._show_current_frame()
        self._report_position()
        self._update_guide_marks()
        return self._is_paused

    def current_bookmark_target(self) -> tuple[int, str] | None:
        """The current word's index and a short snippet of the words around
        it, for creating a bookmark at the reader's current position.
        Returns None when there's no live word to bookmark (no session
        loaded, or the session has finished). The snippet reuses
        ReaderSession.peripheral_context(), the same surrounding-words
        helper the context ribbon uses."""
        if self.session is None or self.session.is_finished:
            return None
        context = self.session.peripheral_context(3, 3)
        snippet = " ".join([*context.before, context.current or "", *context.after]).strip()
        return self.session.index, snippet

    def set_wpm(self, wpm: int) -> None:
        if self.session:
            self.session.set_wpm(wpm)
            self._report_progress()  # a faster/slower rate changes the time remaining

    def set_length_pacing_enabled(self, enabled: bool) -> None:
        if self.session:
            self.session.set_length_pacing_enabled(enabled)
            self._report_progress()  # switches which estimate table is used

    def set_warm_up_enabled(self, enabled: bool) -> None:
        if self.session:
            self.session.set_warm_up_enabled(enabled)

    def set_chunking(self, enabled: bool, size: int, mode: str | None = None, char_target: int | None = None) -> None:
        """Re-group the current session with new chunking settings and refresh
        what's on screen, without restarting the session or disturbing its
        stats, pause state or word position. The session snaps the word index
        to its new chunk's start (see ReaderSession.set_chunking), so reading
        continues from the same place, just grouped differently, and the
        snapped position is reported so it's saved. While actually playing, the
        pending advance is cancelled and rescheduled against the new chunk's
        dwell, so a change made mid-flight takes effect from the current chunk
        forward; while paused, finished or mid-scrub the timing is left alone
        and the normal resume/scrub-end path picks up the new grouping.

        enabled and size always apply. mode and char_target are optional and
        passed straight through to ReaderSession.set_chunking, which keeps the
        session's current values when they are None, so the footer's two-arg
        call leaves the mode and adaptive width untouched while the
        Configure-chunking dialog passes them to switch mode or width. A no-op
        when no session is loaded."""
        if self.session is None:
            return
        self.session.set_chunking(enabled, size, mode, char_target)
        self._recompute_fit_widest()
        self._apply_fit()
        self._update_scrollbar()
        self._show_current_frame()
        self._report_position()
        if self._is_running() and not self._scrubbing:
            self._cancel_pending()
            self._schedule_next()
        self._update_guide_marks()

    def set_resume_rewind(self, enabled: bool, words: int) -> None:
        """Whether resuming from a pause first steps back `words` words for
        re-entry context, and by how many. Read at resume time in
        toggle_pause(); nothing changes about the currently displayed word
        until the next resume."""
        self._resume_rewind_enabled = enabled
        self._resume_rewind_words = words

    def set_scrub_pause(self, enabled: bool) -> None:
        """Whether releasing the progress scrubber pauses reading (on) or
        keeps its prior play state (off). Read at release time in
        scrub_end(); nothing changes about the current word until the next
        scrub is released."""
        self._scrub_pause_enabled = enabled

    def set_peripheral_context(self, enabled: bool, before: int = 1, after: int = 2) -> None:
        """Show or hide the peripheral context ribbon and set how many
        words flank the current one. Off by default. Read live: the ribbon
        redraws immediately, so this can be called any time, whether or not
        a session is loaded. Counts are clamped to >= 0."""
        self._peripheral_context_enabled = enabled
        self._peripheral_context_before = max(0, before)
        self._peripheral_context_after = max(0, after)
        self._update_peripheral_context()

    def set_colors(self, font_color: str, highlight_color: str, background_color: str) -> None:
        self._font_color = font_color
        self._background_color = background_color
        self.configure(fg_color=background_color)
        self.word_row.configure(fg_color=background_color)
        self.before_label.configure(text_color=font_color)
        self.after_label.configure(text_color=font_color)
        self.focus_label.configure(text_color=highlight_color)
        # Vertical guide marks are not touched here: their color is a
        # flat global value from Settings (see set_guide_mark_color()),
        # independent of the current transcript's font color, same as
        # the horizontal ticks are independent via a fixed constant.
        # The ribbon does follow the reading colours, dimmed, so refresh it.
        self._update_peripheral_context()

    def set_font_size(self, size: int) -> None:
        """Set the chosen Word size. The font is then rendered at the fitted
        size (never larger than this), so a wide chunk still fits the reading
        row; the chosen size is only stored here, never read back as the display
        size. The chunks are unchanged, so only the render size is re-derived,
        not the widest chunk."""
        self._chosen_font_size = size
        self._apply_fit()
        self._update_scrollbar()
        self._position_word()
        self._update_guide_marks()

    def set_highlight_offset(self, offset_px: int) -> None:
        """Shift only the highlighted (focus) letter vertically, relative
        to before/after which stay at the row's normal vertical center.
        Positive = up, negative = down, 0 = default.

        Guide marks track this too: their gap is measured from the
        letter's actual current top/bottom edge, so they keep a constant
        clearance from wherever the letter ends up rather than staying
        fixed at the un-offset center."""
        self._highlight_offset_px = offset_px
        self._position_word()
        self._update_guide_marks()

    def set_guide_mark_horizontal_enabled(self, enabled: bool) -> None:
        """Show/hide the horizontal crosshair ticks. This is the only
        configurable property they have. Thickness and color are
        fixed constants, and length is a constant derived from the
        reading row's own width (see GUIDE_MARK_HORIZONTAL_* and
        _guide_mark_horizontal_length())."""
        self._guide_mark_horizontal_enabled = enabled
        self._update_guide_marks()

    def set_guide_mark_thickness(self, thickness_px: int) -> None:
        """Width of the two vertical guide marks (above/below the
        highlighted letter). Stored and applied in _update_guide_marks()
        as an even physical-pixel width, rather than configured directly
        here, because a thin logical width scales to a fragile ~2px value
        that Tk fails to paint at fractional DPI such as 125%."""
        self._guide_mark_thickness_px = thickness_px
        self._update_guide_marks()

    def set_guide_mark_length_percent(self, percent: int) -> None:
        """Length of the two vertical guide marks, as a percentage of
        the current word-size font (e.g. 35 means 0.35 * font size).
        Kept as a ratio rather than a fixed px value unlike the
        horizontal ticks, which are deliberately fixed-style and
        window-relative, the vertical marks anchor the eye to the
        letter itself, so they're meant to keep growing and shrinking
        together with the Word Size setting."""
        self._guide_mark_length_ratio = percent / 100
        self._update_guide_marks()

    def set_guide_mark_color(self, color: str) -> None:
        """Color of the two vertical guide marks (above/below the
        highlighted letter). A flat global value from Settings: unlike
        before/after text and the highlight letter, these marks no
        longer follow the current transcript's font color (see
        set_colors())."""
        self.guide_mark_above.configure(fg_color=color)
        self.guide_mark_below.configure(fg_color=color)

    # Auto-fit: shrink the displayed font so the widest chunk fits the row,
    # without changing the chosen Word size.

    def _apply_fit(self) -> None:
        """Set the font's rendered size to the fitted size for the reading
        row's current width. Render-only: it changes what's on screen, never
        the chosen Word size. Cheap enough to call on every resize, since it
        reuses the widest-chunk measurement cached by _recompute_fit_widest()."""
        self.word_font.configure(size=self._fit_render_size())

    def _fit_render_size(self) -> int:
        """The size to actually render at: the chosen Word size when the widest
        chunk already fits, otherwise the largest size that does fit, down to
        the floor (FIT_FLOOR_RATIO of the chosen size). Falls back to the chosen
        size when there is nothing measured yet or the row has not been sized.
        The widest chunk's required width grows with the font size, so the
        stored width-per-size scales it: the size that just fits is
        usable_width / required_per_size."""
        chosen = self._chosen_font_size
        per_size = self._fit_required_per_size
        if per_size is None or per_size <= 0:
            return chosen
        usable = self.word_row.winfo_width() - 2 * self.FIT_SIDE_MARGIN_PX
        if usable <= 1:
            return chosen  # row not sized yet; the resize handler refits later
        floor = max(8, round(chosen * self.FIT_FLOOR_RATIO))
        fit = int(usable / per_size)
        return max(floor, min(chosen, fit))

    def _recompute_fit_widest(self) -> None:
        """Find the chunk that needs the most horizontal room and remember how
        wide it is per unit of font size, so _fit_render_size() can size the
        font to it. Done only when the chunks change (a load or a re-group),
        not on a resize or a plain size nudge. Character length is a close but
        imperfect stand-in for rendered width (wide and narrow letters differ),
        so this shortlists the longest chunks by characters and then measures
        those few in real pixels, keeping the widest."""
        self._fit_widest = None
        self._fit_required_per_size = None
        self._fit_left_reach_per_size = None
        self._fit_right_reach_per_size = None
        if self.session is None:
            return
        texts = self.session.chunk_texts()
        if not texts:
            return
        candidates = sorted(texts, key=lambda t: max(len(t[0]), len(t[2])), reverse=True)
        widest = None
        widest_reaches = (0.0, 0.0)
        widest_width = -1.0
        for before, focus, after in candidates[:self.FIT_WIDEST_CANDIDATES]:
            left_reach, right_reach = self._measure_reaches(self._chosen_font_size, before, focus, after)
            width = 2 * max(left_reach, right_reach)
            if width > widest_width:
                widest_width = width
                widest = (before, focus, after)
                widest_reaches = (left_reach, right_reach)
        if widest is None or self._chosen_font_size <= 0:
            return
        self._fit_widest = widest
        self._fit_required_per_size = widest_width / self._chosen_font_size
        self._fit_left_reach_per_size = widest_reaches[0] / self._chosen_font_size
        self._fit_right_reach_per_size = widest_reaches[1] / self._chosen_font_size

    def _measure_reaches(self, size: int, before: str, focus: str, after: str) -> tuple[float, float]:
        """How far a chunk reaches left and right of the centre anchor at a given
        font size, in real pixels. The flash is centred on the ORP letter, not on
        the chunk's middle, so the left reach is the before part plus half the
        focus letter and the right reach is the trailing after part plus half the
        focus letter. The reading row must hold twice the larger of the two, and
        each side's reach is what the scrollbar needs to know its overflow. Each
        part is measured on its own off-screen label, the same way the three
        visible labels are sized, so the measurement matches what gets drawn."""
        self._fit_measure_font.configure(size=size)
        widths = []
        for text in (before, focus, after):
            self._fit_measure_label.configure(text=text)
            self._fit_measure_label.update_idletasks()
            widths.append(self._fit_measure_label.winfo_reqwidth())
        before_w, focus_w, after_w = widths
        return before_w + focus_w / 2, after_w + focus_w / 2

    # Horizontal scroll: a bottom scrollbar that pans the flash sideways when
    # the widest chunk still overflows the row after the font has been fitted.

    def _widest_reaches(self) -> tuple[float, float]:
        """How far the widest chunk reaches left and right of the centre anchor
        at the current render size, in real pixels. Scaled from the per-size
        reaches cached by _recompute_fit_widest(), so it is pure arithmetic with
        no measuring, cheap to call on every resize. Returns (0, 0) when there
        is no widest chunk yet."""
        left_per = self._fit_left_reach_per_size
        right_per = self._fit_right_reach_per_size
        if left_per is None or right_per is None:
            return 0.0, 0.0
        size = self.word_font.cget("size")
        return left_per * size, right_per * size

    def _pan_overflows(self) -> tuple[float, float, float]:
        """The (overflow_left, overflow_right, viewport) that drive the pan: how
        far the widest chunk spills past each edge of the reading row at the
        current render size, and the row's usable width. Both overflows are 0
        when the widest chunk fits, which is the usual case once the font has
        been fitted; they go positive only when even the floor size still leaves
        the chunk wider than the row."""
        usable = self.word_row.winfo_width() - 2 * self.FIT_SIDE_MARGIN_PX
        if usable <= 1:
            return 0.0, 0.0, 0.0
        left_reach, right_reach = self._widest_reaches()
        half = usable / 2
        return max(0.0, left_reach - half), max(0.0, right_reach - half), usable

    def _update_scrollbar(self) -> None:
        """Show the horizontal scrollbar only while the widest chunk still spills
        past the reading row after fitting, size its thumb to how much overflows,
        and keep the pan offset clamped to what there is to reveal. When nothing
        overflows the pan is reset to centred and the scrollbar is removed, so it
        never lingers once a narrower grouping or a smaller font makes everything
        fit again."""
        overflow_left, overflow_right, usable = self._pan_overflows()
        if overflow_left + overflow_right <= 0:
            self._pan_offset_px = 0.0
            if self._scrollbar_visible:
                self._scrollbar.pack_forget()
                self._scrollbar_visible = False
            return
        self._pan_offset_px = clamp_pan(self._pan_offset_px, overflow_left, overflow_right)
        first, last = scrollbar_fractions(usable, overflow_left, overflow_right, self._pan_offset_px)
        self._scrollbar.set(first, last)
        if not self._scrollbar_visible:
            self._scrollbar.pack(side="bottom", fill="x", before=self.word_row)
            self._scrollbar_visible = True

    def _handle_scroll(self, *args) -> None:
        """The scrollbar's Tk command. A drag sends ("moveto", fraction); an
        arrow or trough click sends ("scroll", amount, "units"|"pages"). Both
        become a new pan offset that slides the flash and re-syncs the thumb.
        Scrolling right (a positive amount) reveals content that spilled off the
        right, which is a leftward slide of the flash, i.e. a more negative pan."""
        overflow_left, overflow_right, usable = self._pan_overflows()
        if overflow_left + overflow_right <= 0:
            return
        if args and args[0] == "moveto":
            self._pan_offset_px = pan_from_fraction(float(args[1]), usable, overflow_left, overflow_right)
        elif args and args[0] == "scroll":
            amount = int(args[1])
            what = args[2] if len(args) > 2 else "units"
            step = usable if what == "pages" else self.SCROLL_UNIT_PX
            self._pan_offset_px = clamp_pan(self._pan_offset_px - amount * step, overflow_left, overflow_right)
        else:
            return
        self._position_word()
        self._update_guide_marks()
        self._update_scrollbar()

    def _show_current_frame(self) -> None:
        if self.session is None:
            return
        if self.session.is_finished:
            self.before_label.configure(text="(finished)")
            self.focus_label.configure(text="")
            self.after_label.configure(text="")
        else:
            # The chunk currently on screen, assembled the one shared way (see
            # core.reader.assemble_chunk_text): with chunking off this is a
            # single word, and in a chunk only the first word keeps its ORP
            # split and anchored highlight while the rest trail to its right in
            # the after-label. Using the same assembler the font-fit measures
            # keeps the drawn chunk and the measured chunk identical.
            before, focus, after = assemble_chunk_text(self.session.current_chunk())
            self.before_label.configure(text=before)
            self.focus_label.configure(text=focus)
            self.after_label.configure(text=after)
        self._position_word()

    def _place_physical(self, widget, *, x, y, anchor) -> None:
        """place() a child of word_row at a position expressed in real
        on-screen pixels: the same space winfo_width()/winfo_height()
        report, which is what all our anchor math is computed in.

        CustomTkinter's CTkBaseClass.place() silently multiplies x/y by
        the widget's DPI scaling factor before handing them to real
        Tkinter (see customtkinter's ctk_base_class.py place() and
        scaling_base_class.py's _apply_argument_scaling()). Since our
        x/y here are already real physical pixels (derived from
        winfo_width()/winfo_reqwidth(), which report post-scaling
        sizes), passing them to .place() directly gets them scaled a
        second time, which on a 200%-scaled display pushes every word
        roughly twice as far right/down as intended, off the visible
        edge.

        Dividing by that same factor here via CTk's own
        _reverse_widget_scaling() (the exact inverse it uses internally)
        cancels the doubling out, so the widget lands at the physical
        position we actually computed. Every place() call in this file
        must go through this method: calling .place(x=, y=) directly on
        a child of word_row will reintroduce this bug on any
        a child of word_row will reintroduce this bug on any
        non-100%-scaled display.
        """
        widget.place(
            x=self._reverse_widget_scaling(x),
            y=self._reverse_widget_scaling(y),
            anchor=anchor,
        )

    def _configure_physical_height(self, widget, height) -> None:
        """Height counterpart to _configure_physical_width: sets a CTk
        widget's height in real physical pixels, cancelling CTk's DPI
        auto-scaling the same way. Used for the horizontal ticks' thickness,
        which otherwise scales to a fragile ~2px value that Tk fails to paint
        at fractional DPI such as 125%."""
        widget.configure(height=self._reverse_widget_scaling(height))

    def _configure_physical_width(self, widget, width) -> None:
        """configure(width=...) on a CTk widget applies the exact same
        DPI auto-scaling that _place_physical() above has to cancel for
        x/y: setting width=1412 (a physical-pixel value, computed from
        winfo_width()) renders an actual on-screen width of 2824, exactly
        double, on a 200%-scaled display. Dividing by the same factor
        here cancels that out, the same way _place_physical does for
        position. Use this instead of widget.configure(width=) directly
        whenever the width being set was computed from
        winfo_width()/winfo_reqwidth() (i.e. is already physical) rather
        than being a plain logical constant like GUIDE_MARK_THICKNESS.
        """
        widget.configure(width=self._reverse_widget_scaling(width))

    def _position_word(self) -> None:
        """Places before/focus/after so the focus letter's horizontal
        center always lands at the row's fixed center x. Recomputed on
        every frame, since both the word's text and the font size can
        change the letter's rendered width, and on resize."""
        self.word_row.update_idletasks()
        row_width = self.word_row.winfo_width()
        row_height = self.word_row.winfo_height()
        if row_width <= 1 or row_height <= 1:
            return  # not yet mapped/sized, nothing sensible to compute

        center_x = row_width / 2
        center_y = row_height / 2
        # Positive offset = up = smaller y.
        focus_y = center_y - self._highlight_offset_px

        if self.session is not None and self.session.is_finished:
            # No ORP letter to anchor around here: before_label holds
            # the whole "(finished)" message with focus/after emptied.
            # The normal anchor="e" placement below assumes an actual
            # focus_width to butt up against; with that width near 0 it
            # left the message sitting to the left of center instead of
            # centered on it. Center it directly instead. The pan offset
            # is deliberately not applied: "(finished)" is short and never
            # overflows, so it stays on the centre line rather than sliding
            # with a pan left over from the last wide chunk.
            self.focus_label.place_forget()
            self.after_label.place_forget()
            self._place_physical(self.before_label, x=center_x, y=center_y, anchor="center")
            self._anchor_x = center_x
            self._focus_y = focus_y
            self._focus_half_height = 0
            self._row_width = row_width
            # Finished: peripheral_context has no current word, so this
            # clears the ribbon.
            self._update_peripheral_context()
            return

        # The live flash is anchored at the row centre plus the current pan, so
        # a chunk too wide for the row can be slid sideways into view. The pan
        # is 0 (centred) unless the widest chunk overflows and the user has
        # dragged the scrollbar; see _update_scrollbar().
        anchor_x = center_x + self._pan_offset_px
        focus_width = self.focus_label.winfo_reqwidth()
        focus_height = self.focus_label.winfo_reqheight()

        self._place_physical(self.before_label, x=anchor_x - focus_width / 2, y=center_y, anchor="e")
        self._place_physical(self.focus_label, x=anchor_x, y=focus_y, anchor="center")
        self._place_physical(self.after_label, x=anchor_x + focus_width / 2, y=center_y, anchor="w")

        self._anchor_x = anchor_x
        self._focus_y = focus_y
        self._focus_half_height = focus_height / 2
        self._row_width = row_width

        # Redraw the context ribbon against the freshly placed word. This
        # single call at the end of _position_word() covers every case
        # that moves or re-renders the word (load, advance, skip, scrub,
        # restart, resume-rewind, resize, font size, highlight offset),
        # since they all route through here.
        self._update_peripheral_context()

    def _update_guide_marks(self) -> None:
        if not self._is_running() or self._anchor_x is None:
            self.guide_mark_above.place_forget()
            self.guide_mark_below.place_forget()
            self.guide_line_above.place_forget()
            self.guide_line_below.place_forget()
            return

        length = self._guide_mark_length()
        gap = self.GUIDE_MARK_MIN_GAP_PX
        # Width is set as an even physical-pixel value with a floor, not a
        # plain logical configure(width=). The default thickness of 2 scales
        # to about 2 physical px at 125% DPI, which Tk's canvas fails to paint
        # (the marks vanish), while 150% lands on ~3px and shows. The draw
        # engine also floors width to an even number, so the floor is kept
        # even. The horizontal ticks already size themselves physically for
        # the same reason.
        scale = self._get_widget_scaling()
        mark_width = max(4, round(self._guide_mark_thickness_px * scale / 2) * 2)
        self._configure_physical_width(self.guide_mark_above, mark_width)
        self._configure_physical_width(self.guide_mark_below, mark_width)
        self.guide_mark_above.configure(height=length)
        self.guide_mark_below.configure(height=length)

        # Inner edge = nearest the letter, where each vertical mark
        # starts. Outer edge = its far tip, where the matching
        # horizontal tick sits, forming a crosshair.
        inner_top_y = self._focus_y - self._focus_half_height - gap
        inner_bottom_y = self._focus_y + self._focus_half_height + gap
        # The vertical marks render at length * scale physical px tall (their
        # height is a logical value CTk scales up), so the tick that caps each
        # one must sit length * scale away, not an unscaled length, or on a
        # scaled display it lands partway down the mark instead of at the tip.
        outer_top_y = inner_top_y - length * scale
        outer_bottom_y = inner_bottom_y + length * scale

        self._place_physical(self.guide_mark_above, x=self._anchor_x, y=inner_top_y, anchor="s")
        self._place_physical(self.guide_mark_below, x=self._anchor_x, y=inner_bottom_y, anchor="n")

        if self._guide_mark_horizontal_enabled:
            horizontal_length = self._guide_mark_horizontal_length()
            # Thickness gets the same even physical-pixel floor the vertical
            # marks' width does: a 2px-tall tick scales to a fragile value that
            # Tk fails to paint at 125% DPI (the ticks vanish into the
            # background), so it's forced to an even physical height of 4.
            tick_thickness = max(4, round(self.GUIDE_MARK_HORIZONTAL_THICKNESS_PX * scale / 2) * 2)
            self._configure_physical_width(self.guide_line_above, horizontal_length)
            self._configure_physical_width(self.guide_line_below, horizontal_length)
            self._configure_physical_height(self.guide_line_above, tick_thickness)
            self._configure_physical_height(self.guide_line_below, tick_thickness)
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

    def _update_peripheral_context(self) -> None:
        """Draw the dim context ribbon below the focal word: the current
        word centred under the same anchor x, with up to a few previous
        words to its left and upcoming words to its right, all dimmed
        toward the background. Off unless enabled, and hidden whenever
        there's no word on screen (no session, not yet sized, or
        finished). It sits below the farthest point a guide mark can reach,
        plus its own half-height and a margin, so the two never overlap
        whether or not the marks are currently shown."""
        if (not self._peripheral_context_enabled
                or self.session is None
                or self._anchor_x is None):
            self._hide_peripheral_context()
            return
        # Context around the whole current chunk (before its first word, after
        # its last). With chunking off a chunk is one word, so this matches the
        # plain word-centered context.
        context = self.session.chunk_peripheral_context(
            self._peripheral_context_before, self._peripheral_context_after
        )
        if context.current is None:
            self._hide_peripheral_context()
            return

        dim_color = blend_colors(self._font_color, self._background_color, self.PERIPHERAL_CONTEXT_DIM)
        size = max(8, round(self.word_font.cget("size") * self.PERIPHERAL_CONTEXT_SIZE_RATIO))
        self.context_font.configure(size=size)

        before_text = " ".join(context.before)
        after_text = " ".join(context.after)
        self.context_current.configure(text=context.current, text_color=dim_color)
        self.context_before.configure(text=before_text, text_color=dim_color)
        self.context_after.configure(text=after_text, text_color=dim_color)

        # The lowest point a guide mark can reach (its outer tip),
        # computed the same way _update_guide_marks() does, so the ribbon
        # clears it even when the marks are hidden (paused).
        gap = self.GUIDE_MARK_MIN_GAP_PX
        outer_bottom_y = self._focus_y + self._focus_half_height + gap + self._guide_mark_length()

        self.context_current.update_idletasks()
        current_width = self.context_current.winfo_reqwidth()
        current_height = self.context_current.winfo_reqheight()
        ribbon_y = outer_bottom_y + current_height / 2 + self.PERIPHERAL_CONTEXT_TOP_MARGIN_PX

        self._place_physical(self.context_current, x=self._anchor_x, y=ribbon_y, anchor="center")

        word_gap = self.PERIPHERAL_CONTEXT_WORD_GAP_PX
        if before_text:
            self._place_physical(
                self.context_before, x=self._anchor_x - current_width / 2 - word_gap,
                y=ribbon_y, anchor="e",
            )
        else:
            self.context_before.place_forget()
        if after_text:
            self._place_physical(
                self.context_after, x=self._anchor_x + current_width / 2 + word_gap,
                y=ribbon_y, anchor="w",
            )
        else:
            self.context_after.place_forget()

    def _hide_peripheral_context(self) -> None:
        self.context_before.place_forget()
        self.context_current.place_forget()
        self.context_after.place_forget()

    def _is_running(self) -> bool:
        return self.session is not None and not self.session.is_finished and not self._is_paused

    def _handle_row_resized(self, event=None) -> None:
        # A wider or narrower row changes how much the font can fill, so refit
        # before repositioning. The widest chunk is unchanged by a resize, so
        # this only re-derives the render size, it does not re-scan the chunks.
        self._apply_fit()
        self._update_scrollbar()
        self._position_word()
        self._update_guide_marks()

    def _schedule_next(self) -> None:
        if self.session is None or self.session.is_finished or self._is_paused:
            self._after_id = None
            return
        # Schedule by the current chunk's dwell: the sum of its words' delays.
        # With chunking off a chunk is one word, so this equals the single
        # word's delay and the timing is unchanged.
        delay = self.session.current_chunk_delay_ms()
        self._after_id = self.after(delay, self._advance)

    def _advance(self) -> None:
        if self.session is None:
            return
        # advance() steps a whole chunk (one word with chunking off). Count the
        # words actually passed, the move in the index, so stats stay word-based.
        before_index = self.session.index
        self.session.advance()
        self._session_words_read += self.session.index - before_index
        if self.session.is_finished:
            # Reading has genuinely stopped here, even though nothing
            # set _is_paused. Close the active span now rather than
            # leaving it open and silently counting whatever idle time
            # passes before the user eventually navigates away or
            # closes the app.
            self._end_active_span()
        self._show_current_frame()
        self._report_position()
        self._schedule_next()
        self._update_guide_marks()

    def _report_position(self) -> None:
        if self.on_position_changed and self.session:
            self.on_position_changed(self.session.index)
        # Progress read-outs move with the position, so they're reported
        # from the same points. Kept as its own guarded call (not gated on
        # on_position_changed) so a reader with only on_progress still
        # updates.
        self._report_progress()

    def _report_progress(self) -> None:
        """Push estimated time remaining and progress percent to on_progress,
        for the reader's read-outs. Called wherever the position or the
        estimate changes (advancing, seeking, scrubbing, resuming with
        rewind, restarting, loading, and on a WPM or length-pacing change).
        Percent is the current word's position through the transcript, 100
        once finished."""
        if self.on_progress is None or self.session is None:
            return
        total = self.session.total_words
        percent = max(0, min(100, round(100 * self.session.index / total))) if total else 0
        self.on_progress(self.session.remaining_ms(), percent)

    def _start_active_span(self) -> None:
        self._active_span_start = time.monotonic()

    def _end_active_span(self) -> None:
        if self._active_span_start is not None:
            self._session_active_seconds += time.monotonic() - self._active_span_start
            self._active_span_start = None

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None