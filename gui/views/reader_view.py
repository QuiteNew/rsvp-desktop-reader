import customtkinter as ctk


class ReaderView(ctk.CTkFrame):
    """View that displays the flashing word and playback controls."""

    def __init__(self, master, on_back):
        super().__init__(master)
        self.on_back = on_back

        self.word_label = ctk.CTkLabel(self, text="(word will appear here)", font=("Arial", 32))
        self.word_label.pack(expand=True)

        self.back_button = ctk.CTkButton(self, text="Back", command=self.on_back)
        self.back_button.pack(pady=20)

    def set_word(self, text: str) -> None:
        """Update the displayed word text. Placeholder until real ORP rendering exists."""
        self.word_label.configure(text=text)