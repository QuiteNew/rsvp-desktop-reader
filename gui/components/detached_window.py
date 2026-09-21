import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay
from gui.components.canvas_toolbar import CanvasToolbar
from gui.theme import apply_app_icon, center_over_parent, HEARTH_PAPER


class DetachedTranscriptWindow(ctk.CTkToplevel):
    """A standalone window showing one transcript, separate from the main app window."""

    def __init__(
        self, master, transcript, on_text_submitted, on_closed,
        on_position_changed=None, on_pause_changed=None, on_stopped_changed=None,
        initial_draft_text="",
        skip_word_count: int = 10, pause_on_skip: bool = False,
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
        self.skip_word_count = skip_word_count
        self.pause_on_skip = pause_on_skip

        self.title(transcript.title)
        apply_app_icon(self)
        center_over_parent(self, 500, 350)
        self.protocol("WM_DELETE_WINDOW", self.close)
        # Previously unset -- CTkToplevel's own default theme background
        # doesn't match this app's palette, so without this the window
        # showed a mismatched background wherever the toolbar/input/reader
        # widgets below don't fully cover it (and made the white-flash
        # symptom above worse specifically for this window).
        self.configure(fg_color=HEARTH_PAPER)

        self.toolbar = CanvasToolbar(
            self,
            on_skip_back=self._handle_skip_back,
            on_skip_forward=self._handle_skip_forward,
            on_pause_toggle=self._handle_pause_toggle,
            on_restart=self._handle_restart,
            show_skip=True,
            show_maximize=False,
            show_detach=False,
        )

        self.input_view = TranscriptInput(
            self, on_submit=self._handle_text_submitted, initial_text=initial_draft_text
        )
        self.reader_display = ReaderDisplay(self, on_position_changed=self._handle_position_changed)
        self.reader_display.set_highlight_offset(highlight_offset_px)
        self.reader_display.set_guide_mark_horizontal_enabled(guide_mark_horizontal_enabled)
        self.reader_display.set_guide_mark_thickness(guide_mark_thickness_px)
        self.reader_display.set_guide_mark_length_percent(guide_mark_length_percent)
        self.reader_display.set_guide_mark_color(guide_mark_color)

        self._render_current_state()

        # Reveal now that everything above is built, colored, and
        # comfortably past CustomTkinter's own internal titlebar dance
        # (see the alpha note near the top of __init__). update_idletasks()
        # right before flipping alpha forces any still-queued layout/redraw
        # work (including CTk widgets that defer their own first paint via
        # their own internal after() calls) to actually finish first --
        # otherwise the reveal can catch some of that mid-flight, showing
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

    def _render_current_state(self) -> None:
        self.toolbar.pack_forget()
        self.input_view.pack_forget()
        self.reader_display.pack_forget()

        if self.transcript.is_stopped:
            self.input_view.set_text(self.transcript.raw_text)
            self.input_view.pack(fill="both", expand=True)
        elif self.transcript.raw_text.strip():
            self.toolbar.pack(anchor="ne", padx=10, pady=10)
            self.toolbar.set_paused(self.transcript.is_paused)
            self.reader_display.set_colors(self.transcript.font_color, self.transcript.highlight_color, self.transcript.background_color)
            self.reader_display.set_font_size(self.transcript.font_size)
            self.reader_display.pack(fill="both", expand=True)
            self.reader_display.load_session(
                ReaderSession(self.transcript.raw_text, wpm=self.transcript.wpm, start_index=self.transcript.position),
                start_paused=self.transcript.is_paused,
            )
        else:
            self.input_view.pack(fill="both", expand=True)

    def _handle_text_submitted(self, raw_text: str) -> None:
        self._handle_stopped_changed(False)
        self.on_text_submitted(self.transcript, raw_text)
        self._render_current_state()

    def _handle_position_changed(self, index: int) -> None:
        if self.on_position_changed:
            self.on_position_changed(self.transcript, index)

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

    def close(self) -> None:
        self.reader_display.stop()
        draft_text = ""
        if not self.transcript.raw_text.strip():
            draft_text = self.get_draft_text().strip()
        self.on_closed(draft_text)
        self.destroy()