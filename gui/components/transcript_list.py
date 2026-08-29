import customtkinter as ctk


class TranscriptList(ctk.CTkFrame):
    """List of saved transcripts, with a '+' button to add a new one."""

    def __init__(self, master, on_add=None):
        super().__init__(master, fg_color="#2C3E50", corner_radius=0)
        self.on_add = on_add

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(header, text="List of Transcripts").pack(side="left")
        ctk.CTkButton(header, text="+", width=28, command=self._handle_add).pack(side="right")

    def _handle_add(self) -> None:
        # Placeholder — real "add transcript" flow gets wired once we decide where it lives
        if self.on_add:
            self.on_add()
        else:
            print("Add transcript clicked (placeholder)")