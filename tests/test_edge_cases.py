"""The small corners the other test files don't reach: a reading that has run to
its end, a profile value of a kind nobody taught the profiles to check, the app
with no transcript open, the reading keys when no widget reports having the
keyboard, a transcript of a single word, the scrubber with no words at all, and
the sidebar's search box being typed, pasted and cut into for real.

Several of the app's "nothing is open" checks can't be reached by clicking,
because the footer's controls are all disabled while nothing is open. Those are
tested twice: once with real clicks, to show the controls really are disabled
and do nothing, and once by calling the handler directly, so the check itself
is pinned down in case a control is ever left enabled.
"""
import pytest

from core import profiles
from core.reader import ReaderSession
from core.timing import wpm_to_delay_ms
from gui.components.chunking_settings_window import TARGET_CURRENT, TARGET_DEFAULTS, ChunkingSettingsWindow
from tk_helpers import click_button, settle

PAUSED = "▶"
RUNNING = "⏸"


# ---- a reading that has run to its end ----

def _finished(**options):
    session = ReaderSession("one two three four five", wpm=300, **options)
    while not session.is_finished:
        session.advance()
    return session


@pytest.mark.parametrize("chunked", [False, True])
def test_a_finished_reading_has_no_chunk_on_screen(chunked):
    session = _finished(chunk_enabled=chunked, chunk_size=2)

    assert session.current_frame() is None
    assert session.current_chunk() is None
    assert session.current_chunk_bounds() is None


@pytest.mark.parametrize("chunked", [False, True])
def test_a_finished_reading_waits_one_plain_word_before_anything_else(chunked):
    """Nothing is on screen to time, so both delays fall back to one word at
    the reading speed, with no pauses for punctuation or warm-up added."""
    session = _finished(chunk_enabled=chunked, chunk_size=2, warm_up_enabled=True)

    assert session.current_delay_ms() == wpm_to_delay_ms(300)
    assert session.current_chunk_delay_ms() == wpm_to_delay_ms(300)


# ---- what a profile may hold ----

def test_every_profile_setting_is_of_a_kind_the_profiles_can_check():
    """value_is_valid knows three kinds. A setting added to a profile with any
    other kind would be refused whatever its value, so it must not happen."""
    assert set(profiles._KINDS.values()) <= {"bool", "int", "color"}


def test_a_value_of_a_kind_the_profiles_dont_know_is_refused(monkeypatch):
    monkeypatch.setitem(profiles._KINDS, "made_up_setting", "text")

    assert profiles.value_is_valid("made_up_setting", "anything") is False
    assert profiles.sanitize_values({"made_up_setting": "anything"}) == {}


# ---- the app with nothing open ----

@pytest.fixture
def app(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        settle(app, 200)
        app.callback_errors = []
        app.report_callback_exception = lambda *details: app.callback_errors.append(details)
        yield app
        assert app.callback_errors == []


def _footer_controls(footer):
    return {
        "speed slider": footer.wpm_slider,
        "font colour": footer.font_swatch,
        "background colour": footer.background_swatch,
        "highlight colour": footer.highlight_swatch,
        "skip back": footer.skip_back_button,
        "skip forward": footer.skip_forward_button,
        "smaller": footer.size_decrease_button,
        "bigger": footer.size_increase_button,
        "group switch": footer.chunk_switch,
        "group smaller": footer.chunk_decrease_button,
        "group bigger": footer.chunk_increase_button,
    }


def test_with_nothing_open_every_footer_control_is_disabled_and_does_nothing(app):
    settings_before = app.settings_store.export_settings()

    for name, control in _footer_controls(app.footer).items():
        assert control.cget("state") == "disabled", name
        control._canvas.event_generate("<Button-1>", x=5, y=5)
        control._canvas.event_generate("<ButtonRelease-1>", x=5, y=5)
        settle(app, 30)

    assert app.store.transcripts == []
    assert app.settings_store.export_settings() == settings_before
    assert app.canvas.reader_display.session is None


# Each of these is what a footer control calls. With nothing open each must
# do nothing, rather than fall over looking for the open transcript.
HANDLERS = {
    "speed": lambda app: app._handle_wpm_changed(500),
    "grouping": lambda app: app._handle_chunking_changed(True, 3),
    "font colour": lambda app: app._handle_font_color_changed("#123456"),
    "font size": lambda app: app._handle_font_size_changed(40),
    "highlight colour": lambda app: app._handle_highlight_color_changed("#123456"),
    "background colour": lambda app: app._handle_background_color_changed("#123456"),
    "chunking window, this transcript": lambda app: app._apply_chunking_settings("current", True, 3, "fixed", 30),
}


@pytest.mark.parametrize("which", HANDLERS)
def test_with_nothing_open_a_footer_change_does_nothing(app, which):
    settings_before = app.settings_store.export_settings()

    HANDLERS[which](app)
    settle(app, 60)

    assert app.store.transcripts == []
    assert app.settings_store.export_settings() == settings_before
    assert app.canvas.reader_display.session is None


def test_with_nothing_open_the_chunking_window_only_offers_new_transcripts(app):
    """Which is why its "This transcript" check in the app can't be reached
    from the window (it is called directly above)."""
    import customtkinter as ctk

    from tk_helpers import all_widgets

    app._open_settings_window()
    settle(app, 300)
    settings = app._settings_window
    settings.tabview.set("Defaults")
    settle(settings, 100)
    (button,) = [w for w in all_widgets(settings)
                 if isinstance(w, ctk.CTkButton) and w.cget("text") == "Configure chunking…"]
    click_button(button)
    settle(app, 300)

    (window,) = [w for w in settings.winfo_children() if isinstance(w, ChunkingSettingsWindow)]
    assert list(window.target_selector._buttons_dict) == [TARGET_DEFAULTS]
    assert TARGET_CURRENT not in window.target_selector._buttons_dict


# ---- the reading keys when no widget reports having the keyboard ----

def _open_book(app, text, wpm=60):
    transcript = app.store.add_transcript("Book", app.store.current_space, wpm=wpm)
    app.store.set_transcript_text(transcript.id, text)
    app.store.set_transcript_paused(transcript.id, True)
    app._refresh_transcript_list()
    settle(app, 200)
    app._handle_open_transcript(transcript)
    settle(app, 300)
    return transcript


def test_the_reading_keys_work_when_no_widget_reports_having_the_keyboard(app, monkeypatch):
    """focus_get() gives None when the keyboard is somewhere Tk can't name.
    With no text box holding the keyboard, nothing should hold a key back."""
    transcript = _open_book(app, " ".join(f"w{n}" for n in range(50)))
    monkeypatch.setattr(app, "focus_get", lambda: None)

    app.event_generate("<space>")
    settle(app, 60)

    assert app.canvas.toolbar.pause_button.cget("text") == RUNNING
    assert transcript.is_paused is False


# ---- a transcript of a single word ----

def test_a_single_word_has_nothing_to_scrub(app):
    transcript = _open_book(app, "hello")
    scrubber = app.canvas.scrub_bar

    assert scrubber.slider.cget("state") == "disabled"
    assert scrubber.readout.cget("text") == "word 1 of 1"
    scrubber.slider._canvas.event_generate("<Button-1>", x=60, y=5)
    scrubber.slider._canvas.event_generate("<ButtonRelease-1>", x=60, y=5)
    settle(app, 100)

    assert app.canvas.reader_display.session.index == 0
    assert transcript.is_paused is True
    assert app.canvas.toolbar.pause_button.cget("text") == PAUSED


def test_the_scrubber_with_no_words_shows_nothing_and_ignores_a_position(app):
    scrubber = app.canvas.scrub_bar
    scrubber.set_total(0)

    assert scrubber.slider.cget("state") == "disabled"
    assert scrubber.readout.cget("text") == ""
    scrubber.set_position(3)
    assert scrubber.readout.cget("text") == ""
    assert scrubber.slider.get() == 0


# ---- the sidebar's search box, typed into for real ----

def _rows(app):
    return [child for child in app.list_body.entries_frame.winfo_children()]


def _titles(app):
    shown = []
    for transcript in app.store.transcripts:
        if any(transcript.title in str(_texts(row)) for row in _rows(app)):
            shown.append(transcript.title)
    return shown


def _texts(widget):
    found = []
    try:
        found.append(widget.cget("text"))
    except Exception:
        pass
    for child in widget.winfo_children():
        found.extend(_texts(child))
    return found


def _type(entry, text):
    """Each letter as a real key going down and up, the way typing arrives."""
    for letter in text:
        entry.event_generate("<KeyPress>", keysym=letter)
        entry.event_generate("<KeyRelease>", keysym=letter)
    settle(entry, 100)


@pytest.fixture
def two_books(app):
    for title in ("Alpha notes", "Beta notes"):
        app.store.add_transcript(title, app.store.current_space)
    app._refresh_transcript_list()
    settle(app, 200)
    entry = app.list_body._search_box._entry._entry
    entry.focus_force()
    settle(app, 100)
    return app, entry


def test_typing_in_the_search_box_narrows_the_list_as_you_type(two_books):
    app, entry = two_books
    assert _titles(app) == ["Alpha notes", "Beta notes"]

    _type(entry, "alp")

    assert entry.get() == "alp"
    assert _titles(app) == ["Alpha notes"]
    assert app.list_body._search_box._clear_button.winfo_ismapped(), "the X shows"

    for _ in range(3):
        entry.event_generate("<KeyPress>", keysym="BackSpace")
        entry.event_generate("<KeyRelease>", keysym="BackSpace")
    settle(app, 100)

    assert entry.get() == ""
    assert _titles(app) == ["Alpha notes", "Beta notes"]
    assert not app.list_body._search_box._clear_button.winfo_ismapped(), "the X is gone"


def _shortcut(entry, key):
    """Ctrl plus a key, down and up, the way the keyboard sends it. Tk turns
    Ctrl+V and Ctrl+X into the entry's own paste and cut."""
    entry.event_generate(f"<Control-KeyPress-{key}>")
    entry.event_generate(f"<Control-KeyRelease-{key}>")
    settle(entry, 100)


def test_a_paste_or_cut_with_the_keyboard_narrows_the_list_too(two_books):
    """The box only listens for a key going up. By the time Ctrl+V or Ctrl+X
    comes up, the entry has already changed, so the list follows it."""
    app, entry = two_books
    app.clipboard_clear()
    app.clipboard_append("beta")

    _shortcut(entry, "v")

    assert entry.get() == "beta"
    assert _titles(app) == ["Beta notes"]
    assert app.list_body._search_box._clear_button.winfo_ismapped(), "the X shows"

    entry.selection_range(0, "end")
    _shortcut(entry, "x")

    assert entry.get() == ""
    assert _titles(app) == ["Alpha notes", "Beta notes"]
    assert not app.list_body._search_box._clear_button.winfo_ismapped(), "the X is gone"
    assert app.clipboard_get() == "beta", "the cut went to the clipboard"
