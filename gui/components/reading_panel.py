import customtkinter as ctk

from gui.components.header import Header
from gui.components.canvas import Canvas


class ReadingPanel(ctk.CTkFrame):
    """Header (slim) stacked over Canvas (dominant)."""

    HEADER_HEIGHT = 50

    def __init__(self, master, on_text_submitted=None, on_maximize_toggle=None, on_position_changed=None, on_pause_changed=None):
        super().__init__(master, corner_radius=0)
        self.grid_rowconfigure(0, weight=0, minsize=self.HEADER_HEIGHT)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.header = Header(self)
        self.header.grid(row=0, column=0, sticky="nsew")

        self.canvas = Canvas(
            self,
            on_text_submitted=on_text_submitted,
            on_maximize_toggle=on_maximize_toggle,
            on_position_changed=on_position_changed,
            on_pause_changed=on_pause_changed,
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")

    def load_transcript(self, transcript) -> None:
        self.header.set_title(transcript.title)
        self.canvas.load_transcript(transcript)

    def set_focus_mode(self, is_focused: bool) -> None:
        if is_focused:
            self.header.grid_remove()
            self.grid_rowconfigure(0, minsize=0)
        else:
            self.header.grid()
            self.grid_rowconfigure(0, minsize=self.HEADER_HEIGHT)
        self.canvas.set_maximized(is_focused)

    def set_wpm(self, wpm: int) -> None:
        self.canvas.set_wpm(wpm)

    def set_colors(self, font_color: str, highlight_color: str, background_color: str) -> None:
        self.canvas.set_colors(font_color, highlight_color, background_color)