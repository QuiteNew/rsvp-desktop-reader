import customtkinter as ctk

from gui.theme import EMBER_GLOW, EMBER_GLOW_HOVER, WARM_LINE, COCOA_INK, FONT_BODY


class ScrubBar(ctk.CTkFrame):
    """A reading-position slider with a "word X of Y" read-out, shown in
    the reader's control row.

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

    def __init__(self, master, on_scrub=None, on_scrub_release=None):
        super().__init__(master, fg_color="transparent")
        self.on_scrub = on_scrub
        self.on_scrub_release = on_scrub_release
        self._total = 0
        # Raised only while set_position() drives the slider itself, so
        # _handle_slide() can tell a programmatic move from a real drag.
        self._syncing = False

        self.slider = ctk.CTkSlider(
            self, from_=0, to=1, width=self.SLIDER_WIDTH,
            progress_color=EMBER_GLOW, button_color=EMBER_GLOW,
            button_hover_color=EMBER_GLOW_HOVER, fg_color=WARM_LINE,
            command=self._handle_slide,
        )
        self.slider.pack(side="left")
        # A real "let go" event, which the command callback alone can't
        # give. CTkSlider.bind forwards to its inner canvas and preserves
        # CTk's own <ButtonRelease-1> handling (add="+"). Used to decide,
        # once per drag, whether to pause or resume (see on_scrub_release).
        self.slider.bind("<ButtonRelease-1>", self._handle_release, add="+")

        self.readout = ctk.CTkLabel(
            self, text="", text_color=COCOA_INK,
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            width=110, anchor="w",
        )
        self.readout.pack(side="left", padx=(10, 0))

        self.clear()

    def set_total(self, total: int) -> None:
        """Set how many words this session has, sizing the slider's range
        and resetting the thumb to the first word. Call this each time a
        new reading session is loaded, before set_position()."""
        self._total = max(0, total)
        if self._total < 2:
            # Nothing to scrub: a single word (or none). Park the slider
            # at the start and disable it, leaving just the read-out.
            self.slider.configure(from_=0, to=1, state="disabled")
        else:
            self.slider.configure(from_=0, to=self._total - 1, state="normal")
        self._set_slider_value(0)
        self._update_readout(0)

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

    def clear(self) -> None:
        """Blank, disabled state for when no session is loaded (e.g. the
        edit box is showing instead of the reader)."""
        self._total = 0
        self.slider.configure(from_=0, to=1, state="disabled")
        self._set_slider_value(0)
        self.readout.configure(text="")

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