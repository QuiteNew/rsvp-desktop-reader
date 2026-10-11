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


def _load_chunking_transcript(application, enabled, size):
    """Add a transcript seeded with chunking and open it, so the reader goes
    live with its words already grouped. Returns the Transcript (the store
    mutates it in place, so the test can read its fields back directly)."""
    store = application.store
    transcript = store.add_transcript("Chunk smoke", store.current_space)
    store.set_transcript_text(transcript.id, "one two three four five six seven eight")
    store.set_transcript_chunking(transcript.id, enabled, size)
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


def test_settings_font_size_seeds_from_the_saved_default(app):
    """Regression for the Settings default-font-size fix: the slider must seed
    from the saved default like the other defaults, not from the open
    transcript's own size. Loads a transcript at a non-default size and
    confirms Settings still shows the saved default."""
    store = app.store
    transcript = store.add_transcript("Big font", store.current_space)
    store.set_transcript_text(transcript.id, "one two three four five")
    store.set_transcript_font_size(transcript.id, 60)  # a size that isn't the saved default
    app._handle_open_transcript(transcript)

    app._open_settings_window()
    try:
        assert app._settings_window.default_font_size == app.settings_store.default_font_size
    finally:
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


def test_pause_and_restart_route_to_the_detached_reader(app):
    """Regression for the detached-routing bug: while a transcript is
    detached, the main window's toggle_pause()/restart() must drive the
    detached reader (like skip and the bookmark controls already do), not the
    stopped main reader. Reattaches at the end so the shared app is left clean
    for the test that runs after it."""
    _load_reading_transcript(app)
    app.canvas._handle_detach()
    detached = app.canvas._detached_window
    assert detached is not None

    detached_reader = detached.reader_display
    paused_before = detached_reader._is_paused
    app.canvas.toggle_pause()
    # The detached reader toggled, and the stopped main reader stayed stopped.
    assert detached_reader._is_paused != paused_before
    assert app.canvas.reader_display.session is None

    app.canvas.restart()
    assert detached_reader._is_paused is False  # restart always resumes

    app.canvas._handle_reattach()
    assert app.canvas._detached_window is None


def test_footer_chunking_controls_drive_the_reader(app):
    """The footer's Group switch and size stepper re-group the live reader in
    place: the toggle and the stepper both route footer -> app -> store and
    canvas, and the reader keeps the very same ReaderSession object (a
    re-group, not a restart). Starts from a plain single-word reader and
    confirms enabling and resizing land on that session."""
    _load_reading_transcript(app)
    reader = app.canvas.reader_display
    session = reader.session
    assert session is not None and session.chunking_enabled is False

    # Turn chunking on through the footer switch, exactly as a click would.
    app.footer.chunk_switch.select()
    app.footer._handle_chunk_toggle()
    assert reader.session is session          # same session, re-grouped in place
    assert session.chunking_enabled is True

    # Bump the size through the footer stepper (seeded at 2 -> 3).
    app.footer._handle_chunk_increase()
    assert reader.session is session
    assert session.chunk_size == 3

    app.canvas.stop()


def test_chunking_change_does_not_finalize_the_session(app):
    """A chunking change must never end the reading session: it does not
    finalize (so it banks no 'read' and resets no counters) and leaves the
    active-time span open, so toggling mid-read can't inflate the stats. This
    is the guarantee behind choosing an in-place re-group over a reload."""
    transcript = _load_reading_transcript(app)
    reader = app.canvas.reader_display
    assert reader.session is not None
    assert reader._active_span_start is not None       # playing: a span is open

    words_before = reader._session_words_read
    span_before = reader._active_span_start
    reads_before = transcript.times_read

    app._handle_chunking_changed(True, 3)

    # Still the same live session, not stopped or finished.
    assert reader.session is not None and not reader.session.is_finished
    # No finalize happened: counters untouched and the same span still open.
    assert reader._session_words_read == words_before
    assert reader._active_span_start == span_before
    assert transcript.times_read == reads_before

    app.canvas.stop()


def test_detached_window_inherits_chunking(app):
    """A detached window builds its reader from the transcript's chunking, and
    the footer control (routed through the app) re-groups the detached reader
    while a transcript is detached, the same way WPM and colours already reach
    it. Reattaches at the end so the shared app is left clean."""
    _load_chunking_transcript(app, enabled=True, size=3)
    app.canvas._handle_detach()
    detached = app.canvas._detached_window
    assert detached is not None

    dsession = detached.reader_display.session
    assert dsession is not None
    assert dsession.chunking_enabled is True and dsession.chunk_size == 3

    # A footer-driven change while detached reaches the detached reader; the
    # stopped main reader has no session, so the forwarded call there no-ops.
    app._handle_chunking_changed(True, 5)
    assert detached.reader_display.session.chunk_size == 5
    assert app.canvas.reader_display.session is None

    app.canvas._handle_reattach()
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