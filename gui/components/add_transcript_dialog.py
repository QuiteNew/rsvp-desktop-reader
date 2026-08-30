import customtkinter as ctk


class AddTranscriptDialog(ctk.CTkToplevel):
    """Popup for creating a new transcript: asks for a title and a space."""

    def __init__(self, master, spaces: list[str], default_space: str, on_submit):
        super().__init__(master)
        self.title("New Transcript")
        self.geometry("340x220")
        self.resizable(False, False)
        self.on_submit = on_submit

        # Keep this popup on top and modal until closed
        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        ctk.CTkLabel(self, text="Title").pack(anchor="w", padx=20, pady=(20, 4))
        self.title_entry = ctk.CTkEntry(self, placeholder_text="e.g. Lecture 3 notes")
        self.title_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Space").pack(anchor="w", padx=20, pady=(16, 4))
        self.space_menu = ctk.CTkOptionMenu(self, values=spaces)
        self.space_menu.set(default_space)
        self.space_menu.pack(fill="x", padx=20)

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(button_row, text="Cancel", command=self.destroy).pack(side="left")
        ctk.CTkButton(button_row, text="Create", command=self._handle_create).pack(side="right")

    def _handle_create(self) -> None:
        title = self.title_entry.get().strip()
        space = self.space_menu.get()
        if not title:
            return  # simplest possible guard for now — real inline validation comes later
        self.on_submit(title, space)
        self.destroy()