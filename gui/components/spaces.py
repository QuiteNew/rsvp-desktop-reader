import customtkinter as ctk


class Spaces(ctk.CTkFrame):
    """Space switcher: dropdown (left) to pick a space, current name (center, large), '+' (right)."""

    def __init__(self, master, spaces: list[str], current_space: str, on_select=None, on_add=None):
        super().__init__(master, fg_color="#8E44AD", corner_radius=0)
        self.on_select = on_select
        self.on_add = on_add

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  # left — dropdown
        self.grid_columnconfigure(1, weight=1)  # center — name
        self.grid_columnconfigure(2, weight=1)  # right — "+"

        self.space_menu = ctk.CTkOptionMenu(
            self,
            values=spaces,
            width=32,
            dynamic_resizing=False,
            command=self._handle_select,
        )
        self.space_menu.set("")  # show only the built-in dropdown arrow, no text
        self.space_menu.grid(row=0, column=0, sticky="w", padx=10)

        self.name_label = ctk.CTkLabel(self, text=current_space, font=ctk.CTkFont(size=20, weight="bold"))
        self.name_label.grid(row=0, column=1)

        add_button = ctk.CTkButton(self, text="+", width=32, command=self._handle_add)
        add_button.grid(row=0, column=2, sticky="e", padx=10)

    def set_current_space(self, name: str) -> None:
        self.name_label.configure(text=name)

    def update_spaces(self, spaces: list[str]) -> None:
        """Refresh the dropdown's available choices — call this after a new space is created."""
        self.space_menu.configure(values=spaces)

    def _handle_select(self, selected_name: str) -> None:
        self.space_menu.set("")  # reset the button back to arrow-only after each pick
        if self.on_select:
            self.on_select(selected_name)

    def _handle_add(self) -> None:
        if self.on_add:
            self.on_add()