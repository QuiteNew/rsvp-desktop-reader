import customtkinter as ctk

from gui.theme import EMBER_GLOW, EMBER_GLOW_HOVER, WARM_LINE, COCOA_INK, FONT_BODY


class ScrubBar(ctk.CTkFrame):
    """A reading-position slider with a "word X of Y" read-out, shown in
    the reader's control row.

    The read-out sits on its own line directly above the slider, so the
    whole bar is only as wide as the slider itself. It used to sit inline
    to the slider's right, which added roughly 120px to the bar's width
    and, once the toolbar grew its own time and percent read-out pills,
    crowded them off the edge at the default window size. Stacking
    reclaims that width. See gui/components/canvas.py's three-column
    control row for the layout this feeds into.

    Below the slider is a thin strip of bookmark ticks: one short mark per
    saved bookmark, placed under the exact spot the thumb comes to rest at
    that word. The strip is a separate row beneath the slider rather than
    an overlay on top of it, specifically so the tick widgets can never sit
    over the slider and swallow a drag. Owners push the index list in with
    set_bookmarks(); this widget stays otherwise unaware of what a bookmark
    is. See _redraw_ticks()/_thumb_inset() for the alignment math.

    It plays two roles at once, which is the whole reason for the guard
    flag below. As reading advances, its owner calls set_position() to
    walk the thumb along on its own; when the user drags the thumb, the
    slider reports the landed word through on_scrub so the owner can seek
    there. Without a guard, a programmatic set_position() could be taken
    for a user drag and fire on_scrub straight back, fighting itself, so
    set_position() raises _syncing around the slider.set() call and the
    slider's own callback ignores anything that arrives while it's up.

    Colours come from the theme tokens (EMBER_GLOW / WARM_LINE / COCOA_
    INK), which gui/theme.py resolves to the active appearance once at
    import time, so the bar matches whichever theme the app launched in,
    exactly like the WPM slider in the footer it mirrors.

    The slider's range is 0 .. total_words - 1, one stop per word. A
    transcript with fewer than two words has nothing to scrub, so the
    slider is disabled and only the read-out is shown."""

    SLIDER_WIDTH = 220
    TICK_STRIP_HEIGHT = 6     # px, logical. Always present so the bar's height
                              # doesn't jump as bookmarks come and go.
    BOOKMARK_TICK_WIDTH = 2   # px, logical
    BOOKMARK_TICK_HEIGHT = 5  # px, logical

    def __init__(self, master, on_scrub=None, on_scrub_release=None):
        super().__init__(master, fg_color="transparent")
        self.on_scrub = on_scrub
        self.on_scrub_release = on_scrub_release
        self._total = 0
        # Raised only while set_position() drives the slider itself, so
        # _handle_slide() can tell a programmatic move from a real drag.
        self._syncing = False
        # Current bookmark word indices, and the live tick widgets drawn
        # for them. See set_bookmarks()/_redraw_ticks().
        self._bookmark_indices = []
        self._tick_widgets = []

        self.slider = ctk.CTkSlider(
            self, from_=0, to=1, width=self.SLIDER_WIDTH,
            progress_color=EMBER_GLOW, button_color=EMBER_GLOW,
            button_hover_color=EMBER_GLOW_HOVER, fg_color=WARM_LINE,
            command=self._handle_slide,
        )
        # A real "let go" event, which the command callback alone can't
        # give. CTkSlider.bind forwards to its inner canvas and preserves
        # CTk's own <ButtonRelease-1> handling (add="+"). Used to decide,
        # once per drag, whether to pause or resume (see on_scrub_release).
        self.slider.bind("<ButtonRelease-1>", self._handle_release, add="+")

        self.readout = ctk.CTkLabel(
            self, text="", text_color=COCOA_INK,
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            anchor="center",
        )

        # Fixed-size strip for bookmark ticks, sitting directly under the
        # slider with its left edge aligned to the slider's (both anchor
        # "w", same width). pack_propagate(False) keeps the strip at its
        # set height even while it holds only place()'d children, so an
        # empty strip (no bookmarks) still reserves the same space and the
        # bar's overall height stays constant.
        self.tick_strip = ctk.CTkFrame(
            self, fg_color="transparent",
            width=self.SLIDER_WIDTH, height=self.TICK_STRIP_HEIGHT,
        )
        self.tick_strip.pack_propagate(False)

        # Read-out on top, centred over the slider; slider beneath it, then
        # the tick strip. Packing order sets the vertical order for
        # side="top", so the label is packed first even though the slider
        # is created first. fill="x" lets the label span the bar's width so
        # anchor="center" centres the word count over the slider rather
        # than parking it at one end. The small gap keeps the taller,
        # multi-line bar from feeling cramped against the control row above.
        self.readout.pack(side="top", fill="x", pady=(0, 3))
        self.slider.pack(side="top", anchor="w")
        self.tick_strip.pack(side="top", anchor="w")

        self.clear()

    def set_total(self, total: int) -> None:
        """Set how many words this session has, sizing the slider's range
        and resetting the thumb to the first word. Call this each time a
        new reading session is loaded, before set_position(). Bookmark
        ticks are cleared here too, since they belong to whatever session
        is leaving; the owner re-supplies them with set_bookmarks() right
        after."""
        self._total = max(0, total)
        if self._total < 2:
            # Nothing to scrub: a single word (or none). Park the slider
            # at the start and disable it, leaving just the read-out.
            self.slider.configure(from_=0, to=1, state="disabled")
        else:
            self.slider.configure(from_=0, to=self._total - 1, state="normal")
        self._set_slider_value(0)
        self._update_readout(0)
        self._bookmark_indices = []
        self._redraw_ticks()

    def set_position(self, index: int) -> None:
        """Move the thumb to an absolute word index without firing
        on_scrub, so the bar reflects wherever the reader actually is as
        it advances or after a seek."""
        if self._total <= 0:
            return
        # A finished session reports index == total_words; the thumb has
        # no stop past the last word, so it comes to rest on the last one.
        clamped = max(0, min(index, self._total - 1))
        self._set_slider_value(clamped)
        self._update_readout(index)

    def set_bookmarks(self, indices) -> None:
        """Set which word indices show a bookmark tick. Deduped, sorted,
        and clamped to >= 0; indices past the last word are simply drawn at
        the end by _redraw_ticks()'s own clamp. Call after set_total(), and
        again whenever bookmarks are added or removed."""
        self._bookmark_indices = sorted({max(0, int(i)) for i in indices})
        self._redraw_ticks()

    def clear(self) -> None:
        """Blank, disabled state for when no session is loaded (e.g. the
        edit box is showing instead of the reader)."""
        self._total = 0
        self.slider.configure(from_=0, to=1, state="disabled")
        self._set_slider_value(0)
        self.readout.configure(text="")
        self._bookmark_indices = []
        self._redraw_ticks()

    def _set_slider_value(self, value) -> None:
        self._syncing = True
        try:
            self.slider.set(value)
        finally:
            self._syncing = False

    def _handle_slide(self, value) -> None:
        if self._syncing or self._total < 2:
            return
        index = max(0, min(int(round(value)), self._total - 1))
        self._update_readout(index)
        if self.on_scrub:
            self.on_scrub(index)

    def _handle_release(self, event=None) -> None:
        if self._total < 2:
            return
        if self.on_scrub_release:
            self.on_scrub_release()

    def _update_readout(self, index: int) -> None:
        if self._total <= 0:
            self.readout.configure(text="")
            return
        shown = max(1, min(index + 1, self._total))
        self.readout.configure(text=f"word {shown:,} of {self._total:,}")

    def _thumb_inset(self) -> float:
        """How far the thumb's center sits from each end of the slider: on
        a default round-knob CTkSlider the center travels between this inset
        and width - inset, never reaching the literal edges. It's the knob
        radius, which for the default styling is half the slider's height.
        Read from the slider itself so it tracks the theme's height rather
        than hardcoding a number that could drift."""
        try:
            height = float(self.slider.cget("height"))
        except (ValueError, TypeError):
            height = 16.0
        return height / 2 if height else 8.0

    def _redraw_ticks(self) -> None:
        """Rebuild the bookmark tick marks. Every coordinate here is in
        logical units (the SLIDER_WIDTH constant and the height-derived
        inset), so plain place() scales them once to physical pixels and
        the ticks line up on any DPI, unlike geometry computed from
        winfo_width() which would be pre-scaled and double up. Nothing is
        drawn when there's nothing to scrub (fewer than two words) or no
        bookmarks."""
        for tick in self._tick_widgets:
            tick.destroy()
        self._tick_widgets = []

        if self._total < 2 or not self._bookmark_indices:
            return

        inset = self._thumb_inset()
        usable = self.SLIDER_WIDTH - 2 * inset
        if usable <= 0:
            return

        for index in self._bookmark_indices:
            clamped = max(0, min(index, self._total - 1))
            fraction = clamped / (self._total - 1)
            x = inset + fraction * usable
            tick = ctk.CTkFrame(
                self.tick_strip,
                width=self.BOOKMARK_TICK_WIDTH, height=self.BOOKMARK_TICK_HEIGHT,
                fg_color=EMBER_GLOW, corner_radius=0,
            )
            tick.place(x=x, y=0, anchor="n")
            self._tick_widgets.append(tick)