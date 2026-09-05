import customtkinter as ctk


class TranscriptListHeader(ctk.CTkFrame):
    """Top of the sidebar: 'List of Transcripts' title and a '+' button."""

    def __init__(self, master, on_add=None):
        super().__init__(master, fg_color="#2C3E50", corner_radius=0)
        self.on_add = on_add

        ctk.CTkLabel(self, text="List of Transcripts").pack(side="left", padx=10)
        ctk.CTkButton(self, text="+", width=28, command=self._handle_add).pack(side="right", padx=10)

    def _handle_add(self) -> None:
        if self.on_add:
            self.on_add()