"""Tests for Enter and Esc in the app's small popups
(gui/components/dialog_keys.py and the popups that use it).

What was agreed:

- Esc does what the popup's Cancel or close button does, in every popup.
- Enter only where there is one safe answer: creating a space or a transcript
  from what was just typed, saving a profile name, and closing a message.
- The popups that delete or replace something get no Enter at all, so a stray
  key can never confirm them.
- New Space, New Transcript and the profile name popup put the cursor in
  their name box, so the name can be typed straight away.

The keys are sent the way a key press arrives: to the widget that has the
keyboard, which is the popup's text box where it has one. They run against a
real Tk with one hidden root for the whole module, and each popup is opened
from a shown window, because Tk keeps a popup hidden while its owner is
hidden."""

import sys
import tkinter

import customtkinter as ctk
import pytest

# The number pad's Enter key. On Windows, Tk reports it as Return, the same as
# the main Enter key, so there is no separate key to send there and the Return
# tests already cover it. Elsewhere it arrives as KP_Enter, which the popups
# bind as well.
ON_WINDOWS = sys.platform == "win32"
NO_SEPARATE_NUMBER_PAD_ENTER = "Windows reports the number pad Enter as Return"
NUMBER_PAD_ENTER = pytest.param(
    "KP_Enter", marks=pytest.mark.skipif(ON_WINDOWS, reason=NO_SEPARATE_NUMBER_PAD_ENTER),
)


@pytest.fixture(scope="module")
def root(fresh_widget_image_caches):
    """The popups set the app icon, and that picture is kept for the Tk root it
    was made in, so the cache is emptied around this module's root."""
    try:
        window = ctk.CTk()
    except tkinter.TclError:
        pytest.skip("no display available for Tk")
    window.withdraw()
    yield window
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()
    fresh_widget_image_caches()


class Calls:
    """Remembers every call made to it, with its arguments."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)


@pytest.fixture
def owner(root, wait_until_shown):
    """A shown window for the popups to open over, standing in for the main
    window. Anything bound to it records here, so a test can check that a key
    pressed in a popup doesn't also reach the window behind it."""
    window = ctk.CTkToplevel(root)
    window.geometry("600x500+0+0")
    wait_until_shown(window)
    window.behind = Calls()
    window.bind("<Escape>", lambda event: window.behind("Escape"))
    window.bind("<Return>", lambda event: window.behind("Return"))
    yield window
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()


@pytest.fixture
def shown(wait_until_shown):
    """Shows a popup and gives it the keyboard the way a person clicking into
    it would, then returns it."""
    def show(dialog):
        wait_until_shown(dialog)
        if dialog.focus_get() is None:
            dialog.focus_force()
            dialog.update()
        return dialog

    return show


def press(dialog, key):
    """Send a key to whatever has the keyboard in this popup, the way a real
    key press arrives."""
    target = dialog.focus_get() or dialog
    target.event_generate(f"<{key}>")
    if dialog.winfo_exists():
        dialog.update()


def is_open(dialog) -> bool:
    return bool(dialog.winfo_exists())


def typing_goes_to(dialog, entry) -> bool:
    return entry._entry.focus_lastfor() is entry._entry


# ---- New Space ----

def make_add_space(owner):
    from gui.components.add_space_dialog import AddSpaceDialog

    submitted = Calls()
    return AddSpaceDialog(owner, on_submit=submitted), submitted


def test_new_space_puts_the_cursor_in_the_name_box(owner, shown):
    dialog, _ = make_add_space(owner)
    shown(dialog)
    assert typing_goes_to(dialog, dialog.name_entry)


def test_enter_in_new_space_creates_it(owner, shown):
    dialog, submitted = make_add_space(owner)
    shown(dialog)
    dialog.name_entry.insert(0, "Work")
    press(dialog, "Return")
    assert submitted.calls == [("Work",)]
    assert not is_open(dialog)


@pytest.mark.skipif(ON_WINDOWS, reason=NO_SEPARATE_NUMBER_PAD_ENTER)
def test_the_number_pad_enter_works_too(owner, shown):
    dialog, submitted = make_add_space(owner)
    shown(dialog)
    dialog.name_entry.insert(0, "Work")
    press(dialog, "KP_Enter")
    assert submitted.calls == [("Work",)]


def test_enter_with_no_name_does_nothing(owner, shown):
    dialog, submitted = make_add_space(owner)
    shown(dialog)
    press(dialog, "Return")
    assert submitted.calls == []
    assert is_open(dialog)
    dialog.destroy()


def test_esc_in_new_space_cancels(owner, shown):
    dialog, submitted = make_add_space(owner)
    shown(dialog)
    dialog.name_entry.insert(0, "Work")
    press(dialog, "Escape")
    assert submitted.calls == []
    assert not is_open(dialog)


def test_a_key_in_a_popup_does_not_reach_the_window_behind_it(owner, shown):
    """Esc in the main window stops reading. Pressed in a popup, it must only
    close the popup."""
    dialog, _ = make_add_space(owner)
    shown(dialog)
    press(dialog, "Escape")
    assert owner.behind.calls == []


# ---- New Transcript ----

def make_add_transcript(owner, **kwargs):
    from gui.components.add_transcript_dialog import AddTranscriptDialog

    submitted = Calls()
    dialog = AddTranscriptDialog(owner, spaces=["General", "Work"], default_space="Work", on_submit=submitted, **kwargs)
    return dialog, submitted


def test_new_transcript_puts_the_cursor_in_the_title_box(owner, shown):
    dialog, _ = make_add_transcript(owner)
    shown(dialog)
    assert typing_goes_to(dialog, dialog.title_entry)
    assert not dialog.title_entry._entry.selection_present()


def test_a_title_from_a_file_is_selected_so_typing_replaces_it(owner, shown):
    dialog, _ = make_add_transcript(owner, initial_title="lecture-03")
    shown(dialog)
    assert typing_goes_to(dialog, dialog.title_entry)
    assert dialog.title_entry._entry.selection_present()
    assert dialog.title_entry.get() == "lecture-03"
    dialog.destroy()


def test_enter_in_new_transcript_creates_it_in_the_chosen_space(owner, shown):
    dialog, submitted = make_add_transcript(owner)
    shown(dialog)
    dialog.title_entry.insert(0, "Lecture 3")
    press(dialog, "Return")
    assert submitted.calls == [("Lecture 3", "Work")]
    assert not is_open(dialog)


def test_esc_in_new_transcript_cancels(owner, shown):
    dialog, submitted = make_add_transcript(owner)
    shown(dialog)
    dialog.title_entry.insert(0, "Lecture 3")
    press(dialog, "Escape")
    assert submitted.calls == []
    assert not is_open(dialog)


# ---- the keyboard handed back late, as on a busy Windows machine ----

def with_late_hand_back(dialog_class, behind):
    """The popup class, changed to do what CustomTkinter does on Windows at
    its latest: hand the keyboard back to the window behind 10 ms after the
    popup is revealed (see focus_for_typing() in gui/components/dialog_keys.py).
    The cursor must still end up in the popup's box."""
    class LateHandBack(dialog_class):
        def _reveal_now(self):
            super()._reveal_now()
            self.after(10, behind.focus_force)

    return LateHandBack


def keyboard_is_in(dialog, entry) -> bool:
    focused = dialog.focus_get()
    if focused is None:
        pytest.skip("this machine didn't give the test window the keyboard")
    return focused is entry._entry


def test_new_space_keeps_the_cursor_when_the_keyboard_is_handed_back_late(owner, shown):
    from gui.components.add_space_dialog import AddSpaceDialog

    behind = ctk.CTkEntry(owner)
    behind.pack()
    dialog = with_late_hand_back(AddSpaceDialog, behind)(owner, on_submit=Calls())
    shown(dialog)
    assert keyboard_is_in(dialog, dialog.name_entry)
    dialog.destroy()


def test_a_file_title_stays_selected_when_the_keyboard_is_handed_back_late(owner, shown):
    from gui.components.add_transcript_dialog import AddTranscriptDialog

    behind = ctk.CTkEntry(owner)
    behind.pack()
    dialog = with_late_hand_back(AddTranscriptDialog, behind)(
        owner, spaces=["General"], default_space="General", on_submit=Calls(), initial_title="lecture-03",
    )
    shown(dialog)
    assert keyboard_is_in(dialog, dialog.title_entry)
    assert dialog.title_entry._entry.selection_present()
    dialog.destroy()


# ---- the popups that delete or replace something: Esc only ----

def make_delete_transcript(owner):
    from gui.components.delete_transcript_dialog import DeleteTranscriptDialog

    confirmed = Calls()
    return DeleteTranscriptDialog(owner, transcript_title="Lecture 3", on_confirm=confirmed), confirmed


def make_delete_space(owner):
    from gui.components.delete_space_dialog import DeleteSpaceDialog

    confirmed = Calls()
    return DeleteSpaceDialog(owner, space_name="Work", on_confirm=confirmed), confirmed


def make_import_confirm(owner):
    from gui.components.import_confirm_dialog import ImportConfirmDialog

    chosen = Calls()
    return ImportConfirmDialog(owner, on_replace=lambda: chosen("replace"), on_expand=lambda: chosen("expand")), chosen


def make_profile_confirm(owner):
    from gui.components.profile_confirm_dialog import ProfileConfirmDialog

    confirmed = Calls()
    closed = Calls()
    dialog = ProfileConfirmDialog(
        owner, "Delete profile", "Delete the profile?", "Delete",
        on_confirm=confirmed, destructive=True, on_close=closed,
    )
    dialog.closed = closed
    return dialog, confirmed


def make_chooser(owner):
    from gui.components.add_transcript_chooser_dialog import AddTranscriptChooserDialog

    chosen = Calls()
    return AddTranscriptChooserDialog(
        owner, on_choose_blank=lambda: chosen("blank"), on_choose_file=lambda: chosen("file"),
    ), chosen


def make_move(owner):
    from gui.components.move_transcript_dialog import MoveTranscriptDialog

    selected = Calls()
    return MoveTranscriptDialog(owner, transcript_title="Lecture 3", other_spaces=["Work"], on_select=selected), selected


ESC_ONLY = {
    "delete transcript": make_delete_transcript,
    "delete space": make_delete_space,
    "import": make_import_confirm,
    "move transcript": make_move,
    "profile confirm": make_profile_confirm,
    "add transcript chooser": make_chooser,
}


@pytest.mark.parametrize("name", ESC_ONLY)
@pytest.mark.parametrize("key", ["Return", NUMBER_PAD_ENTER])
def test_enter_does_nothing_where_there_is_no_safe_answer(owner, shown, name, key):
    dialog, acted = ESC_ONLY[name](owner)
    shown(dialog)
    press(dialog, key)
    assert acted.calls == [], f"Enter did something in {name}"
    assert is_open(dialog), f"Enter closed {name}"
    dialog.destroy()


@pytest.mark.parametrize("name", ESC_ONLY)
def test_esc_closes_without_doing_anything(owner, shown, name):
    dialog, acted = ESC_ONLY[name](owner)
    shown(dialog)
    press(dialog, "Escape")
    assert acted.calls == [], f"Esc did something in {name}"
    assert not is_open(dialog), f"Esc did not close {name}"


def test_esc_in_the_profile_confirm_still_hands_back_to_settings(owner, shown):
    """Its Cancel button calls on_close, which lets Settings take back the
    input grab. Esc has to do the same."""
    dialog, _ = make_profile_confirm(owner)
    shown(dialog)
    press(dialog, "Escape")
    assert dialog.closed.calls == [()]


# ---- a message ----

def make_message(owner):
    from gui.components.message_dialog import MessageDialog

    closed = Calls()
    return MessageDialog(owner, "Export complete", "Your data was exported.", on_close=closed), closed


@pytest.mark.parametrize("key", ["Return", NUMBER_PAD_ENTER, "Escape"])
def test_enter_and_esc_close_a_message_like_its_button(owner, shown, key):
    """on_close runs however the message is closed: after an import it closes
    the app, which has to happen whichever way the message goes."""
    dialog, closed = make_message(owner)
    shown(dialog)
    press(dialog, key)
    assert not is_open(dialog)
    assert closed.calls == [()]


# ---- a profile name ----

def make_profile_name(owner, existing=(), initial_name=""):
    from gui.components.profile_name_dialog import ProfileNameDialog

    submitted = Calls()
    closed = Calls()
    dialog = ProfileNameDialog(
        owner, "Save profile", "Save", existing_names=list(existing),
        on_submit=submitted, on_close=closed, initial_name=initial_name,
    )
    dialog.closed = closed
    return dialog, submitted


def test_the_profile_name_popup_puts_the_cursor_in_the_box(owner, shown):
    dialog, _ = make_profile_name(owner)
    shown(dialog)
    assert typing_goes_to(dialog, dialog.name_entry)
    dialog.destroy()


def test_renaming_selects_the_current_name_so_typing_replaces_it(owner, shown):
    dialog, _ = make_profile_name(owner, initial_name="Fast skim")
    shown(dialog)
    assert typing_goes_to(dialog, dialog.name_entry)
    assert dialog.name_entry._entry.selection_present()
    dialog.destroy()


def test_the_profile_name_keeps_the_cursor_when_the_keyboard_is_handed_back_late(owner, shown):
    from gui.components.profile_name_dialog import ProfileNameDialog

    behind = ctk.CTkEntry(owner)
    behind.pack()
    dialog = with_late_hand_back(ProfileNameDialog, behind)(
        owner, "Rename profile", "Rename", existing_names=[], on_submit=Calls(), initial_name="Fast skim",
    )
    shown(dialog)
    assert keyboard_is_in(dialog, dialog.name_entry)
    assert dialog.name_entry._entry.selection_present()
    dialog.destroy()


def test_enter_saves_a_profile_name_once(owner, shown):
    """Enter moved from the name box to the popup. It still saves, and only
    once."""
    dialog, submitted = make_profile_name(owner)
    shown(dialog)
    dialog.name_entry.insert(0, "Fast skim")
    press(dialog, "Return")
    assert submitted.calls == [("Fast skim",)]
    assert dialog.closed.calls == [()]


def test_enter_with_a_name_that_is_taken_keeps_the_popup_open(owner, shown):
    dialog, submitted = make_profile_name(owner, existing=["Fast skim"])
    shown(dialog)
    dialog.name_entry.insert(0, "Fast skim")
    press(dialog, "Return")
    assert submitted.calls == []
    assert is_open(dialog)
    assert dialog.error_label.cget("text")
    dialog.destroy()


def test_esc_cancels_a_profile_name(owner, shown):
    dialog, submitted = make_profile_name(owner)
    shown(dialog)
    dialog.name_entry.insert(0, "Fast skim")
    press(dialog, "Escape")
    assert submitted.calls == []
    assert not is_open(dialog)
    assert dialog.closed.calls == [()]


# ---- the helper itself ----

def test_a_key_left_out_is_not_bound(root):
    from gui.components.dialog_keys import bind_dialog_keys

    frame = tkinter.Frame(root)
    try:
        bind_dialog_keys(frame, on_escape=lambda: None)
        assert frame.bind("<Escape>")
        assert not frame.bind("<Return>")
        assert not frame.bind("<KP_Enter>")
    finally:
        frame.destroy()
