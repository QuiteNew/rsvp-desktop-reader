import customtkinter as ctk


class Divider(ctk.CTkFrame):
    """A thin line used to visually separate two stacked sections.

    Deliberately plain for now — color and thickness are placeholders,
    almost certainly revisited once real visual styling begins.
    """

    COLOR = "#000000"
    THICKNESS = 2

    def __init__(self, master):
        super().__init__(master, fg_color=self.COLOR, corner_radius=0, height=self.THICKNESS)