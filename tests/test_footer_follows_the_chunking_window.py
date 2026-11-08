"""The footer's chunking controls show what the Configure chunking window has
just applied to the open transcript.

The footer has its own Group switch and a size with - and + buttons. The
chunking window (Settings, Configure chunking) can change the same two things
for the open transcript. When it did, the reader and the saved transcript
changed but the footer kept showing what was there before. The next press of
the footer's - or + then sent that old on/off along with the new size, so a
person who had just turned grouping on in the window found it turned off again.

Everything here goes through the real windows: Settings is opened, Configure
chunking is clicked, the window's controls are clicked and Apply is pressed.
Both windows are closed before the footer is used, the way a person would.
"""
import customtkinter as ctk
import pytest

from core.settings_store import CHUNK_SIZE_RANGE
from gui.components.chunking_settings_window import TARGET_CURRENT, TARGET_DEFAULTS, ChunkingSettingsWindow
from tk_helpers import all_widgets, click_button, settle

WORDS = " ".join(f"w{number}" for number in range(120))


@pytest.fixture
def open_book(tmp_path, open_real_app):
    """Hands back a function that opens a paused transcript with the given
    chunking in the main window."""
    with open_real_app(tmp_path) as app:
        app.callback_errors = []
        app.report_callback_exception = lambda *details: app.callback_errors.append(details)

        def open_book(enabled, size):
            transcript = app.store.add_transcript("Book", app.store.current_space, wpm=60)
            app.store.set_transcript_text(transcript.id, WORDS)
            app.store.set_transcript_paused(transcript.id, True)
            app.store.set_transcript_chunking(transcript.id, enabled, size)
            app._refresh_transcript_list()
            settle(app, 200)
            app._handle_open_transcript(transcript)
            settle(app, 300)
            return app, transcript

        yield open_book
        assert app.callback_errors == []


def _button(window, text):
    (button,) = [w for w in all_widgets(window) if isinstance(w, ctk.CTkButton) and w.cget("text") == text]
    return button


def _apply_in_the_chunking_window(app, target, enabled, size):
    """Open Settings, click Configure chunking, set the window up and click
    Apply. Then close the chunking window and Settings with their Close
    buttons."""
    app._open_settings_window()
    settle(app, 300)
    settings = app._settings_window
    settings.tabview.set("Defaults")
    settle(settings, 100)
    click_button(_button(settings, "Configure chunking…"))
    settle(app, 300)
    (window,) = [w for w in settings.winfo_children() if isinstance(w, ChunkingSettingsWindow)]

    click_button(window.target_selector._buttons_dict[target])
    settle(window, 60)
    if bool(window.group_switch.get()) != enabled:
        window.group_switch._canvas.event_generate("<Button-1>", x=5, y=5)
    low, high = CHUNK_SIZE_RANGE
    slider = window.size_slider
    width = slider._canvas.winfo_width()
    slider._canvas.event_generate("<Button-1>", x=min(width - 1, round((size - low) / (high - low) * width)), y=5)
    settle(window, 60)
    assert window.size_label.cget("text") == f"{size} words"
    click_button(_button(window, "Apply"))
    settle(app, 100)

    click_button(_button(window, "Close"))
    settle(app, 200)
    click_button(_button(settings, "Close"))
    settle(app, 200)
    assert not settings.winfo_exists()


def _footer(app):
    return bool(app.footer.chunk_switch.get()), int(app.footer.chunk_size_label.cget("text"))


def _press(button):
    click_button(button)
    settle(button, 60)


def test_turning_grouping_on_in_the_window_shows_in_the_footer(open_book):
    app, transcript = open_book(False, 2)

    _apply_in_the_chunking_window(app, TARGET_CURRENT, True, 4)

    assert (transcript.chunking_enabled, transcript.chunk_size) == (True, 4)
    assert _footer(app) == (True, 4)


def test_the_footers_plus_afterwards_keeps_grouping_on(open_book):
    app, transcript = open_book(False, 2)
    _apply_in_the_chunking_window(app, TARGET_CURRENT, True, 4)

    _press(app.footer.chunk_increase_button)

    assert (transcript.chunking_enabled, transcript.chunk_size) == (True, 5)
    assert _footer(app) == (True, 5)
    session = app.canvas.reader_display.session
    assert (session.chunking_enabled, session.chunk_size) == (True, 5), "the reader groups by 5"


def test_turning_grouping_off_in_the_window_shows_in_the_footer(open_book):
    app, transcript = open_book(True, 3)

    _apply_in_the_chunking_window(app, TARGET_CURRENT, False, 3)

    assert _footer(app) == (False, 3)
    _press(app.footer.chunk_decrease_button)
    assert (transcript.chunking_enabled, transcript.chunk_size) == (False, 2), "it stays off"
    assert app.canvas.reader_display.session.chunking_enabled is False


def test_the_footers_switch_afterwards_starts_from_what_the_window_applied(open_book):
    app, transcript = open_book(False, 2)
    _apply_in_the_chunking_window(app, TARGET_CURRENT, True, 5)

    app.footer.chunk_switch._canvas.event_generate("<Button-1>", x=5, y=5)
    settle(app, 60)

    assert (transcript.chunking_enabled, transcript.chunk_size) == (False, 5)
    assert _footer(app) == (False, 5)


def test_applying_to_new_transcripts_leaves_the_footer_alone(open_book):
    app, transcript = open_book(False, 2)

    _apply_in_the_chunking_window(app, TARGET_DEFAULTS, True, 5)

    assert (app.settings_store.default_chunking_enabled, app.settings_store.default_chunk_size) == (True, 5)
    assert (transcript.chunking_enabled, transcript.chunk_size) == (False, 2)
    assert _footer(app) == (False, 2)
