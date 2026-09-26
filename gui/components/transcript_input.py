import customtkinter as ctk


class TranscriptInput(ctk.CTkFrame):
    """Paste-in prompt shown when the selected transcript has no text yet."""

    def __init__(self, master, on_submit, initial_text: str = ""):
        super().__init__(master, fg_color="transparent")
        self.on_submit = on_submit

        self.textbox = ctk.CTkTextbox(self, width=500, height=250)
        self.textbox.pack(padx=20, pady=20, fill="both", expand=True)
        if initial_text:
            self.textbox.insert("1.0", initial_text)

        self.start_button = ctk.CTkButton(self, text="Start reading", command=self._handle_submit)
        self.start_button.pack(pady=(0, 20))

    def get_text(self) -> str:
        """Return whatever's currently typed, submitted or not."""
        return self.textbox.get("1.0", "end")

    def set_text(self, text: str) -> None:
        """Replace the textbox's contents."""
        self.textbox.delete("1.0", "end")
        if text:
            self.textbox.insert("1.0", text)

    def _handle_submit(self) -> None:
        self.on_submit(self.get_text())