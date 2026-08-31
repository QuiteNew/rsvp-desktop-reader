import customtkinter as ctk


class AddSpaceDialog(ctk.CTkToplevel):
    """Popup for creating a new space: asks for a name."""

    def __init__(self, master, on_submit):
        super().__init__(master)
        self.title("New Space")
        self.geometry("300x160")
        self.resizable(False, False)
        self.on_submit = on_submit

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        ctk.CTkLabel(self, text="Space name").pack(anchor="w", padx=20, pady=(20, 4))
        self.name_entry = ctk.CTkEntry(self, placeholder_text="e.g. Work")
        self.name_entry.pack(fill="x", padx=20)

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(button_row, text="Cancel", command=self.destroy).pack(side="left")
        ctk.CTkButton(button_row, text="Create", command=self._handle_create).pack(side="right")

    def _handle_create(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            return
        self.on_submit(name)
        self.destroy()