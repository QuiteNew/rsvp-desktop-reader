"""Tests for Esc in the app's bigger windows: Settings, the chunking window,
About and the space picker (the small popups are in test_dialog_keys.py).

What was agreed: Esc does what each window's Close does, and nothing more. No
window gets an Enter, so a key press can never apply settings or switch a space
by accident. In the space picker, Esc while a name is being edited only cancels
the edit, and the window stays open.

They run against a real Tk with one hidden root for the whole module, and each
window is opened from a shown window, because Tk keeps a window hidden while its
owner is hidden."""

import customtkinter as ctk
import pytest

from tk_helpers import settings_window


class Calls:
    """Remembers every call made to it, with its arguments."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)


@pytest.fixture
def owner(root, wait_until_shown):
    """A shown window to open the windows over, standing in for the main
    window. Its own Esc records here, so a test can check that Esc in a window
    doesn't also reach the one behind it (Esc there stops reading)."""
    window = ctk.CTkToplevel(root)
    window.geometry("700x700+0+0")
    wait_until_shown(window)
    window.behind = Calls()
    window.bind("<Escape>", lambda event: window.behind("Escape"))
    yield window
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()


@pytest.fixture
def shown(wait_until_shown):
    def show(window):
        wait_until_shown(window)
        if window.focus_get() is None:
            window.focus_force()
            window.update()
        return window

    return show


def press(window, key, target=None):
    """Send a key to a widget in the window, by default whatever has the
    keyboard there, the way a real key press arrives."""
    target = target or window.focus_get() or window
    target.event_generate(f"<{key}>")
    if window.winfo_exists():
        window.update()


def is_open(window) -> bool:
    return bool(window.winfo_exists())


def close_if_open(window) -> None:
    if window.winfo_exists():
        for timer in window.tk.splitlist(window.tk.call("after", "info")):
            window.tk.call("after", "cancel", timer)
        window.destroy()


# ---- Settings ----

def make_settings(owner):
    applied = Calls()
    return settings_window(owner, on_apply=applied), applied


def test_esc_closes_settings_without_applying(owner, shown):
    window, applied = make_settings(owner)
    shown(window)
    window._set_entry_value(window.window_width_entry, 1200)
    press(window, "Escape")
    assert not is_open(window)
    assert applied.calls == []


def test_esc_closes_settings_from_the_search_box_too(owner, shown):
    """The keys belong to the whole window, so Esc works wherever the cursor
    is, here in the Defaults search box."""
    window, _ = make_settings(owner)
    shown(window)
    search_entry = window._defaults_search._entry
    search_entry.focus_set()
    window.update()
    press(window, "Escape", target=search_entry)
    assert not is_open(window)


def test_enter_does_not_apply_settings(owner, shown):
    window, applied = make_settings(owner)
    shown(window)
    press(window, "Return")
    assert applied.calls == []
    assert is_open(window)
    close_if_open(window)


def test_esc_in_settings_does_not_reach_the_main_window(owner, shown):
    window, _ = make_settings(owner)
    shown(window)
    press(window, "Escape")
    assert owner.behind.calls == []


# ---- the chunking window ----

def make_chunking(owner):
    from gui.components.chunking_settings_window import ChunkingSettingsWindow

    applied = Calls()
    window = ChunkingSettingsWindow(
        owner, default_enabled=False, default_size=2, default_mode="fixed", default_char_target=14,
        transcript=None, on_apply=applied,
    )
    return window, applied


def test_esc_closes_the_chunking_window_without_applying(owner, shown):
    window, applied = make_chunking(owner)
    shown(window)
    press(window, "Escape")
    assert not is_open(window)
    assert applied.calls == []


def test_enter_does_not_apply_chunking(owner, shown):
    window, applied = make_chunking(owner)
    shown(window)
    press(window, "Return")
    assert applied.calls == []
    assert is_open(window)
    close_if_open(window)


# ---- About ----

def test_esc_closes_about_and_hands_back_to_settings(owner, shown):
    """Its Close button calls on_close, which lets Settings take back the input
    grab. Esc has to do the same."""
    from gui.components.about_dialog import AboutDialog

    closed = Calls()
    window = AboutDialog(owner, on_close=closed)
    shown(window)
    press(window, "Escape")
    assert not is_open(window)
    assert closed.calls == [()]


# ---- the space picker ----

def make_space_picker(owner):
    from gui.components.space_selection_dialog import SpaceSelectionDialog

    selected = Calls()
    renamed = Calls()

    def rename(old, new):
        renamed(old, new)
        return True

    window = SpaceSelectionDialog(
        owner, spaces=["General", "Work"], current_space="General",
        on_select=selected, on_rename_requested=rename, on_delete_requested=Calls(),
    )
    window.renamed = renamed
    return window, selected


def rename_entries(window):
    from customtkinter import CTkEntry

    found = []

    def walk(widget):
        for child in widget.winfo_children():
            if isinstance(child, CTkEntry):
                found.append(child)
            walk(child)

    walk(window)
    return found


def start_renaming(window):
    """Start editing the first space's name with its pencil button, and
    return the box being typed in."""
    from customtkinter import CTkButton

    def walk(widget):
        for child in widget.winfo_children():
            yield child
            yield from walk(child)

    pencil = next(w for w in walk(window) if isinstance(w, CTkButton) and w.cget("text") == "✎")
    pencil.invoke()
    window.update()
    entry = next(e for e in rename_entries(window) if e.winfo_ismapped())
    return entry


def test_esc_closes_the_space_picker_without_switching(owner, shown):
    window, selected = make_space_picker(owner)
    shown(window)
    press(window, "Escape")
    assert not is_open(window)
    assert selected.calls == []


def test_esc_while_renaming_only_cancels_the_rename(owner, shown):
    window, _ = make_space_picker(owner)
    shown(window)
    entry = start_renaming(window)
    entry.delete(0, "end")
    entry.insert(0, "Renamed")
    press(window, "Escape", target=entry._entry)

    assert is_open(window), "Esc closed the window instead of only cancelling the rename"
    assert not entry.winfo_ismapped()
    assert window.renamed.calls == []

    press(window, "Escape")
    assert not is_open(window)