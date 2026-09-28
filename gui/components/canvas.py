import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay
from gui.components.canvas_toolbar import CanvasToolbar
from gui.components.stop_button import StopButton
from gui.components.detached_window import DetachedTranscriptWindow
from gui.components.selection_preview_window import SelectionPreviewWindow
from gui.theme import HEARTH_PAPER


class Canvas(ctk.CTkFrame):
    """Main reading area: stop button (top-left) and toolbar (top-right)
    above whichever content state applies."""

    def __init__(
        self, master,
        on_text_submitted=None, on_maximize_toggle=None,
        on_position_changed=None, on_pause_changed=None, on_draft_changed=None,
        on_stopped_changed=None, on_session_stats=None, on_normalization_changed=None,
        skip_word_count: int = 10, pause_on_skip: bool = False,
        highlight_offset_px: int = 0,
        guide_mark_horizontal_enabled: bool = False,
        guide_mark_thickness_px: int = 2,
        guide_mark_length_percent: int = 35,
        guide_mark_color: str = "#3B2E27",
        length_pacing_enabled: bool = False,
        split_long_paragraphs_enabled: bool = False,
    ):
        super().__init__(master, fg_color=HEARTH_PAPER, corner_radius=0)
        self.on_text_submitted = on_text_submitted
        self.on_maximize_toggle = on_maximize_toggle
        self.on_position_changed = on_position_changed
        self.on_pause_changed = on_pause_changed
        self.on_draft_changed = on_draft_changed
        self.on_stopped_changed = on_stopped_changed
        self.on_session_stats = on_session_stats
        self.on_normalization_changed = on_normalization_changed
        self._skip_word_count = skip_word_count
        self._pause_on_skip = pause_on_skip
        self._highlight_offset_px = highlight_offset_px
        self._guide_mark_horizontal_enabled = guide_mark_horizontal_enabled
        self._guide_mark_thickness_px = guide_mark_thickness_px
        self._guide_mark_length_percent = guide_mark_length_percent
        self._guide_mark_color = guide_mark_color
        self._length_pacing_enabled = length_pacing_enabled
        self._split_long_paragraphs_enabled = split_long_paragraphs_enabled
        self.current_transcript = None
        self._detached_transcript_id = None
        self._detached_transcript = None
        self._detached_window = None
        self._input_currently_shown = False
        # True while a selection preview (right-click Play) is running, so
        # its position, stats and pause state are not persisted to the
        # transcript. See play_selection() and _stop_ephemeral().
        self._ephemeral = False
        # Open selection-preview windows (right-click Detach), as
        # (window, transcript_id, index) tuples. Several may be open at
        # once; each is independent and persists nothing. See
        # open_selection_preview().
        self._selection_previews = []

        self.button_row = ctk.CTkFrame(self, fg_color="transparent")
        self.button_row.grid_columnconfigure(0, weight=1)
        self.button_row.grid_columnconfigure(1, weight=0)

        self.stop_button = StopButton(self.button_row, on_stop=self.stop)
        self.stop_button.grid(row=0, column=0, sticky="w")

        self.toolbar = CanvasToolbar(
            self.button_row,
            on_pause_toggle=self.toggle_pause,
            on_restart=self.restart,
            on_maximize_toggle=self._handle_maximize_toggle,
            on_detach=self._handle_detach,
        )
        self.toolbar.grid(row=0, column=1, sticky="e")

        self.content_area = ctk.CTkFrame(self, fg_color="transparent")

        self.empty_label = ctk.CTkLabel(self.content_area, text="Select or create a transcript to begin")
        self.input_view = TranscriptInput(
            self.content_area, on_submit=self._handle_text_submitted, on_normalized=self._handle_normalized,
            split_long_paragraphs=self._split_long_paragraphs_enabled,
            on_play_selection=self._handle_play_selection,
            on_detach_selection=self._handle_detach_selection,
        )
        self.reader_display = ReaderDisplay(
            self.content_area,
            on_position_changed=self._handle_position_changed,
            on_session_stats=self._handle_session_stats,
        )
        self.reader_display.set_highlight_offset(self._highlight_offset_px)
        self.reader_display.set_guide_mark_horizontal_enabled(self._guide_mark_horizontal_enabled)
        self.reader_display.set_guide_mark_thickness(self._guide_mark_thickness_px)
        self.reader_display.set_guide_mark_length_percent(self._guide_mark_length_percent)
        self.reader_display.set_guide_mark_color(self._guide_mark_color)

        self.detached_placeholder = ctk.CTkFrame(self.content_area, fg_color="transparent")
        ctk.CTkLabel(
            self.detached_placeholder, text="Transcript window detached", text_color="gray60"
        ).pack(expand=True, pady=(0, 10))
        ctk.CTkButton(
            self.detached_placeholder, text="✕  Bring back", width=130, command=self._handle_reattach
        ).pack()

        self._show_empty()

    def load_transcript(self, transcript) -> None:
        self._capture_current_draft()
        self.reader_display.stop()
        # Loading a real transcript ends any selection preview. Cleared
        # after stop() above so that preview's finalize stays suppressed.
        self._ephemeral = False
        self.current_transcript = transcript

        if transcript.id == self._detached_transcript_id:
            self._show_detached_placeholder()
        elif transcript.is_stopped:
            self._fill_input(transcript.raw_text)
            self._show_input()
        elif transcript.raw_text.strip():
            self._show_reader()
            self.toolbar.set_paused(transcript.is_paused)
            self.reader_display.set_colors(transcript.font_color, transcript.highlight_color, transcript.background_color)
            self.reader_display.set_font_size(transcript.font_size)
            self.reader_display.load_session(
                ReaderSession(
                    transcript.raw_text, wpm=transcript.wpm, start_index=transcript.position,
                    length_pacing_enabled=self._length_pacing_enabled,
                ),
                start_paused=transcript.is_paused,
            )
        else:
            self._fill_input(transcript.draft_text)
            self._show_input()

    def handle_transcript_deleted(self, transcript_id: int) -> None:
        was_current = self.current_transcript is not None and self.current_transcript.id == transcript_id
        was_detached = self._detached_transcript_id == transcript_id

        if was_current:
            self.current_transcript = None
            self.reader_display.stop()
            self._ephemeral = False

        if was_detached:
            detached_window = self._detached_window
            self._detached_transcript_id = None
            self._detached_transcript = None
            self._detached_window = None
            if detached_window:
                detached_window.destroy()

        if was_current:
            self._show_empty()

    def set_maximized(self, is_maximized: bool) -> None:
        self.toolbar.set_maximized(is_maximized)

    def set_wpm(self, wpm: int) -> None:
        self.reader_display.set_wpm(wpm)
        if self._detached_window:
            self._detached_window.reader_display.set_wpm(wpm)

    def set_colors(self, font_color: str, highlight_color: str, background_color: str) -> None:
        self.reader_display.set_colors(font_color, highlight_color, background_color)
        if self._detached_window:
            self._detached_window.reader_display.set_colors(font_color, highlight_color, background_color)

    def set_font_size(self, size: int) -> None:
        self.reader_display.set_font_size(size)
        if self._detached_window:
            self._detached_window.reader_display.set_font_size(size)

    def set_highlight_offset(self, offset_px: int) -> None:
        self._highlight_offset_px = offset_px
        self.reader_display.set_highlight_offset(offset_px)
        if self._detached_window:
            self._detached_window.reader_display.set_highlight_offset(offset_px)

    def set_guide_mark_horizontal_enabled(self, enabled: bool) -> None:
        self._guide_mark_horizontal_enabled = enabled
        self.reader_display.set_guide_mark_horizontal_enabled(enabled)
        if self._detached_window:
            self._detached_window.reader_display.set_guide_mark_horizontal_enabled(enabled)

    def set_guide_mark_thickness(self, thickness_px: int) -> None:
        self._guide_mark_thickness_px = thickness_px
        self.reader_display.set_guide_mark_thickness(thickness_px)
        if self._detached_window:
            self._detached_window.reader_display.set_guide_mark_thickness(thickness_px)

    def set_guide_mark_length_percent(self, percent: int) -> None:
        self._guide_mark_length_percent = percent
        self.reader_display.set_guide_mark_length_percent(percent)
        if self._detached_window:
            self._detached_window.reader_display.set_guide_mark_length_percent(percent)

    def set_guide_mark_color(self, color: str) -> None:
        self._guide_mark_color = color
        self.reader_display.set_guide_mark_color(color)
        if self._detached_window:
            self._detached_window.reader_display.set_guide_mark_color(color)

    def skip_backward(self) -> None:
        self._skip(-self._skip_word_count)

    def skip_forward(self) -> None:
        self._skip(self._skip_word_count)

    def _skip(self, delta: int) -> None:
        if self._detached_window:
            is_paused = self._detached_window.reader_display.skip(delta, force_pause=self._pause_on_skip)
            self._detached_window.toolbar.set_paused(is_paused)
        else:
            is_paused = self.reader_display.skip(delta, force_pause=self._pause_on_skip)
            self.toolbar.set_paused(is_paused)
        self._handle_pause_changed(is_paused)

    def set_skip_word_count(self, count: int) -> None:
        self._skip_word_count = count
        if self._detached_window:
            self._detached_window.set_skip_word_count(count)

    def set_pause_on_skip(self, enabled: bool) -> None:
        self._pause_on_skip = enabled
        if self._detached_window:
            self._detached_window.set_pause_on_skip(enabled)

    def set_length_pacing_enabled(self, enabled: bool) -> None:
        self._length_pacing_enabled = enabled
        self.reader_display.set_length_pacing_enabled(enabled)
        if self._detached_window:
            self._detached_window.set_length_pacing_enabled(enabled)

    def set_split_long_paragraphs_enabled(self, enabled: bool) -> None:
        self._split_long_paragraphs_enabled = enabled
        self.input_view.set_split_long_paragraphs(enabled)
        if self._detached_window:
            self._detached_window.set_split_long_paragraphs_enabled(enabled)

    def save_pending_draft(self) -> None:
        self._capture_current_draft()

    def flush_active_session_stats(self) -> None:
        """Report whatever's been accumulated in any reading session
        currently in flight: this canvas's own reader_display, and, if a
        transcript is detached, that window's reader_display too, without
        otherwise disturbing playback state. Called from gui/app.py's
        close handler (_handle_close()), the one exit path that never
        goes through stop() or DetachedTranscriptWindow.close() first:
        quitting the whole app tears down every Toplevel via Tk's own
        destroy() cascade, which does not invoke a Toplevel's own
        WM_DELETE_WINDOW handler, so without this, closing the app
        mid-read (in either window) would silently lose that session's
        tail end. Safe to call unconditionally: both finalize_session()
        calls below are no-ops if nothing is loaded there."""
        self.reader_display.finalize_session()
        if self._detached_window:
            self._detached_window.reader_display.finalize_session()

    def _capture_current_draft(self) -> None:
        if self._input_currently_shown and self.current_transcript:
            text = self.input_view.get_text().strip()
            self._report_draft_changed(self.current_transcript, text)

    def _report_draft_changed(self, transcript, text: str) -> None:
        if self.on_draft_changed:
            self.on_draft_changed(transcript, text)

    def _handle_stopped_changed(self, is_stopped: bool) -> None:
        if self.on_stopped_changed and self.current_transcript:
            self.on_stopped_changed(self.current_transcript, is_stopped)

    def _fill_input(self, text: str) -> None:
        """Show text in the edit box along with the current transcript's
        Normalize undo information, so the button's label always belongs
        to the transcript on screen."""
        self.input_view.set_text(text)
        self.input_view.set_normalization(
            self.current_transcript.pre_normalize_text, self.current_transcript.normalized_text,
        )

    def _handle_normalized(self, result) -> None:
        if self.on_normalization_changed and self.current_transcript:
            self.on_normalization_changed(self.current_transcript, result)

    def _handle_play_selection(self, text: str) -> None:
        self.play_selection(text)

    def _handle_detach_selection(self, text: str) -> None:
        self.open_selection_preview(text)

    def open_selection_preview(self, text: str) -> None:
        """Open a standalone, independent window seeded with the highlighted
        text (right-click Detach). It opens on its own edit box, so you
        choose when (or whether) to start reading, and nothing done in it
        touches this transcript's draft, saved text, position or stats (see
        SelectionPreviewWindow). Several may be open at once; each carries
        the transcript's name plus a per-transcript number in its title,
        and a small cascade offset so successive windows don't land exactly
        on top of each other. Its styling is a snapshot of the transcript's
        current WPM, colours, font and guide-mark settings."""
        transcript = self.current_transcript
        if transcript is None or not text.strip():
            return
        index = self._next_preview_index(transcript.id)
        window = SelectionPreviewWindow(
            self,
            title=f"{transcript.title} ({index})",
            text=text,
            wpm=transcript.wpm,
            font_color=transcript.font_color,
            highlight_color=transcript.highlight_color,
            background_color=transcript.background_color,
            font_size=transcript.font_size,
            on_closed=self._handle_preview_closed,
            cascade_offset=30 * (len(self._selection_previews) % 6),
            skip_word_count=self._skip_word_count,
            pause_on_skip=self._pause_on_skip,
            length_pacing_enabled=self._length_pacing_enabled,
            split_long_paragraphs_enabled=self._split_long_paragraphs_enabled,
            highlight_offset_px=self._highlight_offset_px,
            guide_mark_horizontal_enabled=self._guide_mark_horizontal_enabled,
            guide_mark_thickness_px=self._guide_mark_thickness_px,
            guide_mark_length_percent=self._guide_mark_length_percent,
            guide_mark_color=self._guide_mark_color,
        )
        self._selection_previews.append((window, transcript.id, index))

    def _next_preview_index(self, transcript_id) -> int:
        """The smallest positive number not currently used by an open
        preview of this transcript, so titles stay small and a closed
        window's number can be reused, while every open window keeps a
        stable, distinct title."""
        used = {idx for (_w, tid, idx) in self._selection_previews if tid == transcript_id}
        index = 1
        while index in used:
            index += 1
        return index

    def _handle_preview_closed(self, window) -> None:
        self._selection_previews = [
            entry for entry in self._selection_previews if entry[0] is not window
        ]

    def play_selection(self, text: str) -> None:
        """Run just the highlighted text as a preview in the reader,
        without changing the transcript's saved position, started/stopped
        state or reading stats. It uses the transcript's current WPM,
        colours and font, starts at the first word, and drops back to the
        edit box (with its full text intact) when stopped or finished. See
        the _ephemeral flag and _stop_ephemeral()."""
        transcript = self.current_transcript
        if transcript is None or not text.strip():
            return
        self._ephemeral = True
        self.reader_display.stop()
        self._show_reader()
        self.toolbar.set_paused(False)
        self.reader_display.set_colors(transcript.font_color, transcript.highlight_color, transcript.background_color)
        self.reader_display.set_font_size(transcript.font_size)
        self.reader_display.load_session(
            ReaderSession(
                text, wpm=transcript.wpm, start_index=0,
                length_pacing_enabled=self._length_pacing_enabled,
            ),
            start_paused=False,
        )
        # Move keyboard focus off the (now hidden) edit box so Space/arrows/
        # R drive the reader instead of typing into the draft. The reader
        # area isn't an Entry/Text, so the app's shortcut guard lets them
        # through (see gui/app.py's _shortcut_should_fire). Re-applied after
        # idle so the closing right-click popup's teardown can't hand focus
        # back to the edit box.
        self.reader_display.focus_set()
        self.after_idle(self.reader_display.focus_set)

    def _stop_ephemeral(self) -> None:
        """End a selection preview and return to the edit box, which kept
        its full text while the preview ran. Persists nothing: the
        transcript's position, stopped state and stats are untouched. The
        reader is stopped while _ephemeral is still True, so its finalize
        stays suppressed, then the flag is cleared."""
        self.reader_display.stop()
        self._ephemeral = False
        self.toolbar.set_paused(False)
        self._show_input()

    def _handle_text_submitted(self, raw_text: str) -> None:
        if self.current_transcript:
            self._handle_stopped_changed(False)
            self._report_draft_changed(self.current_transcript, "")
        if self.on_text_submitted and self.current_transcript:
            self.on_text_submitted(self.current_transcript, raw_text)

    def _handle_position_changed(self, index: int) -> None:
        if self._ephemeral:
            return
        if self.on_position_changed and self.current_transcript:
            self.on_position_changed(self.current_transcript, index)

    def _handle_session_stats(self, words_read: int, active_seconds: float) -> None:
        if self._ephemeral:
            return
        if self.on_session_stats and self.current_transcript:
            self.on_session_stats(self.current_transcript, words_read, active_seconds)

    def _handle_pause_changed(self, is_paused: bool) -> None:
        if self._ephemeral:
            return
        if self.on_pause_changed and self.current_transcript:
            self.on_pause_changed(self.current_transcript, is_paused)

    def toggle_pause(self) -> None:
        is_paused = self.reader_display.toggle_pause()
        self.toolbar.set_paused(is_paused)
        self._handle_pause_changed(is_paused)

    def restart(self) -> None:
        self.reader_display.restart()
        self.toolbar.set_paused(False)
        self._handle_pause_changed(False)

    def stop(self) -> None:
        """Ends the current reading session and drops back to the
        paste/edit view, showing whatever text that session was reading.

        Guarded to only actually do anything when the reader is what's
        genuinely on screen right now for this transcript: not while the
        paste/edit view is already showing (self._input_currently_shown,
        the same flag _capture_current_draft() uses for exactly this "is
        the input box what's live right now" question), and not while
        this transcript is off being read in the detached window instead
        (self.current_transcript.id == self._detached_transcript_id, when
        the detached placeholder is what Canvas itself is showing).

        This isn't just an Esc-specific guard: the Stop button itself is
        visible, and just as able to trigger this, in every one of those
        states too, since button_row is shown for both _show_input() and
        _show_reader(). Without it, stopping while nothing is actually
        being read unconditionally overwrites the input box with
        self.current_transcript.raw_text, which for a transcript that's
        never been submitted yet is an empty string, silently wiping out
        whatever was typed."""
        if self._ephemeral:
            self._stop_ephemeral()
            return
        if not self.current_transcript:
            return
        if self._input_currently_shown or self.current_transcript.id == self._detached_transcript_id:
            return
        self.reader_display.stop()
        self.toolbar.set_paused(False)
        self._handle_position_changed(0)
        self._handle_pause_changed(False)
        self._handle_stopped_changed(True)
        self._fill_input(self.current_transcript.raw_text)
        self._show_input()

    def _handle_maximize_toggle(self) -> None:
        if self.on_maximize_toggle:
            self.on_maximize_toggle()

    def _handle_detach(self) -> None:
        if not self.current_transcript:
            return
        self.reader_display.stop()
        self._ephemeral = False
        self._detached_transcript_id = self.current_transcript.id
        self._detached_transcript = self.current_transcript

        draft_text = ""
        if self.current_transcript.is_stopped:
            draft_text = self.current_transcript.raw_text
        elif not self.current_transcript.raw_text.strip():
            draft_text = self.input_view.get_text().strip()
            self._report_draft_changed(self.current_transcript, draft_text)

        self._detached_window = DetachedTranscriptWindow(
            self,
            self.current_transcript,
            initial_draft_text=draft_text,
            on_text_submitted=self._handle_detached_text_submitted,
            on_closed=self._handle_detached_closed,
            on_position_changed=self.on_position_changed,
            on_pause_changed=self.on_pause_changed,
            on_stopped_changed=self.on_stopped_changed,
            on_session_stats=self.on_session_stats,
            on_normalization_changed=self.on_normalization_changed,
            skip_word_count=self._skip_word_count,
            pause_on_skip=self._pause_on_skip,
            highlight_offset_px=self._highlight_offset_px,
            guide_mark_horizontal_enabled=self._guide_mark_horizontal_enabled,
            guide_mark_thickness_px=self._guide_mark_thickness_px,
            guide_mark_length_percent=self._guide_mark_length_percent,
            guide_mark_color=self._guide_mark_color,
            length_pacing_enabled=self._length_pacing_enabled,
            split_long_paragraphs_enabled=self._split_long_paragraphs_enabled,
        )
        self._show_detached_placeholder()

    def _handle_detached_text_submitted(self, transcript, raw_text: str) -> None:
        self._report_draft_changed(transcript, "")
        if self.on_text_submitted:
            self.on_text_submitted(transcript, raw_text)

    def _handle_detached_closed(self, draft_text: str = "") -> None:
        detached_transcript = self._detached_transcript
        self._detached_transcript_id = None
        self._detached_transcript = None
        self._detached_window = None

        if detached_transcript and (detached_transcript.is_stopped or not detached_transcript.raw_text.strip()):
            self._report_draft_changed(detached_transcript, draft_text)

        if self.current_transcript:
            self.load_transcript(self.current_transcript)

    def _handle_reattach(self) -> None:
        if self._detached_window:
            self._detached_window.close()

    def _layout(self, show_buttons: bool) -> None:
        self.button_row.pack_forget()
        self.content_area.pack_forget()
        if show_buttons:
            self.button_row.pack(fill="x", padx=10, pady=10)
        self.content_area.pack(fill="both", expand=True)

    def _show_content(self, widget) -> None:
        for other in (self.empty_label, self.input_view, self.reader_display, self.detached_placeholder):
            other.pack_forget()
        widget.pack(fill="both", expand=True)

    def _show_empty(self) -> None:
        self._input_currently_shown = False
        self._layout(show_buttons=False)
        self._show_content(self.empty_label)

    def _show_input(self) -> None:
        self._input_currently_shown = True
        self._layout(show_buttons=True)
        self._show_content(self.input_view)

    def _show_reader(self) -> None:
        self._input_currently_shown = False
        self._layout(show_buttons=True)
        self._show_content(self.reader_display)

    def _show_detached_placeholder(self) -> None:
        self._input_currently_shown = False
        self._layout(show_buttons=False)
        self._show_content(self.detached_placeholder)