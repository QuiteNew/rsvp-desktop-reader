import customtkinter as ctk

from core.reader import ReaderSession
from gui.components.transcript_input import TranscriptInput
from gui.components.reader_display import ReaderDisplay
from gui.components.canvas_toolbar import CanvasToolbar
from gui.components.detached_window import DetachedTranscriptWindow


class Canvas(ctk.CTkFrame):
    """Main reading area: toolbar row (when relevant) above whichever content state applies."""

    def __init__(self, master, on_text_submitted=None, on_maximize_toggle=None, on_position_changed=None):
        super().__init__(master, fg_color="#2ECC71", corner_radius=0)
        self.on_text_submitted = on_text_submitted
        self.on_maximize_toggle = on_maximize_toggle
        self.on_position_changed = on_position_changed
        self.current_transcript = None
        self._detached_transcript_id = None
        self._detached_window = None

        self.toolbar = CanvasToolbar(
            self,
            on_pause_toggle=self._handle_pause_toggle,
            on_restart=self._handle_restart,
            on_maximize_toggle=self._handle_maximize_toggle,
            on_detach=self._handle_detach,
        )
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")

        self.empty_label = ctk.CTkLabel(self.content_area, text="Select or create a transcript to begin")
        self.input_view = TranscriptInput(self.content_area, on_submit=self._handle_text_submitted)
        self.reader_display = ReaderDisplay(self.content_area, on_position_changed=self._handle_position_changed)

        self.detached_placeholder = ctk.CTkFrame(self.content_area, fg_color="transparent")
        ctk.CTkLabel(
            self.detached_placeholder, text="Transcript window detached", text_color="gray60"
        ).pack(expand=True, pady=(0, 10))
        ctk.CTkButton(
            self.detached_placeholder, text="✕  Bring back", width=130, command=self._handle_reattach
        ).pack()

        self._show_empty()

    def load_transcript(self, transcript) -> None:
        self.reader_display.stop()
        self.current_transcript = transcript

        if transcript.id == self._detached_transcript_id:
            self._show_detached_placeholder()
        elif transcript.raw_text.strip():
            self._show_reader()
            self.toolbar.set_paused(False)
            self.reader_display.load_session(
                ReaderSession(transcript.raw_text, wpm=transcript.wpm, start_index=transcript.position)
            )
        else:
            self.input_view.set_text("")
            self._show_input()

    def set_maximized(self, is_maximized: bool) -> None:
        self.toolbar.set_maximized(is_maximized)

    def _handle_text_submitted(self, raw_text: str) -> None:
        if self.on_text_submitted and self.current_transcript:
            self.on_text_submitted(self.current_transcript, raw_text)

    def _handle_position_changed(self, index: int) -> None:
        if self.on_position_changed and self.current_transcript:
            self.on_position_changed(self.current_transcript, index)

    def _handle_pause_toggle(self) -> None:
        is_paused = self.reader_display.toggle_pause()
        self.toolbar.set_paused(is_paused)

    def _handle_restart(self) -> None:
        self.reader_display.restart()
        self.toolbar.set_paused(False)

    def _handle_maximize_toggle(self) -> None:
        if self.on_maximize_toggle:
            self.on_maximize_toggle()

    def _handle_detach(self) -> None:
        if not self.current_transcript:
            return
        self._detached_transcript_id = self.current_transcript.id

        draft_text = ""
        if not self.current_transcript.raw_text.strip():
            draft_text = self.input_view.get_text().strip()

        self._detached_window = DetachedTranscriptWindow(
            self,
            self.current_transcript,
            initial_draft_text=draft_text,
            on_text_submitted=self._handle_detached_text_submitted,
            on_closed=self._handle_detached_closed,
            on_position_changed=self.on_position_changed,
        )
        self._show_detached_placeholder()

    def _handle_detached_text_submitted(self, transcript, raw_text: str) -> None:
        if self.on_text_submitted:
            self.on_text_submitted(transcript, raw_text)

    def _handle_detached_closed(self, draft_text: str = "") -> None:
        self._detached_transcript_id = None
        self._detached_window = None
        if self.current_transcript:
            self.load_transcript(self.current_transcript)
            if not self.current_transcript.raw_text.strip():
                self.input_view.set_text(draft_text)

    def _handle_reattach(self) -> None:
        if self._detached_window:
            self._detached_window.close()

    def _layout(self, show_toolbar: bool) -> None:
        self.toolbar.pack_forget()
        self.content_area.pack_forget()
        if show_toolbar:
            self.toolbar.pack(anchor="ne", padx=10, pady=10)
        self.content_area.pack(fill="both", expand=True)

    def _show_content(self, widget) -> None:
        for other in (self.empty_label, self.input_view, self.reader_display, self.detached_placeholder):
            other.pack_forget()
        widget.pack(fill="both", expand=True)

    def _show_empty(self) -> None:
        self._layout(show_toolbar=False)
        self._show_content(self.empty_label)

    def _show_input(self) -> None:
        self._layout(show_toolbar=True)
        self._show_content(self.input_view)

    def _show_reader(self) -> None:
        self._layout(show_toolbar=True)
        self._show_content(self.reader_display)

    def _show_detached_placeholder(self) -> None:
        self._layout(show_toolbar=False)
        self._show_content(self.detached_placeholder)