import customtkinter as ctk
from gui.icons import power_icon


class StopButton(ctk.CTkFrame):
    """Single floating-style button that ends the current reading session
    early and returns to the transcript's paste-in screen — without
    touching saved position, pause state, or the transcript's stored text.
    """

    GLASS_COLOR = ("gray85", "gray20")
    GLASS_HOVER = ("gray75", "gray30")

    def __init__(self, master, on_stop=None):
        super().__init__(master, fg_color="transparent")
        self.on_stop = on_stop

        self.button = ctk.CTkButton(
            self, text="", image=power_icon(), width=36, corner_radius=14,
            fg_color=self.GLASS_COLOR, hover_color=self.GLASS_HOVER,
            command=self._handle_stop,
        )
        self.button.pack()

    def _handle_stop(self) -> None:
        if self.on_stop:
            self.on_stop()