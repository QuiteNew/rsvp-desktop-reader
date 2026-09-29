import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay
from gui.components.canvas_toolbar import CanvasToolbar
from gui.components.scrub_bar import ScrubBar
from gui.theme import apply_app_icon, center_over_parent, HEARTH_PAPER


class SelectionPreviewWindow(ctk.CTkToplevel):
    """A standalone, throwaway editing-and-reading window for one selected
    excerpt of a transcript (right-click a selection, Detach).

    It looks and behaves like the detached transcript window
    (gui/components/detached_window.py), with one deliberate difference: it
    is completely independent of the transcript it came from. It opens on
    its own edit box, pre-filled with the selected text, so you choose when
    (or whether) to start reading. Editing, normalizing or reading here
    never touches the transcript's draft, saved text, position or stats:
    this window holds only its own copy of the excerpt, and its
    ReaderDisplay is built with no persistence callbacks, so there is
    nothing to save. Closing it discards everything.

    Several can be open at once, each fully independent (see
    Canvas.open_selection_preview()); the title is the transcript's name
    with a per-transcript number, e.g. "My transcript (2)", and each opens
    slightly offset from the last so they don't stack exactly.

    Its styling (WPM, colours, font, guide mark) is a snapshot of the
    transcript's settings at the moment it opened. Later Settings changes
    in the main app don't flow into an already-open preview, which keeps
    these throwaway windows simple and self-contained."""

    WIDTH = 500
    HEIGHT = 350

    def __init__(
        self, master, title, text,
        wpm, font_color, highlight_color, background_color, font_size,
        on_closed=None,
        cascade_offset: int = 0,
        skip_word_count: int = 10, pause_on_skip: bool = False,
        length_pacing_enabled: bool = False,
        split_long_paragraphs_enabled: bool = False,
        resume_rewind_enabled: bool = False,
        resume_rewind_words: int = 3,
        warm_up_enabled: bool = False,
        highlight_offset_px: int = 0,
        guide_mark_horizontal_enabled: bool = False,
        guide_mark_thickness_px: int = 2,
        guide_mark_length_percent: int = 35,
        guide_mark_color: str = "#3B2E27",
    ):
        super().__init__(master)

        # Hidden until fully built and positioned, so it never flashes at
        # its default spot first. See gui/components/detached_window.py and
        # settings_window.py for the fuller explanation of this pattern.
        self.attributes("-alpha", 0)

        self.on_closed = on_closed
        self._cascade_offset = cascade_offset
        self.wpm = wpm
        self.font_color = font_color
        self.highlight_color = highlight_color
        self.background_color = background_color
        self.font_size = font_size
        self.skip_word_count = skip_word_count
        self.pause_on_skip = pause_on_skip
        self.length_pacing_enabled = length_pacing_enabled
        self.warm_up_enabled = warm_up_enabled

        self.title(title)
        apply_app_icon(self)
        center_over_parent(self, self.WIDTH, self.HEIGHT)
        self.protocol("WM_DELETE_WINDOW", self.close)
        # CTkToplevel's own default theme background doesn't match this
        # app's palette; without this the window shows a mismatched
        # background wherever the widgets below don't fully cover it.
        self.configure(fg_color=HEARTH_PAPER)

        # Control row mirroring the detached window: scrubber left,
        # toolbar right. Shown only over the reader (see _show_reader).
        self.control_row = ctk.CTkFrame(self, fg_color="transparent")
        self.scrub_bar = ScrubBar(self.control_row, on_scrub=self._handle_scrub)
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
        )
        self.toolbar.pack(side="right")

        # Its own edit box, seeded with the selection. on_normalized is left
        # unset and no play/detach handlers are passed: Normalize works
        # entirely inside this window (it only rewrites this box's own
        # text), and there's no nested right-click menu. Nothing here calls
        # back into the transcript, which is what keeps the window
        # independent of it.
        self.input_view = TranscriptInput(
            self, on_submit=self._start_reading, initial_text=text,
            split_long_paragraphs=split_long_paragraphs_enabled,
        )

        # No persistence callbacks: this preview never writes to the store.
        # It does take a position callback, but only to drive the scrubber's
        # thumb as reading advances; nothing here reaches the transcript.
        self.reader_display = ReaderDisplay(self, on_position_changed=self._handle_position_changed)
        self.reader_display.set_highlight_offset(highlight_offset_px)
        self.reader_display.set_guide_mark_horizontal_enabled(guide_mark_horizontal_enabled)
        self.reader_display.set_guide_mark_thickness(guide_mark_thickness_px)
        self.reader_display.set_guide_mark_length_percent(guide_mark_length_percent)
        self.reader_display.set_guide_mark_color(guide_mark_color)
        self.reader_display.set_resume_rewind(resume_rewind_enabled, resume_rewind_words)

        self._show_input()
        self._bind_shortcuts()

        # Reveal once everything above is built and coloured, past
        # CustomTkinter's own internal titlebar dance. See the matching
        # note in gui/components/detached_window.py.
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        if not self.winfo_exists():
            return
        self.update_idletasks()
        # Offset each successive preview down and to the right so several
        # open at once don't land exactly on top of one another. Computed
        # the same way center_over_parent() positions the window, plus the
        # offset, so it behaves consistently at any display scaling.
        if self._cascade_offset:
            try:
                parent = self.master
                parent.update_idletasks()
                x = parent.winfo_rootx() + (parent.winfo_width() - self.WIDTH) // 2 + self._cascade_offset
                y = parent.winfo_rooty() + (parent.winfo_height() - self.HEIGHT) // 2 + self._cascade_offset
                self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
            except Exception:
                pass
        self.attributes("-alpha", 1)

    def _show_input(self) -> None:
        """The edit view: just the seeded text box with its own Normalize
        and Start reading buttons, no toolbar. Mirrors the detached
        transcript window's paste screen."""
        self.control_row.pack_forget()
        self.reader_display.pack_forget()
        self.input_view.pack(fill="both", expand=True)

    def _show_reader(self) -> None:
        self.input_view.pack_forget()
        self.control_row.pack(fill="x", padx=10, pady=10)
        self.reader_display.pack(fill="both", expand=True)

    def _start_reading(self, text: str) -> None:
        """Run whatever's currently in the edit box, at the snapshot WPM,
        colours and font. A no-op on empty or whitespace-only text, so
        Start reading on an emptied box does nothing rather than opening an
        empty reader."""
        if not text.strip():
            return
        self._show_reader()
        self.toolbar.set_paused(False)
        self.reader_display.set_colors(self.font_color, self.highlight_color, self.background_color)
        self.reader_display.set_font_size(self.font_size)
        session = ReaderSession(
            text, wpm=self.wpm, start_index=0,
            length_pacing_enabled=self.length_pacing_enabled,
            warm_up_enabled=self.warm_up_enabled,
        )
        self.reader_display.load_session(session, start_paused=False)
        self.scrub_bar.set_total(session.total_words)
        self.scrub_bar.set_position(session.index)
        # Move keyboard focus off the (now hidden) edit box so Space/arrows/
        # R drive the reader instead of typing into the text. The reader
        # area isn't an Entry/Text, so the shortcut guard lets them through.
        self.reader_display.focus_set()

    def _stop(self) -> None:
        """Stop reading and return to the edit box, its text untouched.
        Persists nothing."""
        self.reader_display.stop()
        self.toolbar.set_paused(False)
        self._show_input()
        # Back to editing: put focus in the box so keys type there and the
        # reading shortcuts stay quiet (see _shortcut_should_fire).
        self.input_view.textbox.focus_set()

    def _handle_skip_back(self) -> None:
        self._handle_skip(-self.skip_word_count)

    def _handle_skip_forward(self) -> None:
        self._handle_skip(self.skip_word_count)

    def _handle_skip(self, delta: int) -> None:
        is_paused = self.reader_display.skip(delta, force_pause=self.pause_on_skip)
        self.toolbar.set_paused(is_paused)

    def _handle_position_changed(self, index: int) -> None:
        """UI-only: keep the scrubber's thumb tracking the reader as it
        advances. This preview persists nothing, so there's no store call
        here, unlike the main and detached windows."""
        self.scrub_bar.set_position(index)

    def _handle_scrub(self, index: int) -> None:
        is_paused = self.reader_display.scrub_to(index)
        self.toolbar.set_paused(is_paused)

    def _handle_pause_toggle(self) -> None:
        is_paused = self.reader_display.toggle_pause()
        self.toolbar.set_paused(is_paused)

    def _handle_restart(self) -> None:
        self.reader_display.restart()
        self.toolbar.set_paused(False)

    def _bind_shortcuts(self) -> None:
        """Reading-control shortcuts scoped to this window, mirroring the
        detached transcript window: Space to pause, Left/Right to skip, R
        to restart, Escape to stop back to the edit box. Bound on this
        toplevel directly, since Tk's window-level bindings only reach the
        window that owns them."""
        self.bind("<space>", self._handle_shortcut_pause_toggle)
        self.bind("<Left>", self._handle_shortcut_skip_backward)
        self.bind("<Right>", self._handle_shortcut_skip_forward)
        self.bind("<r>", self._handle_shortcut_restart)
        self.bind("<R>", self._handle_shortcut_restart)
        self.bind("<Escape>", self._handle_shortcut_stop)

    def _shortcut_should_fire(self) -> bool:
        """Same guard as the main and detached windows: don't fire the
        reading shortcuts while the edit box has focus, so typing (and
        Escape while editing) behaves normally. focus_get() is scoped to
        this window, so it only looks at what has focus here."""
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
            self._stop()

    def close(self) -> None:
        """Stop the reader and close. Nothing is persisted; the owner is
        told so it can drop its reference (see Canvas)."""
        self.reader_display.stop()
        if self.on_closed:
            self.on_closed(self)
        self.destroy()