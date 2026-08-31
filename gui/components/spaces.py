import customtkinter as ctk


class Spaces(ctk.CTkFrame):
    """Space switcher: previous/next arrows around the current space name, '+' on the right."""

    def __init__(self, master, current_space: str, on_previous=None, on_next=None, on_add=None):
        super().__init__(master, fg_color="#8E44AD", corner_radius=0)
        self.on_previous = on_previous
        self.on_next = on_next
        self.on_add = on_add

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  # left spacer
        self.grid_columnconfigure(1, weight=1)  # centered cluster
        self.grid_columnconfigure(2, weight=1)  # right — "+"

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=1)

        ctk.CTkButton(center, text="‹", width=24, command=self._handle_previous).pack(side="left", padx=4)
        self.name_label = ctk.CTkLabel(center, text=current_space)
        self.name_label.pack(side="left", padx=8)
        ctk.CTkButton(center, text="›", width=24, command=self._handle_next).pack(side="left", padx=4)

        add_button = ctk.CTkButton(self, text="+", width=28, command=self._handle_add)
        add_button.grid(row=0, column=2, sticky="e", padx=10)

    def set_current_space(self, name: str) -> None:
        self.name_label.configure(text=name)

    def _handle_previous(self) -> None:
        if self.on_previous:
            self.on_previous()

    def _handle_next(self) -> None:
        if self.on_next:
            self.on_next()

    def _handle_add(self) -> None:
        if self.on_add:
            self.on_add()