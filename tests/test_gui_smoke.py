"""GUI smoke tests: construct the app and its windows and run a few reader
actions, asserting nothing throws. This is the layer that would have caught
the Settings-window argument mismatch that slipped through earlier.

It is deliberately shallow: no click simulation, no asserting on pixels,
just "the wiring holds together." Persistence is redirected to a temp
directory, so these tests never read or write the real ~/.rsvp_reader, and
they skip cleanly if Tk can't start a display.

One app (one Tk root) is shared across the whole module, on purpose:
CustomTkinter binds cached images to the root that was current when they
were created, so building a second root in the same process (a fresh app
per test) makes those images blow up. One root for the module avoids that
entirely; each test cleans up whatever window it opens."""

import pytest

import core.storage as storage
import core.settings_store as settings_store
import core.transcript_store as transcript_store

# Every default-location constant the stores read, redirected together.
# SETTINGS_DIR is what SettingsStore uses directly; the DEFAULT_DATA_DIR
# copies feed AppSettings.data_directory (and thus the TranscriptStore
# location) and the stores' own fallbacks.
_REDIRECT_TARGETS = (
    (storage, "DEFAULT_DATA_DIR"),
    (settings_store, "DEFAULT_DATA_DIR"),
    (settings_store, "SETTINGS_DIR"),
    (transcript_store, "DEFAULT_DATA_DIR"),
)


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    """A single RSVPApp shared across this module, with persistence pointed
    at a throwaway temp directory so the tests never touch the real
    ~/.rsvp_reader. Withdrawn (kept off screen) and destroyed at the end.
    Skips if Tk has no display."""
    import tkinter

    data_dir = tmp_path_factory.mktemp("rsvp_smoke")
    originals = [(mod, name, getattr(mod, name)) for mod, name in _REDIRECT_TARGETS]
    for mod, name in _REDIRECT_TARGETS:
        setattr(mod, name, data_dir)

    def _restore():
        for mod, name, value in originals:
            setattr(mod, name, value)

    from gui.app import RSVPApp

    try:
        application = RSVPApp()
    except tkinter.TclError as exc:
        _restore()
        pytest.skip(f"Tk can't start a display here: {exc}")

    application.withdraw()          # keep it off screen for the tests
    application.update_idletasks()  # flush pending layout so any error surfaces now
    try:
        yield application
    finally:
        application.destroy()
        _restore()


def _load_reading_transcript(application):
    """Add a transcript with real text and open it, so the reader is live
    (not the edit box). Returns the Transcript, which the store mutates in
    place, so the test can read bookmarks back off it directly."""
    store = application.store
    transcript = store.add_transcript("Smoke test", store.current_space)
    store.set_transcript_text(transcript.id, "one two three four five six seven eight")
    application._handle_open_transcript(transcript)
    return transcript


def test_app_constructs(app):
    # The fixture already built it; just confirm the main pieces are wired.
    assert app.canvas is not None
    assert app.header is not None
    assert app.footer is not None


def test_opens_settings_window(app):
    # The exact class of bug that slipped through before: Settings
    # constructing with a mismatched argument list. Opening it is the test.
    app._open_settings_window()
    assert app._settings_window is not None
    assert app._settings_window.winfo_exists()
    app._settings_window.destroy()


def test_reader_actions_run(app):
    _load_reading_transcript(app)
    # A representative sweep of the reader controls; none should raise.
    app.canvas.toggle_pause()
    app.canvas.skip_forward()
    app.canvas.skip_backward()
    app.canvas.restart()
    app.canvas.toggle_bookmark_here()
    app.canvas.open_bookmarks()
    app.canvas._close_bookmarks_popover()
    app.canvas.stop()


def test_bookmark_from_reader_reaches_the_store(app):
    transcript = _load_reading_transcript(app)
    app.canvas.toggle_bookmark_here()
    # The toggle routed canvas -> app -> store and saved onto the transcript.
    assert len(transcript.bookmarks) == 1


def test_detached_window_opens_and_closes(app):
    _load_reading_transcript(app)
    app.canvas._handle_detach()
    detached = app.canvas._detached_window
    assert detached is not None and detached.winfo_exists()

    # Its own bookmarks popover opens and its own toggle works.
    detached.open_bookmarks()
    detached.toggle_bookmark_here()
    detached._close_bookmarks_popover()

    app.canvas._handle_reattach()  # closes the detached window and reattaches
    assert app.canvas._detached_window is None


def test_divider_click_without_drag_does_not_corrupt_saved_layout(app):
    """Regression for the still-click layout bug. A press and release with no
    drag in between still fires on_drag_end, which commits _pending_value, so
    drag-start has to seed _pending_value with the divider's current size.
    Without that, a click with no movement commits either a stale value left
    over from an earlier drag of the other divider, or None on the very first
    interaction (which writes null to settings.json and fails to load next
    launch). Runs last in the module, since it nudges the saved sidebar width."""
    store = app.settings_store

    # First-interaction case: force _pending_value back to its initial None,
    # then click the sidebar divider with no drag. drag-start must reseed it,
    # so the saved width stays put and is never written as None.
    app._pending_value = None
    sidebar_before = store.sidebar_width
    app._handle_sidebar_drag_start()
    app._handle_sidebar_drag_end()
    assert store.sidebar_width == sidebar_before
    assert isinstance(store.sidebar_width, int)  # never None

    # Cross-divider case: a real sidebar drag parks a width in _pending_value,
    # then a click on the bottom divider with no drag must not commit that
    # sidebar width as the band height.
    app._handle_sidebar_drag_start()
    app._handle_sidebar_drag(40)
    app._handle_sidebar_drag_end()
    band_before = store.bottom_band_height
    app._handle_bottom_band_drag_start()
    app._handle_bottom_band_drag_end()
    assert store.bottom_band_height == band_before