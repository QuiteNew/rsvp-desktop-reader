import customtkinter as ctk

from gui.components.transcript_list import TranscriptList
from gui.components.spaces import Spaces
from gui.components.reading_panel import ReadingPanel
from gui.components.footer import Footer


class RSVPApp(ctk.CTk):
    """Main application window, laid out as a single 2x2 grid."""

    SIDEBAR_WIDTH = 220
    BOTTOM_BAND_HEIGHT = 150  # thicker per layout feedback — shared by Spaces and Footer

    def __init__(self):
        super().__init__()
        self.title("RSVP Reader")
        self.geometry("1000x650")

        self.grid_rowconfigure(0, weight=1)  # main content — dominant
        self.grid_rowconfigure(1, weight=0, minsize=self.BOTTOM_BAND_HEIGHT)
        self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_WIDTH)
        self.grid_columnconfigure(1, weight=1)  # right column — expands

        self.transcript_list = TranscriptList(self)
        self.transcript_list.grid(row=0, column=0, sticky="nsew")

        self.reading_panel = ReadingPanel(self)
        self.reading_panel.grid(row=0, column=1, sticky="nsew")

        self.spaces = Spaces(self)
        self.spaces.grid(row=1, column=0, sticky="nsew")

        self.footer = Footer(self)
        self.footer.grid(row=1, column=1, sticky="nsew")