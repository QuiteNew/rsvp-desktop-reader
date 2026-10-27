import tkinter

import customtkinter as ctk

# How far from the right edge the text of a wrapping label stops, in the same
# logical pixels as every other size in the app. One value for every tab, so the
# descriptions in Settings all end the same distance from the scrollbar or the
# edge of the window, whatever its width.
RIGHT_MARGIN = 20

# What the label wraps at before it has been given a real width. It only shows
# for the moment before the first resize event, and it keeps that first paint
# from being one very long line.
START_WRAP_LENGTH = 360

# Below this the text would be one word per line, which helps nobody, so the
# label stops getting narrower here and lets the window clip instead.
MIN_WRAP_LENGTH = 80


class WrappingLabel(ctk.CTkLabel):
    """A label whose text wraps to the room it actually has, instead of at a
    fixed number of pixels.

    A plain CTkLabel wraps at whatever wraplength it was given. With a fixed
    number the text runs past the edge when the window is narrower than that,
    and leaves a wide empty strip when it is wider. This label watches its own
    width and sets its wraplength to that width minus RIGHT_MARGIN every time it
    changes, so its text always ends the same distance from its right edge.

    Pack it with fill="x" (or grid it with sticky="ew"). Its width then comes
    from its parent, never from its own text, so changing the wrap only changes
    its height and can't start a resize loop.

    Two CustomTkinter details matter here. CTkLabel multiplies wraplength by the
    display scaling, while the width in a resize event is already in real screen
    pixels, so the width is turned back into logical pixels first. And
    CustomTkinter keeps its own <Configure> handler on the label's frame, so this
    one is added next to it with add="+", never in place of it. CTkLabel.bind()
    can't be used for this, because it binds on the inner canvas and text label,
    not on the frame."""

    def __init__(self, master, text="", right_margin=RIGHT_MARGIN, **kwargs):
        kwargs.setdefault("justify", "left")
        kwargs.setdefault("anchor", "w")
        kwargs.setdefault("wraplength", START_WRAP_LENGTH)
        super().__init__(master, text=text, **kwargs)
        self._right_margin = right_margin
        tkinter.Frame.bind(self, "<Configure>", self._rewrap, add="+")

    def _rewrap(self, event=None) -> None:
        width = event.width if event is not None else self.winfo_width()
        if width <= 1:
            return  # not laid out yet; the next resize event will bring the width
        wrap = max(MIN_WRAP_LENGTH, round(self._reverse_widget_scaling(width) - self._right_margin))
        if wrap != self.cget("wraplength"):
            self.configure(wraplength=wrap)