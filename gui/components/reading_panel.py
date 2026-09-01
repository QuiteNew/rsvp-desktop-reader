import customtkinter as ctk

from gui.components.header import Header
from gui.components.canvas import Canvas


class ReadingPanel(ctk.CTkFrame):
    """Header (slim) stacked over Canvas (dominant)."""

    HEADER_HEIGHT = 50

    def __init__(self, master, on_text_submitted=None):
        super().__init__(master, corner_radius=0)
        self.grid_rowconfigure(0, weight=0, minsize=self.HEADER_HEIGHT)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.header = Header(self)
        self.header.grid(row=0, column=0, sticky="nsew")

        self.canvas = Canvas(self, on_text_submitted=on_text_submitted)
        self.canvas.grid(row=1, column=0, sticky="nsew")

    def load_transcript(self, transcript) -> None:
        self.header.set_title(transcript.title)
        self.canvas.load_transcript(transcript)