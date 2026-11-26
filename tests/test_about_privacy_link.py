"""Tests for the privacy policy link in the About dialog.

The link sits under the project link and has to work exactly like it: the
same look, the same hover, and a click that opens the page in the browser and
nothing else. It also made the dialog one line taller, so one test checks that
everything still fits inside the window.

They open the real dialog over a shown window on one hidden root for the whole
module, the same way test_window_esc.py does, because Tk keeps a window hidden
while its owner is hidden. The browser is never really opened: webbrowser.open
is swapped for a stand-in that only remembers the address."""

import customtkinter as ctk
import pytest

from core.app_info import PRIVACY_URL, REPO_URL
from tk_helpers import cancel_pending_afters, click, settle


@pytest.fixture
def owner(root, wait_until_shown):
    """A shown window to open the dialog over, standing in for Settings."""
    window = ctk.CTkToplevel(root)
    window.geometry("700x700+0+0")
    wait_until_shown(window)
    yield window
    cancel_pending_afters(window)
    window.destroy()


@pytest.fixture
def about(owner, wait_until_shown):
    """The About dialog, on screen and settled, closed again afterwards."""
    from gui.components.about_dialog import AboutDialog

    dialog = AboutDialog(owner)
    wait_until_shown(dialog)
    settle(dialog)
    yield dialog
    if dialog.winfo_exists():
        cancel_pending_afters(dialog)
        dialog.destroy()


@pytest.fixture
def opened(monkeypatch):
    """Every address the dialog asks the browser to open, in order."""
    import webbrowser

    addresses = []
    monkeypatch.setattr(webbrowser, "open", lambda url, *args, **kwargs: addresses.append(url) or True)
    return addresses


def test_the_link_says_privacy_policy_and_sits_under_the_project_link(about):
    link = about._privacy_link
    assert link.cget("text") == "Privacy policy"

    # Same column as the other text, and the very last thing in it.
    column = about._link.master
    assert link.master is column
    assert column.pack_slaves()[-1] is link
    assert column.pack_slaves()[-2] is about._link
    assert link.winfo_y() > about._link.winfo_y()


def test_the_link_looks_like_the_project_link(about):
    link, project = about._privacy_link, about._link
    assert link.cget("cursor") == "hand2"
    assert link.cget("text_color") == about._link_color
    # The very same underlined font, not just one that looks alike. Tk reports
    # underline as 1 rather than True, hence the bool().
    assert link.cget("font") is project.cget("font")
    assert bool(link.cget("font").cget("underline"))


def test_clicking_the_link_opens_the_privacy_policy_and_nothing_else(about, opened):
    # A real press and release on the label inside the link, the widget a
    # CTkLabel's bindings live on (see click() in tk_helpers.py).
    click(about._privacy_link._label)
    about.update()
    assert opened == [PRIVACY_URL]
    assert about.winfo_exists()


def test_the_project_link_still_opens_the_project(about, opened):
    click(about._link._label)
    about.update()
    assert opened == [REPO_URL]


def test_the_link_darkens_while_the_pointer_is_over_it(about):
    """The same check as the project link's in test_gui_smoke.py. The
    handlers are called directly, because Tk can drop generated Enter and
    Leave events on some machines."""
    from gui.theme import COCOA_INK

    link = about._privacy_link
    assert "_show_privacy_link_hovered" in link._label.bind("<Enter>")
    assert "_show_privacy_link_resting" in link._label.bind("<Leave>")

    about._show_privacy_link_hovered()
    assert link.cget("text_color") == COCOA_INK
    about._show_privacy_link_resting()
    assert link.cget("text_color") == about._link_color


def test_hovering_one_link_leaves_the_other_alone(about):
    about._show_privacy_link_hovered()
    assert about._link.cget("text_color") == about._link_color
    about._show_privacy_link_resting()

    about._show_link_hovered()
    assert about._privacy_link.cget("text_color") == about._link_color
    about._show_link_resting()


def test_everything_still_fits_in_the_dialog(about):
    """The extra line made the dialog taller. If it hadn't, the Close button
    would be squeezed against the bottom edge or cut off."""
    assert about.winfo_reqheight() <= about.winfo_height()
    assert about.winfo_reqwidth() <= about.winfo_width()
