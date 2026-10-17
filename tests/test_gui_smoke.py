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
from core.reader import CHUNK_MODE_ADAPTIVE

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


def _load_adaptive_transcript(application, char_target):
    """Add a transcript in adaptive chunking mode and open it, so the reader
    goes live with its words grouped by width rather than a word count. Returns
    the Transcript (mutated in place by the store, so fields read back here)."""
    store = application.store
    transcript = store.add_transcript("Adaptive smoke", store.current_space)
    store.set_transcript_text(transcript.id, "one two three four five six seven eight")
    store.set_transcript_chunking(transcript.id, True, 3, CHUNK_MODE_ADAPTIVE, char_target)
    application._handle_open_transcript(transcript)
    return transcript


def _open_chunking_dialog(application):
    """Open Settings and build the chunking dialog exactly as
    app._open_chunking_settings does, returning it so a test can drive its
    controls directly. The caller destroys the dialog and the Settings window.
    The gui import is local, the same deferral the app fixture uses, so a
    display-less collection still skips rather than erroring here."""
    from gui.components.chunking_settings_window import ChunkingSettingsWindow

    application._open_settings_window()
    return ChunkingSettingsWindow(
        application._settings_window,
        default_enabled=application.settings_store.default_chunking_enabled,
        default_size=application.settings_store.default_chunk_size,
        default_mode=application.settings_store.default_chunk_mode,
        default_char_target=application.settings_store.default_chunk_char_target,
        transcript=application._current_transcript,
        on_apply=application._apply_chunking_settings,
    )


def _load_wide_chunk_transcript(application, font_size):
    """Add a transcript whose chunks group several words, at a large Word size,
    and open it, so auto-fit has a reason to shrink the rendered font. Returns
    the Transcript."""
    store = application.store
    transcript = store.add_transcript("Wide chunk", store.current_space)
    store.set_transcript_text(transcript.id, "alpha bravo charlie delta echo foxtrot golf hotel")
    store.set_transcript_font_size(transcript.id, font_size)
    store.set_transcript_chunking(transcript.id, True, 5)
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


def test_opens_chunking_settings_window(app):
    """The Configure-chunking opener builds the dialog with the exact argument
    list app hands it, the same argument-mismatch class of bug the Settings
    smoke test guards against. Opening it is the test. It is parented to the
    Settings window, so that is opened first, the way the button is only
    reachable from inside Settings; destroying Settings tears the dialog down
    with it."""
    app._open_settings_window()
    try:
        app._open_chunking_settings()  # must not raise
    finally:
        app._settings_window.destroy()


def test_chunking_dialog_applies_to_current_transcript(app):
    """Apply-to-current from the dialog re-groups the live reader in place (the
    same session, not a reload) and carries mode and adaptive width through to
    both the transcript and the session, not just the on/off and fixed size."""
    from gui.components.chunking_settings_window import TARGET_CURRENT

    transcript = _load_reading_transcript(app)
    reader = app.canvas.reader_display
    session = reader.session
    assert session is not None

    dialog = _open_chunking_dialog(app)
    try:
        dialog.target_selector.set(TARGET_CURRENT)
        dialog.group_switch.select()
        dialog.mode_selector.set("Adaptive")
        dialog.width_slider.set(40)
        dialog._handle_apply()
    finally:
        dialog.destroy()
        app._settings_window.destroy()

    # Same live session, re-grouped in place, now carrying the adaptive fields.
    assert reader.session is session
    assert session.chunking_enabled is True
    assert session.chunk_mode == CHUNK_MODE_ADAPTIVE
    assert session.chunk_char_target == 40
    # And persisted onto the transcript.
    assert transcript.chunk_mode == CHUNK_MODE_ADAPTIVE
    assert transcript.chunk_char_target == 40

    app.canvas.stop()


def test_chunking_dialog_applies_to_defaults_only(app):
    """Apply-to-defaults updates the new-transcript defaults, mode and width
    included, and leaves the open transcript untouched."""
    from gui.components.chunking_settings_window import TARGET_DEFAULTS

    transcript = _load_reading_transcript(app)
    mode_before = transcript.chunk_mode
    target_before = transcript.chunk_char_target

    dialog = _open_chunking_dialog(app)
    try:
        dialog.target_selector.set(TARGET_DEFAULTS)
        dialog.group_switch.select()
        dialog.mode_selector.set("Adaptive")
        dialog.size_slider.set(4)
        dialog.width_slider.set(50)
        dialog._handle_apply()
    finally:
        dialog.destroy()
        app._settings_window.destroy()

    settings = app.settings_store
    assert settings.default_chunking_enabled is True
    assert settings.default_chunk_mode == CHUNK_MODE_ADAPTIVE
    assert settings.default_chunk_size == 4
    assert settings.default_chunk_char_target == 50
    # A defaults-only change never reaches the open transcript.
    assert transcript.chunk_mode == mode_before
    assert transcript.chunk_char_target == target_before

    app.canvas.stop()


def test_adaptive_transcript_reads_in_main_window(app):
    """A transcript in adaptive mode opens into a live reader whose session
    carries the adaptive mode and width; a representative reader sweep still
    runs clean under width-driven grouping."""
    _load_adaptive_transcript(app, char_target=35)
    session = app.canvas.reader_display.session
    assert session is not None
    assert session.chunking_enabled is True
    assert session.chunk_mode == CHUNK_MODE_ADAPTIVE
    assert session.chunk_char_target == 35

    app.canvas.toggle_pause()
    app.canvas.skip_forward()
    app.canvas.skip_backward()
    app.canvas.restart()
    app.canvas.stop()


def test_adaptive_transcript_reads_in_detached_window(app):
    """Adaptive grouping reaches the detached window too: it builds its reader
    from the transcript's adaptive fields, the same way fixed chunking already
    carries across. Reattaches at the end so the shared app is left clean."""
    _load_adaptive_transcript(app, char_target=35)
    app.canvas._handle_detach()
    detached = app.canvas._detached_window
    assert detached is not None

    dsession = detached.reader_display.session
    assert dsession is not None
    assert dsession.chunk_mode == CHUNK_MODE_ADAPTIVE
    assert dsession.chunk_char_target == 35

    app.canvas._handle_reattach()
    assert app.canvas._detached_window is None


def test_autofit_records_chosen_size_and_measures_widest_chunk(app):
    """Opening a chunked transcript records the chosen Word size, measures a
    widest chunk to fit to, and never renders larger than the chosen size. The
    exact shrink depends on the live window width, so it is checked by eye on a
    real display rather than asserted here (this layer does not assert pixels)."""
    _load_wide_chunk_transcript(app, font_size=80)
    reader = app.canvas.reader_display
    assert reader._chosen_font_size == 80
    assert reader._fit_widest is not None
    assert reader.word_font.cget("size") <= 80
    app.canvas.stop()


def test_autofit_is_render_only_and_leaves_the_saved_size(app):
    """Auto-fit changes only the on-screen font; the transcript's saved Word
    size is untouched, whatever the render size ends up being."""
    transcript = _load_wide_chunk_transcript(app, font_size=80)
    assert transcript.font_size == 80
    app.canvas.stop()


def test_autofit_runs_for_a_plain_transcript_too(app):
    """A single-word transcript still routes through the fit cleanly: the chosen
    size is recorded and the render size never exceeds it."""
    _load_reading_transcript(app)
    reader = app.canvas.reader_display
    assert reader.word_font.cget("size") <= reader._chosen_font_size
    app.canvas.stop()


def test_autofit_wires_into_the_detached_window(app):
    """The detached window runs the same auto-fit: loading a wide chunk there
    measures a widest chunk and renders no larger than its own chosen size.
    Reattaches at the end so the shared app is left clean."""
    _load_wide_chunk_transcript(app, font_size=80)
    app.canvas._handle_detach()
    detached = app.canvas._detached_window
    assert detached is not None

    drd = detached.reader_display
    assert drd._fit_widest is not None
    assert drd.word_font.cget("size") <= drd._chosen_font_size

    app.canvas._handle_reattach()
    assert app.canvas._detached_window is None


def test_scrollbar_hidden_and_centred_when_the_flash_fits(app, monkeypatch):
    """When the widest chunk fits the reading row, the horizontal scrollbar is
    packed away and the pan is reset to centred. The 'fits' case is forced (both
    overflows zero) so the result does not hang on the withdrawn test window's
    live width, which is unreliable off screen; the pixel arithmetic itself is
    covered by the core scroll tests."""
    _load_reading_transcript(app)
    reader = app.canvas.reader_display
    monkeypatch.setattr(reader, "_pan_overflows", lambda: (0.0, 0.0, 400.0))
    reader._pan_offset_px = 123.0          # a stale pan, as if left over from a wide chunk
    reader._update_scrollbar()
    assert reader._scrollbar_visible is False
    assert reader._pan_offset_px == 0.0    # reset to centred
    app.canvas.stop()


def test_scrollbar_appears_and_pans_when_a_chunk_overflows(app, monkeypatch):
    """When the widest chunk still spills past the row after fitting, the
    scrollbar is shown and its Tk commands pan the flash. The overflow is forced
    to fixed pixels so the glue is exercised without depending on the live
    geometry: a 'moveto' to the far right reveals the right overflow (the most
    negative pan), and unit scrolls step by SCROLL_UNIT_PX within the clamp. Ends
    by forcing the fits case so the shared reader is left with no scrollbar."""
    _load_reading_transcript(app)
    reader = app.canvas.reader_display
    monkeypatch.setattr(reader, "_pan_overflows", lambda: (0.0, 60.0, 300.0))

    reader._update_scrollbar()
    assert reader._scrollbar_visible is True

    # Drag the thumb fully right: reveals the right overflow, pan = -60.
    reader._handle_scroll("moveto", "1.0")
    assert abs(reader._pan_offset_px - (-60.0)) < 1e-6

    # A unit scroll further right is clamped at that limit (nothing more to show).
    reader._handle_scroll("scroll", "1", "units")
    assert abs(reader._pan_offset_px - (-60.0)) < 1e-6

    # Scrolling back the other way steps in by exactly one unit.
    reader._handle_scroll("scroll", "-1", "units")
    assert abs(reader._pan_offset_px - (-60.0 + reader.SCROLL_UNIT_PX)) < 1e-6

    # Force the fits case to pack the scrollbar away before leaving.
    monkeypatch.setattr(reader, "_pan_overflows", lambda: (0.0, 0.0, 300.0))
    reader._update_scrollbar()
    assert reader._scrollbar_visible is False
    app.canvas.stop()


def test_scrollbar_wires_into_the_detached_window(app, monkeypatch):
    """The detached window runs the same horizontal scroll on its own reader:
    forcing an overflow shows its scrollbar and a drag pans that reader. Forces
    the fits case and reattaches at the end so the shared app is left clean."""
    _load_reading_transcript(app)
    app.canvas._handle_detach()
    detached = app.canvas._detached_window
    assert detached is not None

    drd = detached.reader_display
    monkeypatch.setattr(drd, "_pan_overflows", lambda: (40.0, 0.0, 300.0))
    drd._update_scrollbar()
    assert drd._scrollbar_visible is True

    # Drag the thumb fully left: reveals the left overflow, pan = +40.
    drd._handle_scroll("moveto", "0.0")
    assert abs(drd._pan_offset_px - 40.0) < 1e-6

    monkeypatch.setattr(drd, "_pan_overflows", lambda: (0.0, 0.0, 300.0))
    drd._update_scrollbar()
    assert drd._scrollbar_visible is False

    app.canvas._handle_reattach()
    assert app.canvas._detached_window is None


def test_center_button_follows_the_scrollbar(app, monkeypatch):
    """The small centre button is shown while the scrollbar is, and removed with
    it. The overflow is forced to fixed pixels, as in the scrollbar tests, so
    this checks the show/hide wiring without depending on live geometry. Ends by
    forcing the fits case so the shared reader is left with no scrollbar."""
    _load_reading_transcript(app)
    reader = app.canvas.reader_display

    monkeypatch.setattr(reader, "_pan_overflows", lambda: (0.0, 60.0, 300.0))
    reader._update_scrollbar()
    assert reader._scrollbar_visible is True
    assert reader._center_button.winfo_manager() == "place"

    monkeypatch.setattr(reader, "_pan_overflows", lambda: (0.0, 0.0, 300.0))
    reader._update_scrollbar()
    assert reader._scrollbar_visible is False
    assert reader._center_button.winfo_manager() == ""
    app.canvas.stop()


def test_center_pan_returns_the_flash_to_centre(app, monkeypatch):
    """center_pan() undoes a pan, whether it is called directly or through the
    button's command, and is harmless when already centred."""
    _load_reading_transcript(app)
    reader = app.canvas.reader_display
    monkeypatch.setattr(reader, "_pan_overflows", lambda: (0.0, 60.0, 300.0))
    reader._update_scrollbar()

    reader._handle_scroll("moveto", "1.0")
    assert abs(reader._pan_offset_px - (-60.0)) < 1e-6
    reader.center_pan()
    assert reader._pan_offset_px == 0.0

    # The button is wired to the same action.
    reader._handle_scroll("moveto", "1.0")
    assert reader._pan_offset_px != 0.0
    reader._center_button.invoke()
    assert reader._pan_offset_px == 0.0

    # Already centred: a second call changes nothing and does not raise.
    reader.center_pan()
    assert reader._pan_offset_px == 0.0

    monkeypatch.setattr(reader, "_pan_overflows", lambda: (0.0, 0.0, 300.0))
    reader._update_scrollbar()
    app.canvas.stop()


def test_center_shortcut_reaches_the_main_and_detached_readers(app, monkeypatch):
    """The C shortcut routes like pause and restart: to the main reader normally
    and to the detached reader while a transcript is detached. The focus guard
    is forced open so the result does not depend on which widget happens to hold
    focus in the test window. Reattaches at the end so the shared app is clean."""
    _load_reading_transcript(app)
    reader = app.canvas.reader_display
    monkeypatch.setattr(reader, "_pan_overflows", lambda: (0.0, 60.0, 300.0))
    reader._update_scrollbar()
    reader._handle_scroll("moveto", "1.0")
    assert reader._pan_offset_px != 0.0

    monkeypatch.setattr(app, "_shortcut_should_fire", lambda: True)
    app._handle_shortcut_center()
    assert reader._pan_offset_px == 0.0

    monkeypatch.setattr(reader, "_pan_overflows", lambda: (0.0, 0.0, 300.0))
    reader._update_scrollbar()

    app.canvas._handle_detach()
    detached = app.canvas._detached_window
    assert detached is not None
    drd = detached.reader_display
    monkeypatch.setattr(drd, "_pan_overflows", lambda: (40.0, 0.0, 300.0))
    drd._update_scrollbar()
    drd._handle_scroll("moveto", "0.0")
    assert abs(drd._pan_offset_px - 40.0) < 1e-6

    # Through the main window's routing, then through the window's own binding.
    app.canvas.center_pan()
    assert drd._pan_offset_px == 0.0
    drd._handle_scroll("moveto", "0.0")
    monkeypatch.setattr(detached, "_shortcut_should_fire", lambda: True)
    detached._handle_shortcut_center()
    assert drd._pan_offset_px == 0.0

    monkeypatch.setattr(drd, "_pan_overflows", lambda: (0.0, 0.0, 300.0))
    drd._update_scrollbar()
    app.canvas._handle_reattach()
    assert app.canvas._detached_window is None

def test_search_box_shows_the_clear_button_only_while_there_is_text(app):
    """The shared search box: empty, it shows no X; with text it shows the X;
    the X (clear) puts it back to empty."""
    from gui.components.search_box import SearchBox

    box = SearchBox(app)
    try:
        assert box.get() == ""
        assert box._clear_button.winfo_manager() == ""

        box.set_text("abc")
        assert box.get() == "abc"
        assert box._clear_button.winfo_manager() == "place"

        box.clear()
        assert box.get() == ""
        assert box._clear_button.winfo_manager() == ""
    finally:
        box.destroy()

def test_transcript_search_filters_and_the_clear_button_restores_the_list(app):
    """The transcript list's search runs through the shared search box: typing
    narrows the rows, a search that matches nothing shows the message, and
    clearing brings every row back. Puts the real list back at the end."""
    from types import SimpleNamespace

    def fake(transcript_id, title):
        return SimpleNamespace(id=transcript_id, title=title, times_read=0, total_time_spent_seconds=0)

    body = app.list_body
    body.render_transcripts([fake(1, "Alpha notes"), fake(2, "Beta notes")])
    try:
        assert len(body.entries_frame.winfo_children()) == 2

        body._search_box.set_text("alp")
        assert len(body.entries_frame.winfo_children()) == 1

        body._search_box.set_text("zzz")
        children = body.entries_frame.winfo_children()
        assert len(children) == 1  # the "No transcripts match" message
        assert children[0].cget("text") == "No transcripts match your search."

        body._search_box.clear()
        assert len(body.entries_frame.winfo_children()) == 2
    finally:
        body._search_box.clear()
        app._refresh_transcript_list()

def test_settings_search_filters_the_defaults_tab(app):
    """Typing in the Defaults tab's search box narrows the list live, in the
    original order. Notes and the reset row are hidden while a search is active
    and come back when it is cleared."""
    app._open_settings_window()
    window = app._settings_window
    try:
        items = window._defaults_items
        settings = [item.name for item in items if item.searchable]
        others = [item for item in items if not item.searchable]

        def shown():
            return [item.name for item in items if item.searchable and item.holder.winfo_manager() == "pack"]

        assert shown() == settings
        assert all(item.holder.winfo_manager() == "pack" for item in others)

        window._defaults_search.set_text("crosshair")
        assert shown() == [
            "Thickness of the vertical guide marks, in pixels",
            "Mark length",
            "Mark colour",
            "Show horizontal guide lines",
        ]
        assert all(item.holder.winfo_manager() == "" for item in others)

        window._defaults_search.set_text("zzzz")
        assert shown() == []

        window._defaults_search.clear()
        assert shown() == settings
        assert all(item.holder.winfo_manager() == "pack" for item in others)
    finally:
        window.destroy()

def test_settings_search_descriptions_toggle_messages_and_reset_note(app):
    """The descriptions toggle, the no-match message, and the reset note. With
    the toggle off a description-only word finds nothing and shows the message;
    turning it on finds the setting. A matching search hides the reset row and
    shows a note in its place; clearing brings everything back."""
    app._open_settings_window()
    window = app._settings_window
    try:
        items = window._defaults_items

        def shown():
            return [i.name for i in items if i.searchable and i.holder.winfo_manager() == "pack"]

        # "settle" appears only in the Ease-in setting's description.
        window._defaults_search.set_text("settle")
        assert shown() == []
        assert window._defaults_no_match.winfo_manager() == "pack"
        assert window._defaults_reset_note.winfo_manager() == ""

        assert window._search_descriptions is False
        window._toggle_search_descriptions()
        assert window._search_descriptions is True
        assert "Ease in at the start of reading" in shown()
        assert window._defaults_no_match.winfo_manager() == ""

        # Back off, then a search that matches by name hides the reset row (one
        # of the non-searchable items) and shows the note in its place.
        window._toggle_search_descriptions()
        window._defaults_search.set_text("speed")
        assert shown()
        assert all(i.holder.winfo_manager() == "" for i in items if not i.searchable)
        assert window._defaults_reset_note.winfo_manager() == "pack"
        assert window._defaults_no_match.winfo_manager() == ""

        window._defaults_search.clear()
        assert window._defaults_reset_note.winfo_manager() == ""
        assert shown() == [i.name for i in items if i.searchable]
        assert all(i.holder.winfo_manager() == "pack" for i in items if not i.searchable)
    finally:
        window.destroy()

# ---- Settings About button and About dialog ----
#
# These tests open and close real CustomTkinter windows, which is the most
# delicate thing this suite does on Windows. Two rules keep them from taking
# the interpreter down with them, and both are worth reading before adding
# another test here.
#
# One Settings window is shared by nearly all of them, for the same reason the
# module shares a single app (see the note at the top of this file): CTk is
# built for a window being opened a handful of times over a session, not a
# dozen times in a few seconds. Only the test that has to watch Settings being
# built with particular colours makes its own.
#
# And every window is given time to finish starting up before anything touches
# it, and time to finish tearing down afterwards. A CTkToplevel on Windows does
# not come up in one go: its __init__ hides the window, recolours the titlebar
# and calls update(), then leaves the rest to a string of timers, 5ms to put
# the window back on screen, 10ms to restore focus, another 10ms from
# resizable() to run the whole titlebar routine a second time, 200ms to set the
# icon, 1000ms to settle its min and max size. Our own dialogs add an 80ms
# reveal on top. In the app that sequence always completes, because the event
# loop runs continuously between a person's clicks. In a test nothing runs the
# loop unless we ask, so a window built and destroyed back to back is destroyed
# halfway through its own startup, with Tk's window bookkeeping still mid-change
# and the leftovers queued for whatever window is unlucky enough to call
# update() next. _settle() is what asks, and it is why these tests briefly flash
# real windows on screen while they run.


def _all_widgets(root):
    """root and every widget below it, depth first."""
    found = [root]
    for child in root.winfo_children():
        found.extend(_all_widgets(child))
    return found


def _labels_by_text(root):
    """Every CTkLabel under root, keyed by its text."""
    import customtkinter as ctk

    return {w.cget("text"): w for w in _all_widgets(root) if isinstance(w, ctk.CTkLabel)}


def _find_button(root, text):
    """The CTkButton under root with this text."""
    import customtkinter as ctk

    for widget in _all_widgets(root):
        if isinstance(widget, ctk.CTkButton) and widget.cget("text") == text:
            return widget
    raise AssertionError(f"no button labelled {text!r}")


def _settle(widget, milliseconds=250):
    """Run Tk's event loop for a while, so everything already queued, timers
    included, gets a chance to finish.

    The default is long enough to cover a CTkToplevel's whole startup sequence
    (see the note at the top of this block), so a window that has been settled
    is one Tk has finished putting up and is safe to inspect or destroy."""
    import time

    end = time.monotonic() + milliseconds / 1000
    while time.monotonic() < end:
        widget.update()
        time.sleep(0.005)


def _cancel_pending_afters(window):
    """Cancel whatever Tk timers `window`, or anything inside it, still has
    queued. Only ever called on a settled window that is about to be destroyed,
    so what is left is the long tail, mainly CTkToplevel's 1000ms min and max
    size callback, that would otherwise fire against a freed widget.

    Each timer is cancelled through the widget that scheduled it, found by
    matching the timer's Tcl command name against that widget's own
    _tclCommands list. That detail matters: after_cancel deletes the timer's
    Tcl command and takes it off the calling widget's list, so cancelling
    through any other widget deletes the command while leaving it on its
    owner's list, and the owner then dies with "can't delete Tcl command" when
    it is destroyed. Timers belonging to anything outside this window, such as
    the main window's own widgets or CustomTkinter's DPI watcher, are left
    alone for the same reason."""
    owner_of = {}
    for widget in _all_widgets(window):
        for command_name in (getattr(widget, "_tclCommands", None) or ()):
            owner_of[command_name] = widget

    try:
        pending = window.tk.splitlist(window.tk.call("after", "info"))
    except Exception:
        return
    for after_id in pending:
        try:
            command_name = window.tk.splitlist(window.tk.call("after", "info", after_id))[0]
        except Exception:
            continue
        owner = owner_of.get(command_name)
        if owner is not None:
            try:
                owner.after_cancel(after_id)
            except Exception:
                pass


def _close(application, window):
    """Settle a window, then take it down and let the teardown drain. The
    application is only needed for that last part, since by then the window
    itself is gone and something live has to run the loop."""
    _settle(window)
    _cancel_pending_afters(window)
    window.destroy()
    _settle(application, 100)


def _open_about(settings_window):
    """Press the info button and return the About dialog it opened, settled and
    ready to inspect."""
    settings_window._info_button.invoke()
    dialog = settings_window._about_dialog
    _settle(dialog)
    return dialog


def _close_about(application, dialog, close=None):
    """Close an About dialog the way a person would, with its own Close button
    unless another way in is given, and let both the close and whatever it set
    off in Settings finish."""
    _cancel_pending_afters(dialog)
    (close or _find_button(dialog, "Close").invoke)()
    _settle(application, 150)


def _contrast_ratio(color_a, color_b):
    """WCAG contrast ratio between two "#RRGGBB" colours: 1.0 for identical
    colours up to 21.0 for black on white. Order does not matter."""
    def luminance(color):
        channels = []
        for start in (1, 3, 5):
            value = int(color[start:start + 2], 16) / 255
            channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    lighter, darker = sorted((luminance(color_a), luminance(color_b)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _solid_colour(ctk_image):
    """The average "#RRGGBB" of the fully opaque pixels of a CTkImage, which is
    the colour a drawn glyph actually came out as."""
    picture = ctk_image.cget("light_image")
    pixels = [picture.getpixel((x, y)) for x in range(picture.width) for y in range(picture.height)]
    solid = [pixel for pixel in pixels if pixel[3] == 255]
    assert solid, "expected some fully opaque pixels"
    red, green, blue = (round(sum(pixel[i] for pixel in solid) / len(solid)) for i in range(3))
    return f"#{red:02X}{green:02X}{blue:02X}"


@pytest.fixture(scope="module")
def settings(app):
    """One Settings window, built once and shared by the tests below, for the
    reason given at the top of this block. Every test that uses it has to leave
    it as it found it: no About dialog open, and its own attributes unchanged,
    which is what the monkeypatch calls and the geometry restore below are for."""
    app._open_settings_window()
    window = app._settings_window
    _settle(window)
    try:
        yield window
    finally:
        _close(app, window)


def test_contrast_ratio_helper_matches_known_values():
    assert _contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert _contrast_ratio("#FFFFFF", "#000000") == pytest.approx(21.0)
    assert _contrast_ratio("#777777", "#777777") == pytest.approx(1.0)
    # The widely quoted WCAG example: #767676 on white is the lightest grey
    # that still passes 4.5:1.
    assert _contrast_ratio("#767676", "#FFFFFF") == pytest.approx(4.54, abs=0.01)


def test_settings_info_button_opens_and_closes_the_about_dialog(app, settings):
    from gui.components.about_dialog import AboutDialog

    dialog = _open_about(settings)
    assert isinstance(dialog, AboutDialog)
    assert dialog.winfo_exists()
    assert dialog.title() == "About"

    _close_about(app, dialog)
    assert not dialog.winfo_exists()
    assert settings._about_dialog is None


def test_about_dialog_shows_the_app_details_and_the_icon(app, settings):
    from core.app_info import APP_NAME, APP_VERSION, LICENSE_NAME, REPO_URL

    dialog = _open_about(settings)
    try:
        labels = _labels_by_text(dialog)
        for expected in (
            APP_NAME,
            f"Version {APP_VERSION}",
            f"Released under the {LICENSE_NAME} License",
            REPO_URL.removeprefix("https://"),
        ):
            assert expected in labels

        with_image = [label for label in labels.values() if label.cget("image") is not None]
        assert len(with_image) == 1
        assert with_image[0].cget("image").cget("size") == (96, 96)
    finally:
        _close_about(app, dialog)


def test_about_link_opens_the_project_page_in_the_browser(app, settings, monkeypatch):
    import webbrowser
    from core.app_info import REPO_URL

    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url, *args, **kwargs: opened.append(url) or True)

    dialog = _open_about(settings)
    try:
        assert dialog._link.cget("cursor") == "hand2"
        # A click handler really is attached to the link, not just defined.
        assert dialog._link._label.bind("<Button-1>")

        dialog._open_repo()
        assert opened == [REPO_URL]
    finally:
        _close_about(app, dialog)


def test_pressing_the_info_button_twice_opens_one_about_dialog(app, settings):
    from gui.components.about_dialog import AboutDialog

    dialog = _open_about(settings)
    try:
        settings._info_button.invoke()
        assert settings._about_dialog is dialog
        assert sum(1 for w in settings.winfo_children() if isinstance(w, AboutDialog)) == 1
    finally:
        _close_about(app, dialog)


def test_about_dialog_can_be_opened_again_after_any_kind_of_close(app, settings):
    """Closed with its own button, with the window's close control, or
    destroyed behind Settings' back (so its close hook never ran), the info
    button must open a fresh dialog afterwards and never go dead."""
    dialog = _open_about(settings)
    _close_about(app, dialog)
    assert settings._about_dialog is None

    # The window manager's own close control, which the dialog routes through
    # the same handler as its button.
    dialog = _open_about(settings)
    _close_about(app, dialog, lambda: dialog.tk.call(dialog.protocol("WM_DELETE_WINDOW")))
    assert not dialog.winfo_exists()
    assert settings._about_dialog is None

    # Destroyed without going through the dialog's own handler at all, so
    # Settings is never told. The info button still has to recover.
    dialog = _open_about(settings)
    _close_about(app, dialog, dialog.destroy)

    replacement = _open_about(settings)
    try:
        assert replacement is not dialog
        assert replacement.winfo_exists()
    finally:
        _close_about(app, replacement)


def test_closing_the_about_dialog_hands_the_grab_back_to_settings(app, settings, monkeypatch):
    """The dialog's own input grab replaces Settings', so when it closes,
    Settings has to ask for its grab again (after a short delay). Checks the
    hand-back is requested, not Tk's grab bookkeeping itself."""
    calls = []
    monkeypatch.setattr(settings, "_regrab_if_still_open", lambda: calls.append("regrab"))

    dialog = _open_about(settings)
    try:
        _close_about(app, dialog)
        assert calls == ["regrab"]
    finally:
        if dialog.winfo_exists():
            _close_about(app, dialog)


def test_about_dialog_colours_follow_the_palette(app, settings, monkeypatch):
    """The dialog has to read well in both themes, not just the one the tests
    happen to run in. Swaps in each full palette for the colours the dialog
    imports, builds it, and checks its fill, its text colours and the contrast
    of the two blended ones against the paper. The blends are computed from the
    palette, so the dark dialog's greys and blues must also come out different
    from the light one's, which a hard-coded value would not."""
    from core.app_info import APP_NAME, APP_VERSION
    import gui.components.about_dialog as about_module
    from gui import theme

    blended = {}
    for palette_name, palette in (("light", theme.LIGHT_PALETTE), ("dark", theme.DARK_PALETTE)):
        with monkeypatch.context() as patch:
            for module_name, key in (
                ("HEARTH_PAPER", "hearth_paper"), ("COCOA_INK", "cocoa_ink"), ("DUSK_BLUE", "dusk_blue"),
                ("EMBER_GLOW", "ember_glow"), ("EMBER_GLOW_HOVER", "ember_glow_hover"),
            ):
                patch.setattr(about_module, module_name, palette[key])

            # Built directly rather than through the info button, since the
            # palette has to be in place before __init__ reads it. With no
            # on_close it never touches the shared window's own dialog slot.
            dialog = about_module.AboutDialog(settings)
            _settle(dialog)
            try:
                paper, ink = palette["hearth_paper"], palette["cocoa_ink"]
                labels = _labels_by_text(dialog)

                assert dialog.cget("fg_color") == paper
                assert labels[APP_NAME].cget("text_color") == ink
                assert labels[f"Version {APP_VERSION}"].cget("text_color") == dialog._muted_color
                assert labels[dialog._link.cget("text")].cget("text_color") == dialog._link_color
                assert _contrast_ratio(dialog._muted_color, paper) >= 4.5
                assert _contrast_ratio(dialog._link_color, paper) >= 4.5

                close = _find_button(dialog, "Close")
                assert close.cget("fg_color") == palette["ember_glow"]
                assert close.cget("hover_color") == palette["ember_glow_hover"]
                assert close.cget("text_color") == ink

                blended[palette_name] = (dialog._muted_color, dialog._link_color)
            finally:
                _close_about(app, dialog, dialog.destroy)

    assert blended["light"][0] != blended["dark"][0]
    assert blended["light"][1] != blended["dark"][1]


def test_info_button_colours_follow_the_palette(app, settings, monkeypatch):
    """The info button's chip, hover chip and glyph colours come from the theme,
    and the glyph stays visible against its chip in both palettes. This one
    builds its own Settings windows, since the palette has to be in place
    before Settings' __init__ draws the icons; the shared window is taken only
    to put the app's own reference back afterwards."""
    import gui.components.settings_window as settings_module
    from gui import theme

    for palette in (theme.LIGHT_PALETTE, theme.DARK_PALETTE):
        with monkeypatch.context() as patch:
            for module_name, key in (
                ("COCOA_INK", "cocoa_ink"), ("WARM_TAUPE", "warm_taupe"), ("WARM_LINE", "warm_line"),
            ):
                patch.setattr(settings_module, module_name, palette[key])

            app._open_settings_window()
            window = app._settings_window
            try:
                _settle(window)
                button = window._info_button
                assert button.cget("fg_color") == palette["warm_taupe"]
                assert button.cget("hover_color") == palette["warm_line"]
                assert button.cget("image") is window._info_rest_icon

                rest = _solid_colour(window._info_rest_icon)
                hover = _solid_colour(window._info_hover_icon)
                assert rest != hover
                assert _contrast_ratio(rest, palette["warm_taupe"]) >= 3.0
                assert _contrast_ratio(hover, palette["warm_line"]) >= 3.0
            finally:
                _close(app, window)
                app._settings_window = settings


def test_info_button_sits_above_the_tabs_at_the_right_edge(app, settings):
    """Top right, in a strip of its own, so it can never cover a tab: its
    bottom edge stays above the tab view's top edge, and it stays near the
    right edge of the window, at the usual size and at the smallest the window
    can be made."""
    original_geometry = settings.geometry()
    button = settings._info_button

    def check_position():
        settings.update()
        assert button.winfo_rooty() + button.winfo_height() <= settings.tabview.winfo_rooty()
        assert button.winfo_rootx() > settings.winfo_rootx() + settings.winfo_width() * 0.8
        assert button.winfo_rootx() + button.winfo_width() <= settings.winfo_rootx() + settings.winfo_width()

    try:
        check_position()
        settings.geometry("420x420")
        _settle(settings, 150)
        check_position()
    finally:
        settings.geometry(original_geometry)
        _settle(settings, 150)


# ---- Reading profiles ----
# Saving, snapshotting and applying a profile through the real app: the store
# and the live reader both have to end up holding the profile's values. The
# rules themselves (clamping, the guide mark colour, what a profile may hold)
# are tested without a window in test_profile_apply.py and test_profiles.py.

# A profile that differs from the fresh-install default on every setting.
_PROFILE_VALUES = {
    "highlight_offset_px": 2,
    "guide_mark_horizontal_enabled": True,
    "guide_mark_thickness_px": 4,
    "guide_mark_length_percent": 50,
    "guide_mark_color": "#112233",
    "length_pacing_enabled": True,
    "warm_up_enabled": True,
    "resume_rewind_enabled": True,
    "resume_rewind_words": 5,
    "peripheral_context_enabled": True,
    "skip_word_count": 30,
    "pause_on_skip": True,
    "default_wpm": 450,
    "default_font_size": 48,
    "font_size_step": 4,
    "split_long_paragraphs_enabled": True,
    "scrub_pause_enabled": False,
}


def _put_profile_settings_back(application, values, follows_theme):
    """Write a set of app-wide settings straight back through the store, so a
    test leaves the shared app as it found it. Deliberately not done with
    _apply_profile(), so a broken apply can't hide behind its own cleanup."""
    store = application.settings_store
    store.set_highlight_offset_px(values["highlight_offset_px"])
    store.set_guide_mark_horizontal_enabled(values["guide_mark_horizontal_enabled"])
    store.set_guide_mark_thickness_px(values["guide_mark_thickness_px"])
    store.set_guide_mark_length_percent(values["guide_mark_length_percent"])
    store.restore_guide_mark_color(values["guide_mark_color"], follows_theme)
    store.set_length_pacing_enabled(values["length_pacing_enabled"])
    store.set_warm_up_enabled(values["warm_up_enabled"])
    store.set_resume_rewind(values["resume_rewind_enabled"], values["resume_rewind_words"])
    store.set_peripheral_context_enabled(values["peripheral_context_enabled"])
    store.set_skip_behavior(values["skip_word_count"], values["pause_on_skip"])
    store.set_defaults(
        values["default_wpm"], store.default_font_color, store.default_highlight_color,
        store.default_background_color, values["default_font_size"],
    )
    store.set_font_size_step(values["font_size_step"])
    store.set_split_long_paragraphs_enabled(values["split_long_paragraphs_enabled"])
    store.set_scrub_pause_enabled(values["scrub_pause_enabled"])
    canvas = application.canvas
    application.footer.set_font_size_step(values["font_size_step"])
    canvas.set_split_long_paragraphs_enabled(values["split_long_paragraphs_enabled"])
    canvas.set_scrub_pause(values["scrub_pause_enabled"])
    canvas.set_highlight_offset(values["highlight_offset_px"])
    canvas.set_guide_mark_horizontal_enabled(values["guide_mark_horizontal_enabled"])
    canvas.set_guide_mark_thickness(values["guide_mark_thickness_px"])
    canvas.set_guide_mark_length_percent(values["guide_mark_length_percent"])
    canvas.set_guide_mark_color(values["guide_mark_color"])
    canvas.set_length_pacing_enabled(values["length_pacing_enabled"])
    canvas.set_warm_up_enabled(values["warm_up_enabled"])
    canvas.set_resume_rewind(values["resume_rewind_enabled"], values["resume_rewind_words"])
    canvas.set_peripheral_context_enabled(values["peripheral_context_enabled"])
    canvas.set_skip_word_count(values["skip_word_count"])
    canvas.set_pause_on_skip(values["pause_on_skip"])


@pytest.fixture
def profiles_sandbox(app):
    """Hands a test the shared app with no profiles saved, and puts the
    app-wide settings and the profile list back afterwards."""
    store = app.settings_store
    before = app._current_profile_settings()
    follows_before = store.guide_mark_color_is_default
    for profile in store.profiles:
        store.delete_profile(profile.name)
    try:
        yield app
    finally:
        for profile in store.profiles:
            store.delete_profile(profile.name)
        _put_profile_settings_back(app, before, follows_before)


def test_applying_a_profile_changes_every_app_wide_setting(profiles_sandbox):
    app = profiles_sandbox
    app.settings_store.add_profile("Everything", dict(_PROFILE_VALUES))
    app._apply_profile("Everything")

    # Saved in the store...
    assert app._current_profile_settings() == _PROFILE_VALUES
    # ...and live in the reader, without a restart.
    canvas = app.canvas
    assert canvas._highlight_offset_px == 2
    assert canvas._guide_mark_horizontal_enabled is True
    assert canvas._guide_mark_thickness_px == 4
    assert canvas._guide_mark_length_percent == 50
    assert canvas._guide_mark_color == "#112233"
    assert canvas._length_pacing_enabled is True
    assert canvas._warm_up_enabled is True
    assert canvas._resume_rewind_enabled is True
    assert canvas._resume_rewind_words == 5
    assert canvas._peripheral_context_enabled is True
    assert canvas._skip_word_count == 30
    assert canvas._pause_on_skip is True
    assert canvas._split_long_paragraphs_enabled is True
    assert canvas._scrub_pause_enabled is False
    assert app.footer._font_size_step == 4
    reader = canvas.reader_display
    assert reader._highlight_offset_px == 2
    assert reader._guide_mark_thickness_px == 4
    assert reader._resume_rewind_words == 5
    assert reader._peripheral_context_enabled is True
    assert reader._scrub_pause_enabled is False


def test_an_applied_profile_is_written_to_settings_json(profiles_sandbox):
    import json

    app = profiles_sandbox
    app.settings_store.add_profile("Everything", dict(_PROFILE_VALUES))
    app._apply_profile("Everything")

    saved = json.loads(app.settings_store._settings_file.read_text(encoding="utf-8"))
    for key, value in _PROFILE_VALUES.items():
        assert saved[key] == value, key
    assert saved["guide_mark_color_is_default"] is False


def test_applying_a_profile_leaves_transcripts_the_colours_and_chunking_alone(profiles_sandbox):
    app = profiles_sandbox
    store = app.settings_store
    transcript = app.store.add_transcript(
        "Profile bystander", app.store.current_space,
        wpm=600, font_color="#445566", highlight_color="#778899", background_color="#AABBCC",
        font_size=44, chunking_enabled=True, chunk_size=3,
    )
    transcript_before = dict(vars(transcript))
    # Known colours of its own, so the result can't depend on what an earlier
    # test left behind. Put back afterwards.
    original_colours = (store.default_font_color, store.default_highlight_color, store.default_background_color)
    store.set_defaults(store.default_wpm, "#445566", "#778899", "#AABBCC", store.default_font_size)
    untouched = ("default_font_color", "default_highlight_color", "default_background_color",
                 "default_chunking_enabled", "default_chunk_size",
                 "default_chunk_mode", "default_chunk_char_target", "appearance_mode",
                 "window_width", "sidebar_width")
    untouched_before = {key: getattr(store, key) for key in untouched}
    try:
        store.add_profile("Everything", dict(_PROFILE_VALUES))
        app._apply_profile("Everything")

        assert vars(transcript) == transcript_before
        assert {key: getattr(store, key) for key in untouched} == untouched_before
    finally:
        store.set_defaults(store.default_wpm, *original_colours, store.default_font_size)


def test_applying_a_profile_moves_the_speed_and_word_size_defaults_but_not_the_open_transcript(profiles_sandbox):
    app = profiles_sandbox
    store = app.settings_store
    transcript = _load_reading_transcript(app)
    wpm_before, size_before = transcript.wpm, transcript.font_size
    reader = app.canvas.reader_display
    original_colours = (store.default_font_color, store.default_highlight_color, store.default_background_color)
    store.set_defaults(store.default_wpm, "#445566", "#778899", "#AABBCC", store.default_font_size)
    colours_before = ("#445566", "#778899", "#AABBCC")
    assert (store.default_wpm, store.default_font_size) != (450, 48)
    try:
        store.add_profile("Quick", {"default_wpm": 450, "default_font_size": 48})
        app._apply_profile("Quick")

        # The Defaults sliders' values changed...
        assert store.default_wpm == 450
        assert store.default_font_size == 48
        # ...the colours that share their setter did not...
        assert (store.default_font_color, store.default_highlight_color, store.default_background_color) == colours_before
        # ...and neither did the transcript that is open, or the reader showing it.
        assert (transcript.wpm, transcript.font_size) == (wpm_before, size_before)
        assert reader.session is not None
    finally:
        store.set_defaults(store.default_wpm, *original_colours, store.default_font_size)
        app.canvas.stop()


def test_a_profile_saved_before_speed_and_size_joined_leaves_them_alone(profiles_sandbox):
    app = profiles_sandbox
    store = app.settings_store
    store.set_defaults(
        420, store.default_font_color, store.default_highlight_color,
        store.default_background_color, 40,
    )
    older = {key: value for key, value in _PROFILE_VALUES.items() if key not in (
        "default_wpm", "default_font_size", "font_size_step",
        "split_long_paragraphs_enabled", "scrub_pause_enabled")}
    store.add_profile("Older", older)
    app._apply_profile("Older")

    assert store.skip_word_count == 30           # what it does hold was applied
    assert store.default_wpm == 420              # what it doesn't hold was left alone
    assert store.default_font_size == 40


def test_a_profile_that_holds_only_some_settings_leaves_the_rest_as_they_are(profiles_sandbox):
    app = profiles_sandbox
    store = app.settings_store
    _put_profile_settings_back(app, {**_PROFILE_VALUES, "skip_word_count": 12, "pause_on_skip": True}, False)

    store.add_profile("Only skip", {"skip_word_count": 7})
    app._apply_profile("Only skip")

    # The skip amount changed, and the pause switch that shares its setter
    # kept the value it had.
    assert store.skip_word_count == 7
    assert store.pause_on_skip is True
    assert app.canvas._skip_word_count == 7
    assert app.canvas._pause_on_skip is True
    assert store.guide_mark_thickness_px == 4
    assert store.resume_rewind_words == 5


def test_a_number_outside_the_allowed_range_is_clamped_when_applied(profiles_sandbox):
    from core.settings_store import SKIP_WORD_COUNT_RANGE, GUIDE_MARK_THICKNESS_RANGE

    app = profiles_sandbox
    app.settings_store.add_profile("Too much", {"skip_word_count": 999, "guide_mark_thickness_px": 1})
    app._apply_profile("Too much")

    assert app.settings_store.skip_word_count == SKIP_WORD_COUNT_RANGE[1]
    assert app.canvas._skip_word_count == SKIP_WORD_COUNT_RANGE[1]
    assert app.settings_store.guide_mark_thickness_px == GUIDE_MARK_THICKNESS_RANGE[0]
    assert app.canvas._guide_mark_thickness_px == GUIDE_MARK_THICKNESS_RANGE[0]


def test_a_profile_that_followed_the_theme_gets_the_themes_guide_colour_back(profiles_sandbox):
    app = profiles_sandbox
    store = app.settings_store
    store.restore_guide_mark_color("#AABBCC", False)  # picked by hand, so not following

    store.add_profile("Themed", {"guide_mark_color": None})
    app._apply_profile("Themed")

    assert store.guide_mark_color == app._theme_guide_mark_color()
    assert store.guide_mark_color_is_default is True
    assert app.canvas._guide_mark_color == app._theme_guide_mark_color()


def test_a_guide_colour_picked_by_hand_stops_following_even_when_it_matches_the_theme(profiles_sandbox):
    app = profiles_sandbox
    store = app.settings_store
    theme_colour = app._theme_guide_mark_color()
    store.restore_guide_mark_color(theme_colour, True)

    store.add_profile("Hand picked", {"guide_mark_color": theme_colour})
    app._apply_profile("Hand picked")

    assert store.guide_mark_color == theme_colour
    assert store.guide_mark_color_is_default is False


def test_applying_a_profile_that_does_not_exist_raises_and_changes_nothing(profiles_sandbox):
    from core.profiles import ProfileError

    app = profiles_sandbox
    before = app._current_profile_settings()
    with pytest.raises(ProfileError) as caught:
        app._apply_profile("Nope")
    assert "Nope" in str(caught.value)
    assert app._current_profile_settings() == before


def test_the_theme_guide_colour_is_the_one_the_theme_defines(app):
    # Checked against the theme's own constants rather than against the app,
    # so swapping the Light and Dark colours would be caught here.
    from gui.theme import CTK_APPEARANCE_MODE, DARK_READING_GUIDE_MARK_COLOR, LIGHT_READING_GUIDE_MARK_COLOR

    expected = DARK_READING_GUIDE_MARK_COLOR if CTK_APPEARANCE_MODE == "Dark" else LIGHT_READING_GUIDE_MARK_COLOR
    assert app._theme_guide_mark_color() == expected


def test_the_snapshot_holds_every_profile_setting(profiles_sandbox):
    from core.profiles import PROFILE_KEYS

    assert set(profiles_sandbox._snapshot_current_settings()) == set(PROFILE_KEYS)


def test_the_snapshot_stores_a_guide_colour_that_follows_the_theme_as_none(profiles_sandbox):
    app = profiles_sandbox
    app.settings_store.restore_guide_mark_color(app._theme_guide_mark_color(), True)
    assert app._snapshot_current_settings()["guide_mark_color"] is None


def test_the_snapshot_stores_a_guide_colour_picked_by_hand_as_that_colour(profiles_sandbox):
    app = profiles_sandbox
    app.settings_store.restore_guide_mark_color("#AABBCC", False)
    assert app._snapshot_current_settings()["guide_mark_color"] == "#AABBCC"


def test_saving_then_applying_a_profile_brings_the_settings_back(profiles_sandbox):
    app = profiles_sandbox
    store = app.settings_store
    _put_profile_settings_back(app, _PROFILE_VALUES, False)
    app._save_profile("Mine")
    assert store.get_profile("Mine").values == _PROFILE_VALUES

    # Change everything the profile holds, then bring it back.
    other = {**_PROFILE_VALUES, "highlight_offset_px": -1, "guide_mark_horizontal_enabled": False,
             "guide_mark_thickness_px": 2, "guide_mark_length_percent": 20, "guide_mark_color": "#FFEEDD",
             "length_pacing_enabled": False, "warm_up_enabled": False, "resume_rewind_enabled": False,
             "resume_rewind_words": 1, "peripheral_context_enabled": False, "skip_word_count": 3,
             "pause_on_skip": False}
    _put_profile_settings_back(app, other, False)
    assert app._current_profile_settings() == other

    app._apply_profile("Mine")
    assert app._current_profile_settings() == _PROFILE_VALUES


def test_a_profile_saved_while_following_the_theme_keeps_following_when_applied(profiles_sandbox):
    app = profiles_sandbox
    store = app.settings_store
    store.restore_guide_mark_color(app._theme_guide_mark_color(), True)
    app._save_profile("Following")
    assert store.get_profile("Following").values["guide_mark_color"] is None

    store.restore_guide_mark_color("#AABBCC", False)
    app._apply_profile("Following")
    assert store.guide_mark_color == app._theme_guide_mark_color()
    assert store.guide_mark_color_is_default is True


def test_saving_a_profile_under_a_name_that_is_taken_raises_and_adds_nothing(profiles_sandbox):
    from core.profiles import ProfileError

    app = profiles_sandbox
    app._save_profile("Mine")
    with pytest.raises(ProfileError):
        app._save_profile("mine")
    assert [p.name for p in app.settings_store.profiles] == ["Mine"]


def test_updating_a_profile_replaces_its_settings_and_keeps_its_name(profiles_sandbox):
    app = profiles_sandbox
    store = app.settings_store
    _put_profile_settings_back(app, _PROFILE_VALUES, False)
    app._save_profile("Mine")

    _put_profile_settings_back(app, {**_PROFILE_VALUES, "skip_word_count": 9}, False)
    app._update_profile("Mine")

    assert [p.name for p in store.profiles] == ["Mine"]
    assert store.get_profile("Mine").values["skip_word_count"] == 9


def test_updating_a_profile_that_does_not_exist_raises(profiles_sandbox):
    from core.profiles import ProfileError

    with pytest.raises(ProfileError):
        profiles_sandbox._update_profile("Nope")


def test_applying_a_profile_reaches_a_detached_reader(profiles_sandbox):
    app = profiles_sandbox
    _load_reading_transcript(app)
    app.canvas._handle_detach()
    detached = app.canvas._detached_window
    assert detached is not None
    try:
        app.settings_store.add_profile("Everything", dict(_PROFILE_VALUES))
        app._apply_profile("Everything")
        assert detached.reader_display._guide_mark_thickness_px == 4
        assert detached.reader_display._highlight_offset_px == 2
    finally:
        app.canvas._handle_reattach()
    assert app.canvas._detached_window is None


# ---- Profiles tab ----
# The tab in the Settings window, driven the way a person would: typing into
# Settings' controls, pressing the tab's buttons, filling in its popups. What
# applying, saving and snapshotting do to the settings themselves is covered
# above, so these are about the screen and what it hands to the app. Saving,
# updating and applying all start by running Settings' Apply, so the tests
# change the window's controls (never the store directly) before pressing them.
#
# These use the same shared Settings window as the About tests, and every
# popup is given time to finish opening and closing (see _settle), for the
# reasons in the note above those tests.


def _read_controls(window):
    """The few Settings controls these tests change, so they can be put back."""
    return {
        "thickness": window.guide_mark_thickness_entry.get(),
        "warm_up": bool(window.warm_up_switch.get()),
        "skip": window.skip_word_count_slider.get(),
    }


def _write_controls(window, saved):
    window._set_entry_value(window.guide_mark_thickness_entry, saved["thickness"])
    (window.warm_up_switch.select() if saved["warm_up"] else window.warm_up_switch.deselect())
    window.skip_word_count_slider.set(saved["skip"])


def _popup_of(tab):
    """The popup the tab has just opened, settled and ready to use."""
    popup = tab._popup
    assert popup is not None and popup.winfo_exists()
    _settle(popup)
    return popup


def _finish_popup(application, popup, action):
    """Press a button in a Profiles tab popup, then let the popup close and
    Settings take its grab back."""
    _cancel_pending_afters(popup)
    action()
    _settle(application, 150)


def _type_name(popup, text):
    popup.name_entry.delete(0, "end")
    popup.name_entry.insert(0, text)


def _assert_popup_not_clipped(popup):
    """A window that is shorter than what its content asks for silently cuts
    the content off, so check there is room."""
    popup.update()
    assert popup.winfo_reqheight() <= popup.winfo_height()


def _click_tab(window, name):
    """Press a tab's button in the Settings tab bar, the way a person does.
    Unlike tabview.set(), this goes through CustomTkinter's click handling, so
    the tab view's command runs too, which is what hides and shows the window's
    Apply button."""
    window.tabview._segmented_button._buttons_dict[name].invoke()


@pytest.fixture
def profile_tab(app, settings, profiles_sandbox):
    """The shared Settings window's Profiles tab, shown, with no profiles saved.
    Afterwards it closes any popup left open, removes the profiles, puts the
    controls these tests change back, and returns to the Defaults tab."""
    tab = settings.profiles_tab
    controls = _read_controls(settings)
    _click_tab(settings, "Profiles")
    tab.refresh()
    try:
        yield tab
    finally:
        popup = tab._popup
        if popup is not None and popup.winfo_exists():
            _cancel_pending_afters(popup)
            popup.destroy()
            tab._popup = None
        for profile in app.settings_store.profiles:
            app.settings_store.delete_profile(profile.name)
        tab.refresh()
        _write_controls(settings, controls)
        settings._show_message("")
        _click_tab(settings, "Defaults")
        _settle(app, 100)


def test_the_profiles_tab_sits_between_appearance_and_stats(settings):
    assert settings.tabview._name_list == ["Defaults", "Layout", "Storage", "Appearance", "Profiles", "Stats"]


def test_the_profiles_tab_says_what_a_profile_does_and_does_not_change(settings):
    labels = _labels_by_text(settings.profiles_tab)
    explanation = next(text for text in labels if text.startswith("A profile is"))
    assert "never changes a transcript, your colours or chunking" in explanation
    assert "Speed and Word size only set where new transcripts start" in explanation
    # Speed and Word size are Defaults sliders and do switch, so the text must
    # not promise that the Defaults are left alone.
    assert "your Defaults" not in explanation
    assert "spaces" in explanation
    note = next(text for text in labels if text.startswith("Saving, updating or applying"))
    assert "first applies" in note
    # Settings' own Apply is hidden on this tab, so the note must not send
    # anyone looking for it.
    assert "other tabs" in note
    assert "pressing Apply" not in note


def test_an_empty_profiles_tab_says_so_and_has_nothing_to_act_on(profile_tab):
    assert any(text.startswith("No profiles yet") for text in _labels_by_text(profile_tab.list_frame))
    assert profile_tab.selected_name is None
    for button in profile_tab._action_buttons:
        assert button.cget("state") == "disabled"


def test_saved_profiles_are_listed_in_order_and_none_starts_selected(app, profile_tab):
    app._save_profile("Fast skim")
    app._save_profile("Careful read")
    profile_tab.refresh()
    assert list(profile_tab._rows) == ["Fast skim", "Careful read"]
    assert profile_tab.selected_name is None
    assert not any(text.startswith("No profiles yet") for text in _labels_by_text(profile_tab.list_frame))
    for button in profile_tab._action_buttons:
        assert button.cget("state") == "disabled"


def test_clicking_the_selected_row_again_unselects_it(app, profile_tab):
    from gui.theme import EMBER_GLOW

    app._save_profile("Fast skim")
    app._save_profile("Careful read")
    profile_tab.refresh()

    row = profile_tab._rows["Fast skim"]
    row.invoke()
    assert profile_tab.selected_name == "Fast skim"
    assert row.cget("fg_color") == EMBER_GLOW

    # The second click puts everything back the way it was before the first.
    row.invoke()
    assert profile_tab.selected_name is None
    assert row.cget("fg_color") == "transparent"
    for button in profile_tab._action_buttons:
        assert button.cget("state") == "disabled"

    # And it can be selected again after that.
    row.invoke()
    assert profile_tab.selected_name == "Fast skim"
    assert row.cget("fg_color") == EMBER_GLOW
    for button in profile_tab._action_buttons:
        assert button.cget("state") == "normal"


def test_clicking_a_different_row_moves_the_selection_instead_of_clearing_it(app, profile_tab):
    from gui.theme import EMBER_GLOW

    app._save_profile("Fast skim")
    app._save_profile("Careful read")
    profile_tab.refresh()

    profile_tab._rows["Fast skim"].invoke()
    profile_tab._rows["Careful read"].invoke()

    assert profile_tab.selected_name == "Careful read"
    assert profile_tab._rows["Careful read"].cget("fg_color") == EMBER_GLOW
    assert profile_tab._rows["Fast skim"].cget("fg_color") == "transparent"
    for button in profile_tab._action_buttons:
        assert button.cget("state") == "normal"


def test_select_always_selects_and_deselect_clears_whatever_is_selected(app, profile_tab):
    app._save_profile("Fast skim")
    profile_tab.refresh()

    profile_tab.deselect()  # nothing selected yet: harmless
    assert profile_tab.selected_name is None

    profile_tab.select("Fast skim")
    profile_tab.select("Fast skim")  # selecting the selected one does not toggle it
    assert profile_tab.selected_name == "Fast skim"

    profile_tab.deselect()
    assert profile_tab.selected_name is None
    for button in profile_tab._action_buttons:
        assert button.cget("state") == "disabled"


def test_after_unselecting_the_action_buttons_open_nothing(app, profile_tab):
    app._save_profile("Fast skim")
    profile_tab.refresh()
    row = profile_tab._rows["Fast skim"]
    row.invoke()
    row.invoke()

    for button in profile_tab._action_buttons:
        button.invoke()  # disabled, so these do nothing

    assert profile_tab._popup is None
    assert [p.name for p in app.settings_store.profiles] == ["Fast skim"]


def test_selecting_a_row_highlights_it_and_switches_the_buttons_on(app, profile_tab):
    from gui.theme import EMBER_GLOW

    app._save_profile("Fast skim")
    app._save_profile("Careful read")
    profile_tab.refresh()

    profile_tab.select("Careful read")
    assert profile_tab.selected_name == "Careful read"
    assert profile_tab._rows["Careful read"].cget("fg_color") == EMBER_GLOW
    assert profile_tab._rows["Fast skim"].cget("fg_color") == "transparent"
    for button in profile_tab._action_buttons:
        assert button.cget("state") == "normal"

    # Clicking a row does the same, and the highlight moves with it.
    profile_tab._rows["Fast skim"].invoke()
    assert profile_tab.selected_name == "Fast skim"
    assert profile_tab._rows["Fast skim"].cget("fg_color") == EMBER_GLOW
    assert profile_tab._rows["Careful read"].cget("fg_color") == "transparent"


def test_the_selection_survives_a_refresh_and_goes_when_its_profile_does(app, profile_tab):
    app._save_profile("Fast skim")
    profile_tab.refresh()
    profile_tab.select("Fast skim")
    profile_tab.refresh()
    assert profile_tab.selected_name == "Fast skim"

    app._delete_profile("Fast skim")
    profile_tab.refresh()
    assert profile_tab.selected_name is None
    for button in profile_tab._action_buttons:
        assert button.cget("state") == "disabled"


def test_save_current_settings_as_applies_pending_changes_then_saves_them(app, settings, profile_tab):
    store = app.settings_store
    settings._set_entry_value(settings.guide_mark_thickness_entry, 4)
    settings.warm_up_switch.select()

    profile_tab.save_button.invoke()
    popup = _popup_of(profile_tab)
    assert popup.title() == "Save Profile"
    _type_name(popup, "  My   skim ")
    _finish_popup(app, popup, _find_button(popup, "Save").invoke)

    # The name is tidied up, and the profile holds what was typed in Settings
    # even though Apply was never pressed.
    profile = store.get_profile("My skim")
    assert profile is not None
    assert profile.values["guide_mark_thickness_px"] == 4
    assert profile.values["warm_up_enabled"] is True
    # Which is because Apply ran first, so the app has those changes too.
    assert store.guide_mark_thickness_px == 4
    assert store.warm_up_enabled is True
    assert list(profile_tab._rows) == ["My skim"]
    assert profile_tab.selected_name == "My skim"
    assert settings.error_label.cget("text") == ""


def test_the_name_dialog_stays_open_on_a_bad_name_and_cancel_saves_nothing(app, settings, profile_tab, monkeypatch):
    long_name = "W" * 30
    app._save_profile(long_name)
    profile_tab.refresh()
    regrabs = []
    monkeypatch.setattr(settings, "_regrab_if_still_open", lambda: regrabs.append("regrab"))

    profile_tab.save_button.invoke()
    popup = _popup_of(profile_tab)
    _type_name(popup, long_name.lower())  # the same name, apart from its capitals
    popup._handle_submit()
    assert popup.winfo_exists()
    assert "already a profile" in popup.error_label.cget("text")
    _assert_popup_not_clipped(popup)

    _type_name(popup, "")
    popup._handle_submit()
    assert popup.winfo_exists()
    assert popup.error_label.cget("text") == "Give the profile a name."

    _finish_popup(app, popup, _find_button(popup, "Cancel").invoke)
    assert not popup.winfo_exists()
    assert profile_tab._popup is None
    assert [p.name for p in app.settings_store.profiles] == [long_name]
    # Closing it handed the input grab back to Settings.
    assert regrabs == ["regrab"]


def test_pressing_save_twice_opens_one_name_dialog(app, profile_tab):
    from gui.components.profile_name_dialog import ProfileNameDialog

    profile_tab.save_button.invoke()
    popup = _popup_of(profile_tab)
    profile_tab.save_button.invoke()
    assert profile_tab._popup is popup
    toplevel = profile_tab.winfo_toplevel()
    assert sum(isinstance(w, ProfileNameDialog) for w in toplevel.winfo_children()) == 1
    _finish_popup(app, popup, _find_button(popup, "Cancel").invoke)


def test_rename_starts_from_the_current_name_and_changes_only_the_name(app, profile_tab):
    store = app.settings_store
    store.add_profile("Fast skim", {"skip_word_count": 33, "warm_up_enabled": True})
    store.add_profile("Careful read", {})
    profile_tab.refresh()
    profile_tab.select("Fast skim")

    profile_tab.rename_button.invoke()
    popup = _popup_of(profile_tab)
    assert popup.title() == "Rename Profile"
    assert popup.name_entry.get() == "Fast skim"

    _type_name(popup, "careful READ")  # another profile's name
    popup._handle_submit()
    assert popup.winfo_exists()
    assert "already a profile" in popup.error_label.cget("text")

    _type_name(popup, "Quick skim")
    _finish_popup(app, popup, _find_button(popup, "Rename").invoke)

    assert [p.name for p in store.profiles] == ["Quick skim", "Careful read"]
    assert store.get_profile("Quick skim").values == {"skip_word_count": 33, "warm_up_enabled": True}
    assert profile_tab.selected_name == "Quick skim"
    assert list(profile_tab._rows) == ["Quick skim", "Careful read"]


def test_a_profile_can_be_renamed_to_change_only_its_capitals(app, profile_tab):
    app._save_profile("Fast skim")
    profile_tab.refresh()
    profile_tab.select("Fast skim")

    profile_tab.rename_button.invoke()
    popup = _popup_of(profile_tab)
    _type_name(popup, "fast SKIM")
    _finish_popup(app, popup, _find_button(popup, "Rename").invoke)

    assert [p.name for p in app.settings_store.profiles] == ["fast SKIM"]
    assert profile_tab.selected_name == "fast SKIM"


def test_renaming_a_profile_to_the_name_it_already_has_changes_nothing(app, settings, profile_tab):
    app._save_profile("Fast skim")
    profile_tab.refresh()
    profile_tab._rename("Fast skim", "Fast skim")
    assert [p.name for p in app.settings_store.profiles] == ["Fast skim"]
    assert settings.error_label.cget("text") == ""


def test_delete_asks_first_and_cancel_keeps_the_profile(app, profile_tab):
    name = "W" * 30
    app._save_profile(name)
    profile_tab.refresh()
    profile_tab.select(name)

    profile_tab.delete_button.invoke()
    popup = _popup_of(profile_tab)
    assert popup.title() == "Delete Profile"
    assert any(name in text for text in _labels_by_text(popup))
    assert popup.confirm_button.cget("fg_color") == "#A33636"
    _assert_popup_not_clipped(popup)

    _finish_popup(app, popup, _find_button(popup, "Cancel").invoke)
    assert app.settings_store.get_profile(name) is not None
    assert profile_tab.selected_name == name
    assert profile_tab._popup is None


def test_confirming_delete_removes_the_profile_and_clears_the_selection(app, profile_tab):
    app._save_profile("Fast skim")
    app._save_profile("Careful read")
    profile_tab.refresh()
    profile_tab.select("Fast skim")

    profile_tab.delete_button.invoke()
    popup = _popup_of(profile_tab)
    _finish_popup(app, popup, popup.confirm_button.invoke)

    assert [p.name for p in app.settings_store.profiles] == ["Careful read"]
    assert list(profile_tab._rows) == ["Careful read"]
    assert profile_tab.selected_name is None
    for button in profile_tab._action_buttons:
        assert button.cget("state") == "disabled"


def test_update_asks_first_and_cancel_leaves_the_profile_as_it_was(app, settings, profile_tab):
    name = "W" * 30
    app._save_profile(name)
    profile_tab.refresh()
    profile_tab.select(name)
    settings.warm_up_switch.select()

    profile_tab.update_button.invoke()
    popup = _popup_of(profile_tab)
    assert popup.title() == "Update Profile"
    assert any(name in text for text in _labels_by_text(popup))
    _assert_popup_not_clipped(popup)
    _finish_popup(app, popup, _find_button(popup, "Cancel").invoke)

    assert app.settings_store.get_profile(name).values["warm_up_enabled"] is False


def test_confirming_update_replaces_the_profile_with_the_settings_in_the_window(app, settings, profile_tab):
    store = app.settings_store
    app._save_profile("Mine")
    profile_tab.refresh()
    profile_tab.select("Mine")
    assert store.get_profile("Mine").values["warm_up_enabled"] is False

    settings.warm_up_switch.select()  # not applied yet
    profile_tab.update_button.invoke()
    popup = _popup_of(profile_tab)
    _finish_popup(app, popup, popup.confirm_button.invoke)

    assert store.get_profile("Mine").values["warm_up_enabled"] is True
    assert [p.name for p in store.profiles] == ["Mine"]
    assert profile_tab.selected_name == "Mine"


def test_applying_a_profile_applies_pending_changes_first_then_the_profile_and_closes_settings(app, settings, profiles_sandbox):
    store = app.settings_store
    store.add_profile("Careful", {"skip_word_count": 9, "warm_up_enabled": True})
    wpm_before = store.default_wpm

    # Its own window, since applying closes it.
    app._open_settings_window()
    window = app._settings_window
    try:
        _settle(window)
        window.default_wpm_slider.set(333)       # a setting this profile doesn't hold
        window.skip_word_count_slider.set(40)    # one the profile sets too
        chosen_wpm = int(window.default_wpm_slider.get())
        assert chosen_wpm != wpm_before

        window.profiles_tab.select("Careful")
        _cancel_pending_afters(window)
        window.profiles_tab.apply_button.invoke()
        _settle(app, 150)

        assert not window.winfo_exists()
        assert store.default_wpm == chosen_wpm   # applied first, as if Apply had been pressed
        assert store.skip_word_count == 9        # and the profile wins for what it holds
        assert store.warm_up_enabled is True
        assert app.canvas._skip_word_count == 9
        assert app.canvas._warm_up_enabled is True
    finally:
        if window.winfo_exists():
            _close(app, window)
        app._settings_window = settings
        store.set_defaults(
            wpm_before, store.default_font_color, store.default_highlight_color,
            store.default_background_color, store.default_font_size,
        )


def test_switching_profiles_moves_the_defaults_tab_sliders_and_switches_when_settings_is_reopened(app, settings, profiles_sandbox):
    """The case that was reported: after applying a profile, the Speed and Word
    size sliders (and the +/- step, scrubber and paragraph switches) on the
    Defaults tab have to show the profile's values the next time Settings opens."""
    store = app.settings_store
    wpm_before, size_before = store.default_wpm, store.default_font_size
    store.add_profile("Everything", dict(_PROFILE_VALUES))

    app._open_settings_window()
    first = app._settings_window
    second = None
    try:
        _settle(first)
        assert int(first.default_wpm_slider.get()) == wpm_before
        assert int(first.default_font_size_slider.get()) == size_before

        first.profiles_tab.select("Everything")
        _cancel_pending_afters(first)
        first.profiles_tab.apply_button.invoke()
        _settle(app, 150)
        assert not first.winfo_exists()

        app._open_settings_window()
        second = app._settings_window
        _settle(second)
        assert int(second.default_wpm_slider.get()) == 450
        assert second.default_wpm_label.cget("text") == "450 WPM"
        assert int(second.default_font_size_slider.get()) == 48
        assert second.default_font_size == 48
        assert second.default_font_size_label.cget("text") == "48 px"
        assert second.font_size_step_entry.get() == "4"
        assert bool(second.split_long_paragraphs_switch.get()) is True
        assert bool(second.scrub_pause_switch.get()) is False
    finally:
        for window in (first, second):
            if window is not None and window.winfo_exists():
                _close(app, window)
        app._settings_window = settings


def test_a_bad_value_in_settings_stops_save_update_and_apply_and_is_reported(app, settings, profile_tab):
    store = app.settings_store
    store.add_profile("Fast skim", {"skip_word_count": 9})
    profile_tab.refresh()
    profile_tab.select("Fast skim")
    skip_before = store.skip_word_count

    settings._set_entry_value(settings.guide_mark_thickness_entry, "abc")
    for button in (profile_tab.save_button, profile_tab.update_button, profile_tab.apply_button):
        settings._show_message("")
        button.invoke()
        assert profile_tab._popup is None
        assert "must be a whole number" in settings.error_label.cget("text")

    assert settings.winfo_exists()            # applying did not close it
    assert store.skip_word_count == skip_before
    assert [p.name for p in store.profiles] == ["Fast skim"]


def test_a_profile_that_has_gone_missing_is_reported_and_the_list_is_rebuilt(app, settings, profile_tab):
    app._save_profile("Mine")
    profile_tab.refresh()
    profile_tab.select("Mine")
    app.settings_store.delete_profile("Mine")  # gone behind the tab's back

    profile_tab.apply_button.invoke()

    assert settings.error_label.cget("text") == 'There is no profile called "Mine".'
    assert profile_tab.selected_name is None
    assert list(profile_tab._rows) == []
    assert settings.winfo_exists()


def test_profile_buttons_do_nothing_while_nothing_is_selected(app, settings, profile_tab):
    app._save_profile("Fast skim")
    profile_tab.refresh()
    before = app._current_profile_settings()

    for handler in (
        profile_tab._handle_apply_clicked, profile_tab._handle_update_clicked,
        profile_tab._handle_rename_clicked, profile_tab._handle_delete_clicked,
    ):
        handler()

    assert profile_tab._popup is None
    assert settings.winfo_exists()
    assert app._current_profile_settings() == before


def test_the_windows_apply_button_is_hidden_on_the_profiles_tab_only(app, settings):
    apply_button = settings.apply_button
    close_button = _find_button(settings, "Close")
    button_row = apply_button.master
    row_height = button_row.winfo_reqheight()

    try:
        assert settings.tabview.get() == "Defaults"
        assert apply_button.winfo_manager() == "pack"

        for name in settings.tabview._name_list:
            _click_tab(settings, name)
            assert settings.tabview.get() == name
            expected = "" if name == "Profiles" else "pack"
            assert apply_button.winfo_manager() == expected, name
            # Close stays, and the row doesn't change size as Apply comes and goes.
            assert close_button.winfo_manager() == "pack", name
            assert button_row.winfo_reqheight() == row_height, name
    finally:
        _click_tab(settings, "Defaults")

    assert apply_button.winfo_manager() == "pack"


def test_apply_comes_back_on_the_right_after_visiting_the_profiles_tab(settings):
    apply_button = settings.apply_button
    close_button = _find_button(settings, "Close")
    try:
        _click_tab(settings, "Profiles")
        assert apply_button.winfo_manager() == ""
        _click_tab(settings, "Stats")
        assert apply_button.winfo_manager() == "pack"
        assert apply_button.pack_info()["side"] == "right"
        assert close_button.pack_info()["side"] == "left"
    finally:
        _click_tab(settings, "Defaults")


def test_the_profile_buttons_still_apply_pending_changes_with_the_windows_apply_hidden(app, settings, profile_tab):
    """On this tab the window's own Apply is gone, so Save has to be enough: it
    applies what was typed in the other tabs first and then saves the profile."""
    store = app.settings_store
    assert settings.apply_button.winfo_manager() == ""
    settings._set_entry_value(settings.guide_mark_thickness_entry, 3)

    profile_tab.save_button.invoke()
    popup = _popup_of(profile_tab)
    _type_name(popup, "No apply button")
    _finish_popup(app, popup, _find_button(popup, "Save").invoke)

    assert store.guide_mark_thickness_px == 3
    assert store.get_profile("No apply button").values["guide_mark_thickness_px"] == 3


def test_the_profiles_tab_fits_the_smallest_settings_window(app, settings, profile_tab):
    """At the smallest size Settings can be made, the tab must not ask for so
    much room that the tab view grows over the error line and the Close and
    Apply buttons below it (a scrollable list asks for a lot of height unless
    told otherwise), and its text must wrap inside the tab instead of running
    off the side. Only the window's own children are measured against each
    other, since widgets nested inside frames report no size until the window
    is really on screen.

    The window is made small first and the Profiles tab shown after, which is
    what happens when someone opens a small Settings window and clicks the tab.
    The other order does not show the problem: a tab that is already showing
    when the window shrinks never lays out over what is below it."""
    app._save_profile("Fast skim")
    app._save_profile("Careful read")
    profile_tab.refresh()
    original_geometry = settings.geometry()
    try:
        _click_tab(settings, "Defaults")
        settings.geometry("420x420")
        _settle(settings, 250)
        _click_tab(settings, "Profiles")
        _settle(settings, 250)

        tabview_bottom = settings.tabview.winfo_y() + settings.tabview.winfo_height()
        assert tabview_bottom <= settings.error_label.winfo_y()
        assert profile_tab.winfo_reqheight() <= settings.tabview.tab("Profiles").winfo_height()

        import customtkinter as ctk
        for label in (w for w in _all_widgets(profile_tab) if isinstance(w, ctk.CTkLabel)):
            assert label.winfo_reqwidth() <= profile_tab.winfo_width()
    finally:
        settings.geometry(original_geometry)
        _settle(settings, 150)


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