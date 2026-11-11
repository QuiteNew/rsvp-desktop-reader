"""Tests for the Configure speaker cues window (gui/components/speaker_cues_window.py).

The window is built on its own here, with stand-ins for what the app hands it:
a transcript (just the parts the window reads), two Calls for the Apply
callbacks, and a FakePlayer that remembers what it was asked to play. Opening
it from Settings, and what the app does with Apply, are tested with the app.

They run against a real Tk with one hidden root for the whole module, and each
window is opened from a shown window, because Tk keeps a window hidden while its
owner is hidden (the same set-up as test_window_esc.py).

TEXT: Ann and Bob start two lines each, so Auto ticks them. Cat starts only one,
so she gets an unticked row."""

from types import SimpleNamespace

import customtkinter as ctk
import pytest

from core.chime import CHANGE_PATTERN, CHIME_STYLES, SPEAKER_PATTERNS
from core.settings_store import SPEAKER_CUE_SOUNDS
from gui.components.speaker_cues_window import (
    LIST_AUTOMATIC, LIST_CUSTOM, PREVIEW_PAUSE_MS, PREVIEW_SPEAKERS, SOUND_LABELS,
    SPEAKER_LIST_MAX_PX, SPEAKER_ROW_PX, STYLE_LABELS, SpeakerCuesWindow,
    appearances_text, preview_plan,
)

from tk_helpers import click_button, settle

TEXT = "Ann: hi\nBob: yo\nCat: once\nAnn: and\nBob: so"


class Calls:
    """Remembers every call made to it, with its arguments."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)


class FakePlayer:
    def __init__(self, available=True):
        self.available = available
        self.played = []

    def play(self, notes, style, wait=False):
        self.played.append((tuple(notes), style, wait))
        return True


def _transcript(text=TEXT, custom=None):
    return SimpleNamespace(id="t-1", title="Talk", raw_text=text, speaker_custom=custom)


@pytest.fixture
def owner(root, wait_until_shown):
    window = ctk.CTkToplevel(root)
    window.geometry("700x700+0+0")
    wait_until_shown(window)
    yield window
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()


@pytest.fixture
def make(owner, wait_until_shown):
    """Open the window with the saved values given (the defaults otherwise),
    shown and ready. Hands back the window, the two Apply callbacks' Calls and
    the player."""
    opened = []

    def build(enabled=False, name_tag=True, flash=True, sound="off", style="bell",
              transcript="default", player="default"):
        transcript = _transcript() if transcript == "default" else transcript
        player = FakePlayer() if player == "default" else player
        applied, applied_speakers = Calls(), Calls()
        window = SpeakerCuesWindow(
            owner, enabled, name_tag, flash, sound, style, transcript,
            on_apply=applied, on_apply_speakers=applied_speakers, chime_player=player,
        )
        opened.append(window)
        wait_until_shown(window)
        settle(window, 150)
        return window, applied, applied_speakers, player

    yield build
    for window in opened:
        if window.winfo_exists():
            window.destroy()


def _row(window, key):
    """A speaker row's (row as loaded, tick box, name variable)."""
    return next(entry for entry in window._row_widgets if entry[0].key == key)


def _mode(window):
    return window.list_mode_label.cget("text")


# --- The pieces with no window ------------------------------------------------

def test_the_choices_on_screen_cover_every_saved_value():
    assert list(SOUND_LABELS) == list(SPEAKER_CUE_SOUNDS)
    assert list(SOUND_LABELS.values()) == ["Off", "One chime", "Per speaker"]
    assert list(STYLE_LABELS) == list(CHIME_STYLES)
    assert list(STYLE_LABELS.values()) == ["Bell", "Soft", "Glass", "Wood"]


def test_appearances_are_counted_in_words():
    assert appearances_text(1) == "seen 1 time"
    assert appearances_text(2) == "seen 2 times"
    assert appearances_text(14) == "seen 14 times"


def test_per_speaker_plays_three_speakers_one_after_another():
    assert (PREVIEW_SPEAKERS, PREVIEW_PAUSE_MS) == (3, 250)
    # Bell chimes are 450, 570 and 570 ms long, so each one starts once the
    # one before is over, plus the pause.
    assert preview_plan("per_speaker", "bell") == [
        (0, SPEAKER_PATTERNS[0]),
        (450 + 250, SPEAKER_PATTERNS[1]),
        (450 + 250 + 570 + 250, SPEAKER_PATTERNS[2]),
    ]


def test_a_chime_shorter_than_the_readers_gap_still_waits_for_the_gap():
    # Wood's first chime is 300 ms, under the reader's 400 ms gap.
    assert preview_plan("per_speaker", "wood") == [
        (0, SPEAKER_PATTERNS[0]),
        (400 + 250, SPEAKER_PATTERNS[1]),
        (400 + 250 + 420 + 250, SPEAKER_PATTERNS[2]),
    ]


def test_one_chime_and_off_play_the_change_chime_once():
    assert preview_plan("change", "glass") == [(0, CHANGE_PATTERN)]
    assert preview_plan("off", "glass") == [(0, CHANGE_PATTERN)]


# --- What it shows ------------------------------------------------------------

def test_it_shows_the_saved_values(make):
    window, *_ = make(enabled=True, name_tag=False, flash=True, sound="per_speaker", style="glass")
    assert window.enabled_switch.get() == 1
    assert window.name_tag_check.get() == 0
    assert window.flash_check.get() == 1
    assert window.sound_selector.get() == "Per speaker"
    assert window.style_selector.get() == "Glass"


def test_it_shows_the_other_saved_values_too(make):
    window, *_ = make(enabled=False, name_tag=True, flash=False, sound="change", style="wood")
    assert window.enabled_switch.get() == 0
    assert window.name_tag_check.get() == 1
    assert window.flash_check.get() == 0
    assert window.sound_selector.get() == "One chime"
    assert window.style_selector.get() == "Wood"


def test_every_label_gets_a_row_as_auto_has_it(make):
    window, *_ = make()
    rows = [(row.key, check.get(), name.get()) for row, check, name in window._row_widgets]
    assert rows == [("ann", 1, "Ann"), ("bob", 1, "Bob"), ("cat", 0, "Cat")]
    assert _mode(window) == LIST_AUTOMATIC


def test_rows_follow_the_transcripts_own_list(make):
    window, *_ = make(transcript=_transcript(custom={"cat": "Kat"}))
    rows = [(row.key, check.get(), name.get()) for row, check, name in window._row_widgets]
    assert rows == [("ann", 0, "Ann"), ("bob", 0, "Bob"), ("cat", 1, "Kat")]
    assert _mode(window) == LIST_CUSTOM


def test_each_row_says_how_often_the_name_starts_a_line(make):
    window, *_ = make()
    texts = [
        child.cget("text")
        for line in window.speaker_list.winfo_children()
        for child in line.winfo_children()
        if isinstance(child, ctk.CTkLabel)
    ]
    assert texts == ["seen 2 times", "seen 2 times", "seen 1 time"]


def test_the_list_is_as_tall_as_its_rows_up_to_four(make):
    assert (SPEAKER_ROW_PX, SPEAKER_LIST_MAX_PX) == (34, 136)
    window, *_ = make()
    assert window.speaker_list.cget("height") == 3 * 34
    many = "\n".join(f"P{i}: a\nP{i}: b" for i in range(9))
    window, *_ = make(transcript=_transcript(text=many))
    assert window.speaker_list.cget("height") == 136


def test_the_scrollbar_does_not_make_the_list_taller(make):
    window, *_ = make()
    assert window.speaker_list._scrollbar.cget("height") == 3 * 34


def test_the_window_is_shorter_with_no_list_to_show(make):
    with_list, *_ = make()
    without_transcript, *_ = make(transcript=None)
    without_names, *_ = make(transcript=_transcript(text="just some words"))
    # In screen pixels, so scaled the way CustomTkinter scales the size given
    # to geometry() on a high-DPI display.
    def on_screen(window, height):
        return round(height * window._get_window_scaling())

    assert with_list.winfo_height() == on_screen(with_list, 700)
    assert without_transcript.winfo_height() == on_screen(without_transcript, 540)
    assert without_names.winfo_height() == on_screen(without_names, 540)


def test_with_no_transcript_open_there_is_no_list(make):
    window, applied, applied_speakers, _ = make(transcript=None)
    assert window.list_mode_label is None
    assert window._row_widgets == []
    click_button(window.apply_button)
    assert len(applied.calls) == 1
    assert applied_speakers.calls == []


def test_a_transcript_with_no_names_has_no_rows_and_saves_no_list(make):
    window, applied, applied_speakers, _ = make(transcript=_transcript(text="just some words"))
    assert window._row_widgets == []
    assert _mode(window) == LIST_AUTOMATIC
    click_button(window.apply_button)
    assert len(applied.calls) == 1
    assert applied_speakers.calls == []


# --- Changing the speaker list ------------------------------------------------

def test_ticking_a_row_makes_the_list_custom_and_unticking_makes_it_automatic(make):
    window, *_ = make()
    _, cat, _ = _row(window, "cat")
    cat.toggle()
    assert _mode(window) == LIST_CUSTOM
    cat.toggle()
    assert _mode(window) == LIST_AUTOMATIC


def test_typing_a_name_makes_the_list_custom(make):
    window, *_ = make()
    _, _, ann = _row(window, "ann")
    ann.set("Annie")
    assert _mode(window) == LIST_CUSTOM


def test_back_to_automatic_puts_every_row_back(make):
    window, *_ = make(transcript=_transcript(custom={"cat": "Kat"}))
    click_button(window.back_to_automatic_button)
    rows = [(row.key, check.get(), name.get()) for row, check, name in window._row_widgets]
    assert rows == [("ann", 1, "Ann"), ("bob", 1, "Bob"), ("cat", 0, "Cat")]
    assert _mode(window) == LIST_AUTOMATIC


# --- Apply ---------------------------------------------------------------------

def test_apply_hands_back_what_is_on_screen(make):
    window, applied, applied_speakers, _ = make()
    window.enabled_switch.select()
    window.name_tag_check.deselect()
    window.sound_selector.set("Per speaker")
    window.style_selector.set("Wood")

    click_button(window.apply_button)

    assert applied.calls == [(True, False, True, "per_speaker", "wood")]
    assert applied_speakers.calls == [("t-1", None)]
    assert window.status_label.cget("text") == "Applied."
    assert window.winfo_exists(), "the window stays open after Apply"


def test_apply_saves_a_changed_list(make):
    window, _, applied_speakers, _ = make()
    _row(window, "cat")[1].toggle()
    _row(window, "bob")[2].set("Ann")

    click_button(window.apply_button)

    assert applied_speakers.calls == [("t-1", {"ann": "Ann", "bob": "Ann", "cat": "Cat"})]


def test_apply_after_back_to_automatic_saves_automatic(make):
    window, _, applied_speakers, _ = make(transcript=_transcript(custom={"cat": "Kat"}))
    click_button(window.back_to_automatic_button)
    click_button(window.apply_button)
    assert applied_speakers.calls == [("t-1", None)]


def test_close_and_esc_leave_without_applying(make):
    window, applied, applied_speakers, _ = make()
    window.enabled_switch.select()
    window.event_generate("<Return>")
    window.update()
    assert applied.calls == [] and window.winfo_exists(), "Enter applies nothing"

    window.event_generate("<Escape>")
    settle(window.master, 50)
    assert not window.winfo_exists()
    assert (applied.calls, applied_speakers.calls) == ([], [])

    window, applied, _, _ = make()
    click_button(window.close_button)
    settle(window.master, 50)
    assert not window.winfo_exists()
    assert applied.calls == []


# --- Sound and Listen ---------------------------------------------------------

def test_listen_plays_the_choice_on_screen_without_applying_it(make):
    window, applied, _, player = make(sound="off", style="bell")
    window.sound_selector.set("One chime")
    window.style_selector.set("Glass")

    click_button(window.listen_button)

    assert player.played == [(CHANGE_PATTERN, "glass", True)]
    assert applied.calls == []


def test_listen_plays_three_speakers_in_turn(make):
    window, _, _, player = make(sound="per_speaker", style="wood")
    click_button(window.listen_button)
    assert player.played == [(SPEAKER_PATTERNS[0], "wood", True)], "the first one at once"

    settle(window, 1500)

    assert player.played == [(notes, "wood", True) for notes in SPEAKER_PATTERNS[:3]]


def test_a_second_click_starts_again_from_the_beginning(make):
    window, _, _, player = make(sound="per_speaker", style="wood")
    click_button(window.listen_button)
    click_button(window.listen_button)
    assert len(window._preview_after_ids) == 2, "only the second click's timers are kept"
    settle(window, 1500)
    assert player.played == [(notes, "wood", True) for notes in (
        SPEAKER_PATTERNS[0], SPEAKER_PATTERNS[0], SPEAKER_PATTERNS[1], SPEAKER_PATTERNS[2],
    )]


def test_closing_stops_what_listen_still_had_to_play(make):
    # Tk would otherwise still run the two timers after the window has gone,
    # and report an "invalid command name" error for each.
    window, _, _, player = make(sound="per_speaker", style="wood")
    owner = window.master
    click_button(window.listen_button)
    waiting = list(window._preview_after_ids)
    assert len(waiting) == 2

    window.destroy()

    still_waiting = owner.tk.splitlist(owner.tk.call("after", "info"))
    assert not set(waiting) & set(still_waiting)
    settle(owner, 1500)
    assert player.played == [(SPEAKER_PATTERNS[0], "wood", True)]


@pytest.mark.parametrize("player", [None, FakePlayer(available=False)], ids=["no player", "no sound here"])
def test_without_sound_the_sound_part_is_greyed_and_kept_as_saved(make, player):
    window, applied, _, _ = make(sound="per_speaker", style="glass", player=player)

    for widget in (window.sound_selector, window.style_selector, window.listen_button):
        assert widget.cget("state") == "disabled"
    assert window.sound_note.cget("text") == "Sound is Windows only for now, so it can't be changed here."

    click_button(window.apply_button)
    assert applied.calls == [(False, True, True, "per_speaker", "glass")]


def test_with_sound_the_sound_part_can_be_used(make):
    window, *_ = make()
    for widget in (window.sound_selector, window.style_selector, window.listen_button):
        assert widget.cget("state") == "normal"
