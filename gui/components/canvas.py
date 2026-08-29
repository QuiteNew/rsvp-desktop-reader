import customtkinter as ctk


class Canvas(ctk.CTkFrame):
    """Largest section — where words will eventually flash."""

    def __init__(self, master):
        super().__init__(master, fg_color="#2ECC71", corner_radius=0)
        ctk.CTkLabel(self, text="RSVP reading canvas").pack(expand=True)