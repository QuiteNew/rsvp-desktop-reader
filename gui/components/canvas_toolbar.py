import customtkinter as ctk


class CanvasToolbar(ctk.CTkFrame):
    """Floating-style control row: maximize/restore, then detach.

    True translucency isn't possible in Tkinter — this approximates a
    'glass' look with a light, low-contrast fill and soft rounded corners.
    """

    GLASS_COLOR = ("gray85", "gray20")
    GLASS_HOVER = ("gray75", "gray30")

    def __init__(self, master, on_maximize_toggle=None, on_detach=None):
        super().__init__(master, fg_color="transparent")
        self.on_maximize_toggle = on_maximize_toggle
        self.on_detach = on_detach

        self.maximize_button = ctk.CTkButton(
            self, text="< >", width=36, corner_radius=14,
            fg_color=self.GLASS_COLOR, hover_color=self.GLASS_HOVER,
            text_color=("gray20", "gray90"),
            command=self._handle_maximize,
        )
        self.maximize_button.pack(side="left", padx=(0, 6))

        self.detach_button = ctk.CTkButton(
            self, text="↗", width=36, corner_radius=14,
            fg_color=self.GLASS_COLOR, hover_color=self.GLASS_HOVER,
            text_color=("gray20", "gray90"),
            command=self._handle_detach,
        )
        self.detach_button.pack(side="left")

    def set_maximized(self, is_maximized: bool) -> None:
        self.maximize_button.configure(text="> <" if is_maximized else "< >")

    def _handle_maximize(self) -> None:
        if self.on_maximize_toggle:
            self.on_maximize_toggle()

    def _handle_detach(self) -> None:
        if self.on_detach:
            self.on_detach()