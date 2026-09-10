import customtkinter as ctk


class CanvasToolbar(ctk.CTkFrame):
    """Floating-style control row: optionally skip back/forward, then
    pause/play, restart, and optionally detach + maximize.

    True translucency isn't possible in Tkinter — this approximates a
    'glass' look with a light, low-contrast fill and soft rounded corners.
    """

    GLASS_COLOR = ("gray85", "gray20")
    GLASS_HOVER = ("gray75", "gray30")

    def __init__(
        self,
        master,
        on_skip_back=None,
        on_skip_forward=None,
        on_pause_toggle=None,
        on_restart=None,
        on_maximize_toggle=None,
        on_detach=None,
        show_skip: bool = False,
        show_maximize: bool = True,
        show_detach: bool = True,
    ):
        super().__init__(master, fg_color="transparent")
        self.on_skip_back = on_skip_back
        self.on_skip_forward = on_skip_forward
        self.on_pause_toggle = on_pause_toggle
        self.on_restart = on_restart
        self.on_maximize_toggle = on_maximize_toggle
        self.on_detach = on_detach

        # Order: [Rewind, Forward,] Pause, Restart, [Detach,] [Maximize] — left to right
        if show_skip:
            self.skip_back_button = self._make_button("<<", self._handle_skip_back)
            self.skip_back_button.pack(side="left", padx=(0, 6))

            self.skip_forward_button = self._make_button(">>", self._handle_skip_forward)
            self.skip_forward_button.pack(side="left", padx=(0, 6))

        self.pause_button = self._make_button("⏸", self._handle_pause_toggle)
        self.pause_button.pack(side="left", padx=(0, 6))

        self.restart_button = self._make_button("⟳", self._handle_restart)
        self.restart_button.pack(side="left", padx=(0, 6))

        if show_detach:
            self.detach_button = self._make_button("↗", self._handle_detach)
            self.detach_button.pack(side="left", padx=(0, 6))

        if show_maximize:
            self.maximize_button = self._make_button("< >", self._handle_maximize)
            self.maximize_button.pack(side="left")

    def _make_button(self, text: str, command) -> ctk.CTkButton:
        return ctk.CTkButton(
            self, text=text, width=36, corner_radius=14,
            fg_color=self.GLASS_COLOR, hover_color=self.GLASS_HOVER,
            text_color=("gray20", "gray90"),
            command=command,
        )

    def set_maximized(self, is_maximized: bool) -> None:
        if hasattr(self, "maximize_button"):
            self.maximize_button.configure(text="> <" if is_maximized else "< >")

    def set_paused(self, is_paused: bool) -> None:
        self.pause_button.configure(text="▶" if is_paused else "⏸")

    def _handle_skip_back(self) -> None:
        if self.on_skip_back:
            self.on_skip_back()

    def _handle_skip_forward(self) -> None:
        if self.on_skip_forward:
            self.on_skip_forward()

    def _handle_pause_toggle(self) -> None:
        if self.on_pause_toggle:
            self.on_pause_toggle()

    def _handle_restart(self) -> None:
        if self.on_restart:
            self.on_restart()

    def _handle_maximize(self) -> None:
        if self.on_maximize_toggle:
            self.on_maximize_toggle()

    def _handle_detach(self) -> None:
        if self.on_detach:
            self.on_detach()