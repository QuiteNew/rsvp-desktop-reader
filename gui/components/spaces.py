import customtkinter as ctk


class Spaces(ctk.CTkFrame):
    """Space switcher: current space name (centered) with a '+' to add a new one."""

    def __init__(self, master, current_space: str, on_add=None):
        super().__init__(master, fg_color="#8E44AD", corner_radius=0)
        self.on_add = on_add

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  # left spacer — balances the button's column
        self.grid_columnconfigure(1, weight=1)  # centered label
        self.grid_columnconfigure(2, weight=1)  # right — holds the "+" button

        self.name_label = ctk.CTkLabel(self, text=current_space)
        self.name_label.grid(row=0, column=1)

        add_button = ctk.CTkButton(self, text="+", width=28, command=self._handle_add)
        add_button.grid(row=0, column=2, sticky="e", padx=10)

    def set_current_space(self, name: str) -> None:
        """Update the displayed space name after switching or creating one."""
        self.name_label.configure(text=name)

    def _handle_add(self) -> None:
        if self.on_add:
            self.on_add()