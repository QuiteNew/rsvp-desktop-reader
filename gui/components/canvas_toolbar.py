import customtkinter as ctk

from core.timing import format_duration
from gui.theme import FONT_BODY


class CanvasToolbar(ctk.CTkFrame):
    """Floating-style control row: optionally skip back/forward, an
    optional time-remaining and progress-% read-out, then pause/play,
    restart, and optionally detach + maximize.

    True translucency isn't possible in Tkinter, so this approximates a
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
        show_progress: bool = False,
    ):
        super().__init__(master, fg_color="transparent")
        self.on_skip_back = on_skip_back
        self.on_skip_forward = on_skip_forward
        self.on_pause_toggle = on_pause_toggle
        self.on_restart = on_restart
        self.on_maximize_toggle = on_maximize_toggle
        self.on_detach = on_detach
        self.show_progress = show_progress

        # Order, left to right: [Rewind, Forward,] [Time, %,] Pause, Restart, [Detach,] [Maximize]
        if show_skip:
            self.skip_back_button = self._make_button("<<", self._handle_skip_back)
            self.skip_back_button.pack(side="left", padx=(0, 6))

            self.skip_forward_button = self._make_button(">>", self._handle_skip_forward)
            self.skip_forward_button.pack(side="left", padx=(0, 6))

        # Read-only pills, shaped like the buttons, sitting just left of
        # pause: estimated time remaining, then progress %. Created before
        # the pause button so they land in that order without needing an
        # explicit pack order; set_progress_shown() re-inserts them before
        # pause when toggled back on.
        if show_progress:
            self.time_readout = self._make_readout(64)
            self.time_readout.pack(side="left", padx=(0, 6))
            self.percent_readout = self._make_readout(48)
            self.percent_readout.pack(side="left", padx=(0, 6))

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

    def _make_readout(self, width: int) -> ctk.CTkLabel:
        """A non-interactive pill matching the buttons' glass look, with
        its text centered so it doesn't jump around as the value changes
        width (e.g. "45s" vs "1h 05m")."""
        return ctk.CTkLabel(
            self, text="", width=width, height=28, corner_radius=14,
            fg_color=self.GLASS_COLOR, text_color=("gray20", "gray90"),
            font=ctk.CTkFont(family=FONT_BODY, size=12), anchor="center",
        )

    def set_maximized(self, is_maximized: bool) -> None:
        if hasattr(self, "maximize_button"):
            self.maximize_button.configure(text="> <" if is_maximized else "< >")

    def set_paused(self, is_paused: bool) -> None:
        self.pause_button.configure(text="▶" if is_paused else "⏸")

    def set_progress(self, remaining_ms: int, percent: int) -> None:
        """Update the two read-outs: estimated time remaining (formatted
        H/M/S) and progress percent. A no-op when this toolbar wasn't built
        with show_progress."""
        if not self.show_progress:
            return
        self.time_readout.configure(text=format_duration(max(0, round(remaining_ms / 1000))))
        self.percent_readout.configure(text=f"{percent}%")

    def set_progress_shown(self, shown: bool) -> None:
        """Show or hide the read-outs. Used by the main window, whose
        toolbar stays on screen over the edit box too, so the pills need
        pulling when no session is being read. Re-inserted before the pause
        button (time, then %) so their order is preserved."""
        if not self.show_progress:
            return
        if shown:
            self.time_readout.pack(side="left", padx=(0, 6), before=self.pause_button)
            self.percent_readout.pack(side="left", padx=(0, 6), before=self.pause_button)
        else:
            self.time_readout.pack_forget()
            self.percent_readout.pack_forget()

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