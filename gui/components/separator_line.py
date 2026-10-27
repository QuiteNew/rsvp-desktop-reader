import tkinter

from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

# The line is plain black in both themes. It is meant to look the same whatever
# the theme, so it doesn't come from gui/theme.py's palette.
LINE_COLOR = "#000000"

# How much of the row's width the line takes, centred, so it never touches the
# sides of the window.
WIDTH_FRACTION = 0.6

# Thickness of the line, in logical pixels, the same unit as every other size in
# the app. It is turned into real screen pixels by the display scaling (see
# _scale()), and so is the space around the line.
THICKNESS = 1

# The space wanted on each side of the line, between the explanation above it
# and the setting below it. Each place that adds a line says how much of that
# its neighbours already give, so the line sits in the middle of the gap.
GAP = 20


class SeparatorLine(tkinter.Frame):
    """A thin black line, centred under a setting's explanation, that keeps the
    settings in a long list apart.

    It is a plain tkinter.Frame and not a CTkFrame. CustomTkinter draws its
    frames on a canvas, and that drawing doesn't show anything at 1 pixel thick
    (the same thing that once hid the horizontal guide ticks), while a plain
    frame with a background colour always paints. The cost is that Tk doesn't
    scale a plain frame for the display, so this does it itself: the thickness
    and the space around it are multiplied by the scaling CustomTkinter uses for
    the window the line is in, and the width is a share of its parent's width.

    Pack it straight after the explanation it goes under. above and below are
    the extra space it adds on each side, on top of what the explanation and
    the next setting already leave, so that the line ends up GAP away from
    both. It packs itself (pack_line()) so that space is always the scaled one,
    and the width is kept up to date by watching the parent's size, added next
    to whatever the parent already listens for, never in its place. It has no
    children, so it keeps the size it is given."""

    def __init__(self, master, above=0, below=GAP):
        super().__init__(master, bg=LINE_COLOR, highlightthickness=0, borderwidth=0)
        self._above = above
        self._below = below
        self._scale_used = None
        tkinter.Frame.bind(master, "<Configure>", self._fit_to_parent, add="+")

    def pack_line(self) -> None:
        """Show the line, with the scaled space around it. Safe to call again
        after pack_forget(); the line goes back to the end of its parent, which
        is where it belongs, under the explanation."""
        scale = self._scale()
        self.configure(height=self._thickness(scale))
        self.pack(pady=self._pady(scale))
        self._scale_used = scale
        self._fit_to_parent()

    def _thickness(self, scale: float) -> int:
        return max(1, round(THICKNESS * scale))

    def _pady(self, scale: float) -> tuple[int, int]:
        return round(self._above * scale), round(self._below * scale)

    def _scale(self) -> float:
        try:
            return ScalingTracker.get_widget_scaling(self)
        except KeyError:
            return 1.0  # not inside a CustomTkinter window, which the app never does

    def _fit_to_parent(self, event=None) -> None:
        if not self.winfo_exists():
            return
        width = event.width if event is not None else self.master.winfo_width()
        if width <= 1:
            return  # not laid out yet; the parent's next resize brings the width
        self.configure(width=max(1, round(width * WIDTH_FRACTION)))
        # A change of display scaling resizes the parent too, so this is also
        # where a thickness and space set for the old scaling are brought up to
        # date. Only while the line is shown: a hidden one gets them in
        # pack_line().
        scale = self._scale()
        if scale != self._scale_used and self.winfo_manager() == "pack":
            self.configure(height=self._thickness(scale))
            self.pack_configure(pady=self._pady(scale))
            self._scale_used = scale