import customtkinter as ctk

from gui.components.transcript_list import TranscriptList
from gui.components.spaces import Spaces
from gui.components.reading_panel import ReadingPanel
from gui.components.footer import Footer
from gui.components.add_transcript_dialog import AddTranscriptDialog
from gui.components.add_space_dialog import AddSpaceDialog
from core.transcript_store import TranscriptStore


class RSVPApp(ctk.CTk):
    """Main application window, laid out as a single 2x2 grid."""

    SIDEBAR_WIDTH = 220
    BOTTOM_BAND_HEIGHT = 150

    def __init__(self):
        super().__init__()
        self.title("RSVP Reader")
        self.geometry("1000x650")

        self.store = TranscriptStore()

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0, minsize=self.BOTTOM_BAND_HEIGHT)
        self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_WIDTH)
        self.grid_columnconfigure(1, weight=1)

        self.transcript_list = TranscriptList(self, on_add=self._open_add_transcript_dialog)
        self.transcript_list.grid(row=0, column=0, sticky="nsew")

        self.reading_panel = ReadingPanel(self)
        self.reading_panel.grid(row=0, column=1, sticky="nsew")

        self.spaces = Spaces(
            self,
            spaces=self.store.spaces,
            current_space=self.store.current_space,
            on_select=self._handle_space_selected,
            on_add=self._open_add_space_dialog,
        )
        self.spaces.grid(row=1, column=0, sticky="nsew")

        self.footer = Footer(self)
        self.footer.grid(row=1, column=1, sticky="nsew")

    def _open_add_transcript_dialog(self) -> None:
        AddTranscriptDialog(
            self,
            spaces=self.store.spaces,
            default_space=self.store.current_space,
            on_submit=self._handle_new_transcript,
        )

    def _handle_new_transcript(self, title: str, space: str) -> None:
        self.store.add_transcript(title, space)
        self._refresh_transcript_list()

    def _open_add_space_dialog(self) -> None:
        AddSpaceDialog(self, on_submit=self._handle_new_space)

    def _handle_new_space(self, name: str) -> None:
        current = self.store.add_space(name)
        self.spaces.update_spaces(self.store.spaces)
        self.spaces.set_current_space(current)
        self._refresh_transcript_list()

    def _handle_space_selected(self, name: str) -> None:
        current = self.store.switch_to_space(name)
        self.spaces.set_current_space(current)
        self._refresh_transcript_list()

    def _refresh_transcript_list(self) -> None:
        self.transcript_list.render_transcripts(self.store.transcripts_in_current_space)