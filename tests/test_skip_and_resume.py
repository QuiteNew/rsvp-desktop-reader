"""Skipping and resuming in a real app, with real clicks: the footer's skip
buttons, the skip settings in the Settings window, rewinding a few words when
reading resumes, and the footer's chunk size buttons.

The footer has the << and >> buttons either side of the speed slider. They skip
by the skip amount from Settings, in the main window or, when the transcript has
been detached, in the detached window. With "Pause playback when skipping" on,
a skip leaves the reading paused on the word it lands on.

The skip amount slider and the pause-on-skip switch in Settings take effect the
moment they are changed, without Apply. Closing Settings (Close or Esc) keeps
them, because they were already applied. "Reset to Original Defaults" puts both
back straight away too.

Timers run at different speeds on different machines, so no test says where a
running reading has got to. They pause first and then look, or they use a speed
slow enough (60 words a minute) that nothing moves while they look.
"""
import pytest

from core.settings_store import CHUNK_SIZE_RANGE, SettingsStore
from tk_helpers import click_button, settle

WORD_LIST = [f"w{number}" for number in range(200)]
WORDS = " ".join(WORD_LIST)
PAUSED = "▶"
RUNNING = "⏸"


# ---- helpers ----

def _open_book(app, wpm=60, chunk=None):
    """A transcript with text, paused on its first word, open in the main window.
    chunk is (enabled, size) for the transcript's chunking."""
    transcript = app.store.add_transcript("Book", app.store.current_space, wpm=wpm)
    app.store.set_transcript_text(transcript.id, WORDS)
    app.store.set_transcript_paused(transcript.id, True)
    if chunk is not None:
        app.store.set_transcript_chunking(transcript.id, *chunk)
    app._refresh_transcript_list()
    settle(app, 200)
    app._handle_open_transcript(transcript)
    settle(app, 300)
    # Tk prints an error raised inside a click handler and carries on, so
    # without this a handler that fell over would not fail a test.
    app.callback_errors = []
    app.report_callback_exception = lambda *details: app.callback_errors.append(details)
    return transcript


@pytest.fixture
def book(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _open_book(app)
        yield app, transcript
        assert app.callback_errors == []


def _reader(app):
    return app.canvas.reader_display


def _index(app):
    return _reader(app).session.index


def _shown(reader):
    return "".join(label.cget("text") for label in (reader.before_label, reader.focus_label, reader.after_label))


def _pause_label(app):
    return app.canvas.toolbar.pause_button.cget("text")


def _skip_forward(app):
    click_button(app.footer.skip_forward_button)
    settle(app, 60)


def _skip_back(app):
    click_button(app.footer.skip_back_button)
    settle(app, 60)


def _pause_button(app):
    click_button(app.canvas.toolbar.pause_button)
    settle(app, 60)


def _open_settings(app):
    app._open_settings_window()
    settle(app, 300)
    window = app._settings_window
    window.tabview.set("Defaults")
    settle(window, 100)
    return window


def _slide_skip_amount_to(window, count):
    """Click the skip amount slider where count is, the way a person clicks
    along a slider. It runs from 1 to 50 in steps of 1."""
    slider = window.skip_word_count_slider
    low, high = 1, 50
    x = round((count - low) / (high - low) * slider._canvas.winfo_width())
    slider._canvas.event_generate("<Button-1>", x=x, y=5)
    settle(window, 60)


def _click_switch(switch):
    switch._canvas.event_generate("<Button-1>", x=5, y=5)
    settle(switch, 60)


def _button(window, text, tab=None):
    """The one button with this text, looking only in one tab when tab is given
    (every tab has its own "Reset to Original Defaults")."""
    import customtkinter as ctk

    from tk_helpers import all_widgets

    where = window.tabview.tab(tab) if tab else window
    (button,) = [w for w in all_widgets(where) if isinstance(w, ctk.CTkButton) and w.cget("text") == text]
    return button


def _set_resume_rewind_in_settings(app, on, words):
    """Turn rewind-on-resume on or off and set how far, in the real Settings
    window, then Apply."""
    window = _open_settings(app)
    switch = window.resume_rewind_switch
    if bool(switch.get()) != on:
        _click_switch(switch)
    entry = window.resume_rewind_words_entry
    entry.delete(0, "end")
    entry.insert(0, str(words))
    click_button(window.apply_button)
    settle(app, 200)
    assert not window.winfo_exists(), "Apply closes Settings"


def _detach(app):
    click_button(app.canvas.toolbar.detach_button)
    settle(app, 700)
    window = app.canvas._detached_window
    assert window is not None
    return window


# ---- the footer's skip buttons ----

def test_the_footer_skip_buttons_move_by_the_skip_amount_and_save_the_place(book):
    app, transcript = book
    assert app.settings_store.skip_word_count == 10

    _skip_forward(app)
    assert _index(app) == 10
    assert _shown(_reader(app)) == WORD_LIST[10]
    assert transcript.position == 10

    _skip_forward(app)
    _skip_back(app)
    assert _index(app) == 10
    assert transcript.position == 10

    _skip_back(app)
    _skip_back(app)
    assert _index(app) == 0, "a skip back stops at the first word"
    assert transcript.position == 0


@pytest.mark.parametrize("pause_on_skip", [False, True])
def test_a_skip_while_reading_keeps_reading_unless_pause_on_skip_is_on(tmp_path, open_real_app, pause_on_skip):
    with open_real_app(tmp_path) as app:
        app.settings_store.set_skip_behavior(10, pause_on_skip)
        app.canvas.set_pause_on_skip(pause_on_skip)
        transcript = _open_book(app, wpm=300)
        _pause_button(app)
        assert transcript.is_paused is False

        _skip_forward(app)

        assert transcript.is_paused is pause_on_skip
        assert _pause_label(app) == (PAUSED if pause_on_skip else RUNNING)
        landed = _index(app)
        assert landed >= 10
        settle(app, 800)
        if pause_on_skip:
            assert _index(app) == landed, "paused on the word it landed on"
            assert _shown(_reader(app)) == WORD_LIST[landed]
        else:
            assert _index(app) > landed, "the reading went on"
        assert app.callback_errors == []


@pytest.mark.parametrize("pause_on_skip", [False, True])
def test_a_skip_while_paused_stays_paused_either_way(tmp_path, open_real_app, pause_on_skip):
    with open_real_app(tmp_path) as app:
        app.settings_store.set_skip_behavior(10, pause_on_skip)
        app.canvas.set_pause_on_skip(pause_on_skip)
        transcript = _open_book(app, wpm=300)

        _skip_forward(app)
        settle(app, 500)

        assert transcript.is_paused is True
        assert _pause_label(app) == PAUSED
        assert _index(app) == 10
        assert app.callback_errors == []


def test_a_skip_that_pauses_stops_counting_reading_time(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        app.settings_store.set_skip_behavior(10, True)
        app.canvas.set_pause_on_skip(True)
        _open_book(app, wpm=300)
        _pause_button(app)
        reader = _reader(app)
        assert reader._active_span_start is not None, "reading time is being counted"

        _skip_forward(app)

        assert reader._active_span_start is None, "the skip paused, so the count stopped"
        counted = reader._session_active_seconds
        settle(app, 400)
        assert reader._session_active_seconds == counted


def test_the_footer_skip_buttons_move_the_detached_window_when_it_has_the_transcript(book):
    app, transcript = book
    window = _detach(app)
    assert _reader(app).session is None, "the main window's reader is stopped"

    _skip_forward(app)
    assert window.reader_display.session.index == 10
    assert transcript.position == 10
    _skip_back(app)
    assert window.reader_display.session.index == 0


def test_the_footer_skip_buttons_do_nothing_with_no_transcript_open(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        settle(app, 200)
        errors = []
        app.report_callback_exception = lambda *details: errors.append(details)
        for button in (app.footer.skip_back_button, app.footer.skip_forward_button):
            assert button.cget("state") == "disabled"
            click_button(button)
            settle(app, 60)
        assert _reader(app).session is None
        assert errors == []


# ---- the skip settings, applied as they change ----

def test_the_skip_amount_slider_applies_as_it_moves(book):
    app, transcript = book
    window = _open_settings(app)

    _slide_skip_amount_to(window, 7)

    assert window.skip_word_count_label.cget("text") == "7 words"
    assert app.settings_store.skip_word_count == 7
    click_button(_button(window, "Close"))
    settle(app, 200)
    assert not window.winfo_exists()

    _skip_forward(app)
    assert _index(app) == 7, "Close keeps it, it was applied already"


def test_the_skip_amount_slider_reaches_a_detached_window_that_is_open(book):
    app, transcript = book
    detached = _detach(app)
    window = _open_settings(app)

    _slide_skip_amount_to(window, 4)
    click_button(_button(window, "Close"))
    settle(app, 200)

    click_button(detached.toolbar.skip_forward_button)
    settle(app, 60)
    assert detached.reader_display.session.index == 4


def test_the_skip_amount_from_the_slider_is_on_disk_while_the_app_is_still_open(book):
    """So it isn't lost if the app is closed by force. A drag sends many moves,
    so they are written at most once a second, but the first is written at once."""
    app, transcript = book
    window = _open_settings(app)

    _slide_skip_amount_to(window, 23)

    assert SettingsStore().skip_word_count == 23


def test_the_skip_amount_from_the_slider_is_saved_by_the_time_the_app_closes(tmp_path, open_real_app):
    """The second move comes too soon after the first to be written straight
    away. Closing the app writes it."""
    with open_real_app(tmp_path) as app:
        _open_book(app)
        window = _open_settings(app)
        _slide_skip_amount_to(window, 23)
        _slide_skip_amount_to(window, 31)
        click_button(_button(window, "Close"))
        settle(app, 200)

        app._handle_close()

        assert SettingsStore().skip_word_count == 31


def test_the_pause_on_skip_switch_applies_and_is_saved_at_once(book):
    app, transcript = book
    window = _open_settings(app)
    assert not window.pause_on_skip_switch.get()

    _click_switch(window.pause_on_skip_switch)
    assert app.settings_store.pause_on_skip is True
    assert SettingsStore().pause_on_skip is True, "on disk without waiting"
    _click_switch(window.pause_on_skip_switch)
    assert SettingsStore().pause_on_skip is False, "a quick second change is saved too"
    _click_switch(window.pause_on_skip_switch)
    assert SettingsStore().pause_on_skip is True

    window.focus_force()
    settle(window, 100)
    (window.focus_get() or window).event_generate("<Escape>")
    settle(app, 200)
    assert not window.winfo_exists(), "Esc closes Settings"

    _pause_button(app)
    assert transcript.is_paused is False
    _skip_forward(app)
    assert transcript.is_paused is True, "Esc keeps it, it was applied already"

    window = _open_settings(app)
    assert window.pause_on_skip_switch.get(), "Settings shows it on next time"
    _click_switch(window.pause_on_skip_switch)
    assert SettingsStore().pause_on_skip is False


def test_reset_to_original_defaults_puts_the_skip_settings_back_at_once(book):
    app, transcript = book
    app.settings_store.set_skip_behavior(7, True)
    app.canvas.set_skip_word_count(7)
    app.canvas.set_pause_on_skip(True)
    window = _open_settings(app)
    assert window.skip_word_count_label.cget("text") == "7 words"
    assert window.pause_on_skip_switch.get()

    click_button(_button(window, "Reset to Original Defaults", tab="Defaults"))
    settle(window, 100)

    assert window.skip_word_count_slider.get() == 10
    assert window.skip_word_count_label.cget("text") == "10 words"
    assert not window.pause_on_skip_switch.get()
    assert (app.settings_store.skip_word_count, app.settings_store.pause_on_skip) == (10, False)
    click_button(_button(window, "Close"))
    settle(app, 200)

    _pause_button(app)
    _skip_forward(app)
    assert transcript.is_paused is False, "pause on skip is off again"
    _pause_button(app)
    assert transcript.is_paused is True
    assert _index(app) >= 10


# ---- rewinding a few words when reading resumes ----

def _paused_at(app, index, reader=None):
    """One skip forward, still paused, to land on index. reader is the one
    showing the transcript, the main window's unless it says otherwise."""
    app.settings_store.set_skip_behavior(index, False)
    app.canvas.set_skip_word_count(index)
    _skip_forward(app)
    assert (reader or _reader(app)).session.index == index


def test_resuming_steps_back_by_the_rewind_amount(book):
    app, transcript = book
    _set_resume_rewind_in_settings(app, on=True, words=3)
    _paused_at(app, 20)

    _pause_button(app)

    assert transcript.is_paused is False
    assert _index(app) == 17
    assert _shown(_reader(app)) == WORD_LIST[17]
    assert transcript.position == 17, "the place it went back to is saved"
    _pause_button(app)
    assert _index(app) in (17, 18)


def test_pausing_does_not_rewind_only_resuming_does(book):
    app, transcript = book
    _set_resume_rewind_in_settings(app, on=True, words=3)
    _paused_at(app, 20)
    _pause_button(app)
    assert _index(app) == 17

    _pause_button(app)

    assert transcript.is_paused is True
    assert _index(app) in (17, 18)


def test_resuming_near_the_start_goes_back_no_further_than_the_first_word(book):
    app, transcript = book
    _set_resume_rewind_in_settings(app, on=True, words=5)
    _paused_at(app, 2)

    _pause_button(app)

    assert _index(app) == 0
    assert _shown(_reader(app)) == WORD_LIST[0]
    assert transcript.position == 0


def test_with_rewind_off_resuming_carries_on_from_the_same_word(book):
    app, transcript = book
    _set_resume_rewind_in_settings(app, on=False, words=3)
    _paused_at(app, 20)

    _pause_button(app)

    assert transcript.is_paused is False
    assert _index(app) == 20
    assert _shown(_reader(app)) == WORD_LIST[20]


def test_the_rewind_applies_in_the_detached_window_too(book):
    app, transcript = book
    window = _detach(app)
    _set_resume_rewind_in_settings(app, on=True, words=4)
    _paused_at(app, 30, window.reader_display)

    click_button(window.toolbar.pause_button)
    settle(app, 60)

    assert window.reader_display.session.index == 26
    assert _shown(window.reader_display) == WORD_LIST[26]
    assert transcript.position == 26


# ---- the footer's chunk size buttons ----

def _record_chunking_saves(app, monkeypatch):
    saved = []
    original = app.store.set_transcript_chunking

    def recording(*args, **kwargs):
        saved.append(args[1:])
        return original(*args, **kwargs)

    monkeypatch.setattr(app.store, "set_transcript_chunking", recording)
    return saved


def test_the_chunk_size_minus_button_steps_down_and_stops_at_the_smallest(tmp_path, open_real_app, monkeypatch):
    low, high = CHUNK_SIZE_RANGE
    with open_real_app(tmp_path) as app:
        transcript = _open_book(app, chunk=(True, low + 2))
        saved = _record_chunking_saves(app, monkeypatch)
        _pause_button(app)
        _pause_button(app)

        for size in (low + 1, low):
            click_button(app.footer.chunk_decrease_button)
            settle(app, 60)
            assert app.footer.chunk_size_label.cget("text") == str(size)
            assert transcript.chunk_size == size
            assert _reader(app).session.chunk_size == size, "the reader groups by the new size"
        assert saved == [(True, low + 1), (True, low)]

        click_button(app.footer.chunk_decrease_button)
        settle(app, 60)

        assert app.footer.chunk_size_label.cget("text") == str(low)
        assert transcript.chunk_size == low
        assert saved == [(True, low + 1), (True, low)], "a press at the end changes and saves nothing"
        assert app.callback_errors == []


def test_the_chunk_size_plus_button_stops_at_the_largest(tmp_path, open_real_app, monkeypatch):
    low, high = CHUNK_SIZE_RANGE
    with open_real_app(tmp_path) as app:
        transcript = _open_book(app, chunk=(True, high - 1))
        saved = _record_chunking_saves(app, monkeypatch)

        click_button(app.footer.chunk_increase_button)
        settle(app, 60)
        click_button(app.footer.chunk_increase_button)
        settle(app, 60)

        assert app.footer.chunk_size_label.cget("text") == str(high)
        assert transcript.chunk_size == high
        assert saved == [(True, high)]


def test_the_chunk_size_buttons_change_the_size_while_chunking_is_off(tmp_path, open_real_app):
    low, high = CHUNK_SIZE_RANGE
    with open_real_app(tmp_path) as app:
        transcript = _open_book(app, chunk=(False, high))

        click_button(app.footer.chunk_decrease_button)
        settle(app, 60)

        assert transcript.chunk_size == high - 1
        assert transcript.chunking_enabled is False, "the size is kept for later"
        assert _reader(app).session.chunking_enabled is False

        _click_switch(app.footer.chunk_switch)

        assert (transcript.chunking_enabled, transcript.chunk_size) == (True, high - 1)
        assert _reader(app).session.chunk_size == high - 1, "turned on with the size chosen while it was off"
        assert app.callback_errors == []
