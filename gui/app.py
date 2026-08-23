import customtkinter as ctk


class RSVPApp(ctk.CTk):
    """Main application window for the RSVP reader."""

    def __init__(self):
        super().__init__()
        self.title("RSVP Reader")
        self.geometry("600x400")