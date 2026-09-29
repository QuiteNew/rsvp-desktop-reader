import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay
from gui.components.canvas_toolbar import CanvasToolbar
from gui.components.scrub_bar import ScrubBar
from gui.theme import apply_app_icon, center_over_parent, HEARTH_PAPER


class DetachedTranscriptWindow(ctk.CTkToplevel):
    """A standalone window showing one transcript, separate from the main app window."""

    def __init__(
        self, master, transcript, on_text_submitted, on_closed,
        on_position_changed=None, on_pause_changed=None, on_stopped_changed=None,
        on_session_stats=None, on_normalization_changed=None,
        initial_draft_text="",
        skip_word_count: int = 10, pause_on_skip: bool = False,
        length_pacing_enabled: bool = False,
        split_long_paragraphs_enabled: bool = False,
        resume_rewind_enabled: bool = False,
        resume_rewind_words: int = 3,
        warm_up_enabled: bool = False,
        scrub_pause_enabled: bool = True,
        highlight_offset_px: int = 0,
        guide_mark_horizontal_enabled: bool = False,
        guide_mark_thickness_px: int = 2,
        guide_mark_length_percent: int = 35,
        guide_mark_color: str = "#3B2E27",
    ):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # end of __init__, and gui/components/settings_window.py for the
        # fuller explanation of why this uses -alpha rather than
        # withdraw()/deiconify()).
        self.attributes("-alpha", 0)

        self.transcript = transcript
        self.on_text_submitted = on_text_submitted
        self.on_closed = on_closed
        self.on_position_changed = on_position_changed
        self.on_pause_changed = on_pause_changed
        self.on_stopped_changed = on_stopped_changed
        self.on_normalization_changed = on_normalization_changed
        self.on_session_stats = on_session_stats
        self.skip_word_count = skip_word_count
        self.pause_on_skip = pause_on_skip
        self.length_pacing_enabled = length_pacing_enabled
        self.split_long_paragraphs_enabled = split_long_paragraphs_enabled
        self.warm_up_enabled = warm_up_enabled
        self.scrub_pause_enabled = scrub_pause_enabled

        self.title(transcript.title)
        apply_app_icon(self)
        center_over_parent(self, 500, 350)
        self.protocol("WM_DELETE_WINDOW", self.close)
        # Previously unset: CTkToplevel's own default theme background
        # doesn't match this app's palette, so without this the window
        # showed a mismatched background wherever the toolbar/input/
        # reader widgets below don't fully cover it.
        self.configure(fg_color=HEARTH_PAPER)

        # The control row mirrors the main window: the scrubber sits on
        # the left, the toolbar hugs the right. Packed as a unit in
        # _render_current_state()'s reader branch.
        self.control_row = ctk.CTkFrame(self, fg_color="transparent")
        self.scrub_bar = ScrubBar(
            self.control_row, on_scrub=self._handle_scrub, on_scrub_release=self._handle_scrub_release,
        )
        self.scrub_bar.pack(side="left")
        self.toolbar = CanvasToolbar(
            self.control_row,
            on_skip_back=self._handle_skip_back,
            on_skip_forward=self._handle_skip_forward,
            on_pause_toggle=self._handle_pause_toggle,
            on_restart=self._handle_restart,
            show_skip=True,
            show_maximize=False,
            show_detach=False,
            show_progress=True,
        )
        self.toolbar.pack(side="right")

        self.input_view = TranscriptInput(
            self, on_submit=self._handle_text_submitted, initial_text=initial_draft_text,
            on_normalized=self._handle_normalized, split_long_paragraphs=split_long_paragraphs_enabled,
        )
        self.reader_display = ReaderDisplay(
            self,
            on_position_changed=self._handle_position_changed,
            on_session_stats=self._handle_session_stats,
            on_progress=self._handle_progress,
        )
        self.reader_display.set_highlight_offset(highlight_offset_px)
        self.reader_display.set_guide_mark_horizontal_enabled(guide_mark_horizontal_enabled)
        self.reader_display.set_guide_mark_thickness(guide_mark_thickness_px)
        self.reader_display.set_guide_mark_length_percent(guide_mark_length_percent)
        self.reader_display.set_guide_mark_color(guide_mark_color)
        self.reader_display.set_resume_rewind(resume_rewind_enabled, resume_rewind_words)
        self.reader_display.set_scrub_pause(scrub_pause_enabled)

        self._render_current_state()
        self._bind_shortcuts()

        # Reveal now that everything above is built, colored, and
        # comfortably past CustomTkinter's own internal titlebar dance
        # (see the alpha note near the top of __init__). update_idletasks()
        # right before flipping alpha forces any still-queued layout/redraw
        # work, including CTk widgets that defer their own first paint via
        # their own internal after() calls, to actually finish first.
        # Otherwise the reveal can catch some of that mid-flight, showing
        # pieces of the window popping in over a white background instead
        # of one clean paint.
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        self.update_idletasks()
        self.attributes("-alpha", 1)

    def get_draft_text(self) -> str:
        return self.input_view.get_text()

    def set_skip_word_count(self, count: int) -> None:
        self.skip_word_count = count

    def set_pause_on_skip(self, enabled: bool) -> None:
        self.pause_on_skip = enabled

    def set_length_pacing_enabled(self, enabled: bool) -> None:
        self.length_pacing_enabled = enabled
        self.reader_display.set_length_pacing_enabled(enabled)

    def set_split_long_paragraphs_enabled(self, enabled: bool) -> None:
        self.split_long_paragraphs_enabled = enabled
        self.input_view.set_split_long_paragraphs(enabled)

    def set_resume_rewind(self, enabled: bool, words: int) -> None:
        self.reader_display.set_resume_rewind(enabled, words)

    def set_warm_up_enabled(self, enabled: bool) -> None:
        self.warm_up_enabled = enabled
        self.reader_display.set_warm_up_enabled(enabled)

    def set_scrub_pause(self, enabled: bool) -> None:
        self.scrub_pause_enabled = enabled
        self.reader_display.set_scrub_pause(enabled)

    def _render_current_state(self) -> None:
        self.control_row.pack_forget()
        self.input_view.pack_forget()
        self.reader_display.pack_forget()

        if self.transcript.is_stopped:
            self.input_view.set_text(self.transcript.raw_text)
            self.input_view.set_normalization(self.transcript.pre_normalize_text, self.transcript.normalized_text)
            self.input_view.pack(fill="both", expand=True)
        elif self.transcript.raw_text.strip():
            self.control_row.pack(fill="x", padx=10, pady=10)
            self.toolbar.set_paused(self.transcript.is_paused)
            self.reader_display.set_colors(self.transcript.font_color, self.transcript.highlight_color, self.transcript.background_color)
            self.reader_display.set_font_size(self.transcript.font_size)
            self.reader_display.pack(fill="both", expand=True)
            session = ReaderSession(
                self.transcript.raw_text, wpm=self.transcript.wpm, start_index=self.transcript.position,
                length_pacing_enabled=self.length_pacing_enabled,
                warm_up_enabled=self.warm_up_enabled,
            )
            self.reader_display.load_session(session, start_paused=self.transcript.is_paused)
            self.scrub_bar.set_total(session.total_words)
            self.scrub_bar.set_position(session.index)
        else:
            self.input_view.set_normalization(self.transcript.pre_normalize_text, self.transcript.normalized_text)
            self.input_view.pack(fill="both", expand=True)

    def _handle_normalized(self, result) -> None:
        if self.on_normalization_changed:
            self.on_normalization_changed(self.transcript, result)

    def _handle_text_submitted(self, raw_text: str) -> None:
        self._handle_stopped_changed(False)
        self.on_text_submitted(self.transcript, raw_text)
        self._render_current_state()

    def _handle_position_changed(self, index: int) -> None:
        self.scrub_bar.set_position(index)
        if self.on_position_changed:
            self.on_position_changed(self.transcript, index)

    def _handle_scrub(self, index: int) -> None:
        """A live drag: playback is held, so just seek and sync the
        toolbar. The paused state is persisted once on release."""
        is_paused = self.reader_display.scrub_move(index)
        self.toolbar.set_paused(is_paused)

    def _handle_scrub_release(self) -> None:
        """Release: scrub_end() applies the "pause after scrubbing"
        setting (stay paused, or resume from the landed word), then sync
        and persist the final state, the same shape as _handle_skip()."""
        is_paused = self.reader_display.scrub_end()
        self.toolbar.set_paused(is_paused)
        self._handle_pause_changed(is_paused)

    def _handle_progress(self, remaining_ms: int, percent: int) -> None:
        self.toolbar.set_progress(remaining_ms, percent)

    def _handle_session_stats(self, words_read: int, active_seconds: float) -> None:
        if self.on_session_stats:
            self.on_session_stats(self.transcript, words_read, active_seconds)

    def _handle_stopped_changed(self, is_stopped: bool) -> None:
        if self.on_stopped_changed:
            self.on_stopped_changed(self.transcript, is_stopped)

    def _handle_skip_back(self) -> None:
        self._handle_skip(-self.skip_word_count)

    def _handle_skip_forward(self) -> None:
        self._handle_skip(self.skip_word_count)

    def _handle_skip(self, delta: int) -> None:
        is_paused = self.reader_display.skip(delta, force_pause=self.pause_on_skip)
        self.toolbar.set_paused(is_paused)
        self._handle_pause_changed(is_paused)

    def _handle_pause_changed(self, is_paused: bool) -> None:
        if self.on_pause_changed:
            self.on_pause_changed(self.transcript, is_paused)

    def _handle_pause_toggle(self) -> None:
        is_paused = self.reader_display.toggle_pause()
        self.toolbar.set_paused(is_paused)
        self._handle_pause_changed(is_paused)

    def _handle_restart(self) -> None:
        self.reader_display.restart()
        self.toolbar.set_paused(False)
        self._handle_pause_changed(False)

    def _handle_stop(self) -> None:
        """Ends the reading session and drops back to the paste/edit
        view, right here in this window. Mirrors Canvas.stop() (see
        gui/components/canvas.py), but built for the first time here,
        since this window had no stop capability at all before this
        method (no button, no handler).

        Guarded the same way Canvas.stop() is guarded, for the same
        reason: only act when the reader is genuinely what's on screen
        right now (self.transcript.is_stopped is False and
        self.transcript.raw_text.strip() is truthy, the exact condition
        _render_current_state()'s own elif branch below already uses to
        decide whether to show the reader). Without this, stopping while
        the transcript is a blank, never-submitted draft unconditionally
        re-renders with self.transcript.raw_text, which is an empty
        string for a draft that's never been submitted, silently wiping
        out whatever was typed.

        Doesn't need Canvas.stop()'s separate detached-placeholder check:
        this window has no further "detach" of its own (show_detach=False
        on its toolbar), so there's no equivalent third state to guard
        against here.

        Also doesn't need Canvas.stop()'s explicit
        `self.input_view.set_text(...)` call before showing the input
        view: _render_current_state() below already does that itself as
        part of its `is_stopped` branch, since this window drives its
        content purely off self.transcript's current fields rather than
        Canvas's separate _show_X() methods. _handle_stopped_changed(True)
        reaches self.transcript.is_stopped via the same
        store-mutates-the-object-in-place path _handle_text_submitted()
        above already relies on for the opposite (False) transition, so
        by the time _render_current_state() runs, self.transcript already
        reflects the stop."""
        if self.transcript.is_stopped or not self.transcript.raw_text.strip():
            return
        self.reader_display.stop()
        self.toolbar.set_paused(False)
        self._handle_position_changed(0)
        self._handle_pause_changed(False)
        self._handle_stopped_changed(True)
        self._render_current_state()

    def _bind_shortcuts(self) -> None:
        """Same reading-control shortcuts as the main window (see
        gui/app.py's _bind_shortcuts() for the full reasoning): Space,
        Left/Right, R, Esc. Bound separately here since this is its own
        CTkToplevel and Tk's window-level binding only reaches the window
        it's actually bound on. Space/Left/Right/R call straight into
        this window's own existing handlers (_handle_pause_toggle,
        _handle_skip_back, _handle_skip_forward, _handle_restart), which
        only ever needed to be called from this class to begin with (by
        the toolbar's own callback wiring), so nothing about their
        visibility needs to change. Esc/_handle_stop had no existing
        private handler to call into, since this window had no stop
        capability before it (see that method's own docstring)."""
        self.bind("<space>", self._handle_shortcut_pause_toggle)
        self.bind("<Left>", self._handle_shortcut_skip_backward)
        self.bind("<Right>", self._handle_shortcut_skip_forward)
        self.bind("<r>", self._handle_shortcut_restart)
        self.bind("<R>", self._handle_shortcut_restart)
        self.bind("<Escape>", self._handle_shortcut_stop)

    def _shortcut_should_fire(self) -> bool:
        """Identical guard to gui/app.py's; see that docstring for the
        full reasoning. focus_get() here is scoped to this window (Tk
        tracks focus per-toplevel), so this only looks at what has focus
        inside the detached window, not the main window."""
        focused = self.focus_get()
        if focused is None:
            return True
        return focused.winfo_class() not in ("Entry", "Text")

    def _handle_shortcut_pause_toggle(self, event=None) -> None:
        if self._shortcut_should_fire():
            self._handle_pause_toggle()

    def _handle_shortcut_skip_backward(self, event=None) -> None:
        if self._shortcut_should_fire():
            self._handle_skip_back()

    def _handle_shortcut_skip_forward(self, event=None) -> None:
        if self._shortcut_should_fire():
            self._handle_skip_forward()

    def _handle_shortcut_restart(self, event=None) -> None:
        if self._shortcut_should_fire():
            self._handle_restart()

    def _handle_shortcut_stop(self, event=None) -> None:
        if self._shortcut_should_fire():
            self._handle_stop()

    def close(self) -> None:
        """Closing this window while it's mid-read commits nothing new:
        Canvas._handle_detached_closed()'s own condition (is_stopped or
        raw_text empty) will be False there, so nothing gets reported,
        since whatever was already read is already persisted via the
        normal position/pause callbacks that fire throughout reading.

        Otherwise, stopped (self.transcript.is_stopped, shown as editable
        text that may have been changed further since stopping) or
        never-submitted (raw_text still empty), capture whatever's
        actually in the box right now and pass it along.

        This condition must match _handle_detached_closed()'s own
        condition for when it'll actually use draft_text, or the two
        fall out of sync: a stopped-but-not-empty transcript (exactly the
        state Esc/_handle_stop() leaves one in) needs draft_text
        captured here, since _handle_detached_closed() treats is_stopped
        as reason enough to report and persist it, empty or not."""
        self.reader_display.stop()
        draft_text = ""
        if self.transcript.is_stopped or not self.transcript.raw_text.strip():
            draft_text = self.get_draft_text().strip()
        self.on_closed(draft_text)
        self.destroy()