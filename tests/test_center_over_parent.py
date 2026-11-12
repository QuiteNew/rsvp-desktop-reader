"""center_over_parent() in gui/theme.py on scaled displays.

On a display scaled to 125%, 150% or 200%, CustomTkinter's geometry() makes a
window that many times bigger on screen but leaves its position alone. Popups
were centred with their unscaled size, so they landed too far right and too far
down, by half of the extra size. At 200% the Chunking window ran off the bottom
of the screen. These tests set CustomTkinter's window scaling on top of
whatever the display already has, the same thing a more scaled display does,
and check the popup is placed so that its middle is on its parent's middle.

What's checked is the corner the popup was placed at, read back from Tk, and
not where its inside ends up. On Windows the title bar and border sit between
the two, and they'd move the inside by their own size whatever the scaling."""

import tkinter as tk

import customtkinter as ctk
import pytest
from customtkinter import ScalingTracker

from gui.theme import center_over_parent

from tk_helpers import settle


@pytest.fixture
def scaled(root):
    """Sets CustomTkinter's window scaling for one test and puts it back to 1
    afterwards, since it applies to every window in the process."""
    def set_scaling(scale):
        ctk.set_window_scaling(scale)
        root.update()

    yield set_scaling
    ctk.set_window_scaling(1)
    root.update()


@pytest.fixture
def parent(root, wait_until_shown):
    window = ctk.CTkToplevel(root)
    window.geometry("300x250+60+40")
    wait_until_shown(window)
    yield window
    window.destroy()


def _placed_at(window):
    """The corner Tk was asked to put the window at, in screen pixels."""
    _size, x, y = window.tk.call("wm", "geometry", window._w).replace("+", " ").split()
    return int(x), int(y)


def _middle_spot(parent, popup):
    """Where popup's corner goes to put its middle on parent's middle."""
    return (
        parent.winfo_rootx() + (parent.winfo_width() - popup.winfo_width()) // 2,
        parent.winfo_rooty() + (parent.winfo_height() - popup.winfo_height()) // 2,
    )


@pytest.mark.parametrize("scale", [1, 1.25, 1.5, 2])
def test_a_popup_is_placed_in_the_middle_of_its_parent(root, parent, wait_until_shown, scaled, scale):
    scaled(scale)
    settle(parent, 50)
    popup = ctk.CTkToplevel(parent)
    try:
        center_over_parent(popup, 200, 120)
        wait_until_shown(popup)
        settle(popup, 50)

        on_screen = ScalingTracker.get_window_scaling(popup)
        assert popup.winfo_width() == round(200 * on_screen)
        assert popup.winfo_height() == round(120 * on_screen)
        assert _placed_at(popup) == _middle_spot(parent, popup)
    finally:
        popup.destroy()


def test_a_popup_bigger_than_its_parent_still_starts_on_screen(root, wait_until_shown, scaled):
    # The parent's corner is near the screen's, so centring the much bigger
    # popup would put its corner above and left of the screen.
    scaled(2)
    small = ctk.CTkToplevel(root)
    small.geometry("100x80+5+5")
    wait_until_shown(small)
    popup = ctk.CTkToplevel(small)
    try:
        center_over_parent(popup, 400, 300)
        wait_until_shown(popup)
        settle(popup, 50)
        assert _placed_at(popup) == (0, 0)
    finally:
        popup.destroy()
        small.destroy()


def test_a_window_customtkinter_does_not_scale_is_centred_at_its_own_size(root, parent, wait_until_shown, scaled):
    # A plain Tk window isn't scaled by CustomTkinter, so its size is used as
    # it is, the way every popup used to be centred. It's wider than the other
    # popups here because Windows won't make a window with a title bar
    # narrower than its own minimum, which grows with the display's scaling
    # (a 200 wide one came out 232 wide at 200%), and CustomTkinter's scaling
    # doesn't make this one any bigger to clear it.
    scaled(2)
    settle(parent, 50)
    plain = tk.Toplevel(parent)
    try:
        center_over_parent(plain, 500, 300)
        wait_until_shown(plain)
        settle(plain, 50)
        assert (plain.winfo_width(), plain.winfo_height()) == (500, 300)
        assert _placed_at(plain) == _middle_spot(parent, plain)
    finally:
        plain.destroy()
