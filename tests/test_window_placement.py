"""Tests for remembering the main window: the rules in core/window_placement.py,
the settings that hold it (core/settings_store.py) and the app's side of it
(gui/app.py).

What was agreed: the app remembers the window's size, its position and whether
it was maximized, and opens the same way next time. On top of that: a position
whose screen has gone (an unplugged monitor) is ignored, so the window never
opens where it can't be seen. The size kept is always the normal one, so
un-maximizing goes back to it, and a window closed while minimized remembers
how it was before.

Most of the app's side is tested on a stand-in, the same way as in
test_settings_apply.py. A few tests at the end build the real app, and two of
those only run on Windows, because they check what Windows itself does with a
maximized window and with the list of monitors."""

import json
import sys
import time

import pytest

import core.storage as storage
import core.settings_store as settings_store
import core.transcript_store as transcript_store
from core.profiles import PROFILE_KEYS
from core.settings_store import AppSettings, SettingsStore, WINDOW_WIDTH_RANGE, WINDOW_HEIGHT_RANGE
from core.window_placement import (
    TITLE_BAR_DEPTH, TITLE_BAR_INSET, clamp, geometry_string, parse_geometry,
    position_is_usable, title_bar_points,
)

ON_WINDOWS = sys.platform.startswith("win")


# ---- the rules (core/window_placement.py) ----

def test_a_geometry_string_is_split_into_size_and_position():
    assert parse_geometry("1000x650+120+80") == (1000, 650, 120, 80)


def test_a_position_left_of_or_above_the_main_screen_is_negative():
    assert parse_geometry("1000x650+-1500+-20") == (1000, 650, -1500, -20)


def test_a_position_counted_from_the_right_or_bottom_keeps_only_the_size():
    assert parse_geometry("1000x650-10+20") == (1000, 650, None, None)
    assert parse_geometry("1000x650+10-20") == (1000, 650, None, None)


@pytest.mark.parametrize("text", ["", "abc", "1000x650", "1000x650+10", "x+1+2", "1000x650+1+2junk"])
def test_anything_else_is_not_a_geometry(text):
    assert parse_geometry(text) is None


def test_spaces_around_a_geometry_string_are_ignored():
    assert parse_geometry(" 800x600+5+6\n") == (800, 600, 5, 6)


def test_a_geometry_string_is_built_with_or_without_a_position():
    assert geometry_string(1000, 650, 120, 80) == "1000x650+120+80"
    assert geometry_string(1000, 650, -1500, -20) == "1000x650+-1500+-20"
    assert geometry_string(1000, 650, None, None) == "1000x650"
    assert geometry_string(1000, 650, 120, None) == "1000x650"


def test_building_and_splitting_give_the_same_numbers_back():
    for numbers in ((1000, 650, 120, 80), (500, 400, -1920, 0), (2000, 1400, 0, -300)):
        assert parse_geometry(geometry_string(*numbers)) == numbers


def test_the_title_bar_is_checked_near_both_ends_and_in_the_middle():
    row = 100 + TITLE_BAR_DEPTH
    assert title_bar_points(10, 100, 1000) == [
        (10 + TITLE_BAR_INSET, row), (10 + 500, row), (10 + 1000 - TITLE_BAR_INSET, row),
    ]


def test_a_narrow_window_keeps_its_points_inside_it():
    for px, _ in title_bar_points(0, 0, 20):
        assert 0 <= px <= 20


def test_a_position_is_usable_when_any_part_of_the_title_bar_is_on_a_screen():
    # A screen 1000 pixels wide. The window hangs off its left edge, but the
    # right end of its title bar is still on it.
    on_screen = lambda x, y: 0 <= x < 1000 and 0 <= y < 800
    assert position_is_usable(-900, 50, 1000, on_screen)
    assert position_is_usable(100, 50, 1000, on_screen)


def test_a_position_is_not_usable_when_none_of_the_title_bar_is_on_a_screen():
    on_screen = lambda x, y: 0 <= x < 1000 and 0 <= y < 800
    assert not position_is_usable(1200, 50, 600, on_screen)  # off to the right
    assert not position_is_usable(-2000, 50, 600, on_screen)  # a monitor that has gone
    assert not position_is_usable(100, 900, 600, on_screen)  # below the bottom
    assert not position_is_usable(-32000, -32000, 600, on_screen)  # where Windows parks a minimized window


def test_only_the_title_bar_row_is_asked_about():
    asked = []
    position_is_usable(10, 100, 1000, lambda x, y: asked.append(y) or False)
    assert set(asked) == {100 + TITLE_BAR_DEPTH}


def test_clamp_keeps_a_value_inside_its_range():
    assert clamp(50, (100, 200)) == 100
    assert clamp(150, (100, 200)) == 150
    assert clamp(250, (100, 200)) == 200


# ---- the settings (core/settings_store.py) ----

@pytest.fixture
def settings(tmp_path):
    return SettingsStore(str(tmp_path / "settings"))


def test_nothing_is_remembered_before_the_first_close(settings):
    assert settings.window_x is None
    assert settings.window_y is None
    assert settings.window_maximized is False
    assert (settings.window_width, settings.window_height) == (1000, 650)


def test_the_placement_is_saved_and_survives_a_restart(settings, tmp_path):
    settings.set_window_placement(1200, 800, -1500, 40, True)
    again = SettingsStore(str(tmp_path / "settings"))
    assert (again.window_width, again.window_height) == (1200, 800)
    assert (again.window_x, again.window_y) == (-1500, 40)
    assert again.window_maximized is True


def test_no_position_is_saved_as_none(settings, tmp_path):
    settings.set_window_placement(1200, 800, 5, 6, False)
    settings.set_window_placement(1200, 800, None, None, False)
    again = SettingsStore(str(tmp_path / "settings"))
    assert (again.window_x, again.window_y) == (None, None)


@pytest.mark.parametrize("odd", ["120", True, 1.5, [1], None])
def test_an_odd_position_in_the_file_reads_as_none(settings, odd):
    settings._settings.window_x = odd
    settings._settings.window_y = odd
    assert settings.window_x is None
    assert settings.window_y is None


@pytest.mark.parametrize("odd", ["true", 1, "yes", None])
def test_an_odd_maximized_value_in_the_file_reads_as_not_maximized(settings, odd):
    settings._settings.window_maximized = odd
    assert settings.window_maximized is False


def test_an_old_settings_file_without_them_keeps_its_size(tmp_path):
    folder = tmp_path / "settings"
    folder.mkdir()
    old = {key: value for key, value in vars(AppSettings()).items()
           if key not in ("window_x", "window_y", "window_maximized")}
    old["window_width"], old["window_height"] = 1300, 900
    (folder / "settings.json").write_text(json.dumps(old), encoding="utf-8")
    loaded = SettingsStore(str(folder))
    assert (loaded.window_width, loaded.window_height) == (1300, 900)
    assert (loaded.window_x, loaded.window_y, loaded.window_maximized) == (None, None, False)


def test_the_placement_is_not_part_of_a_reading_profile():
    for key in ("window_x", "window_y", "window_maximized"):
        assert key not in PROFILE_KEYS, key


# ---- the app's side, on a stand-in (gui/app.py) ----

class _Window:
    """Just enough of the app for its window placement methods: a settings
    store, a geometry() that reports what it is given, a state that a test can
    set, and after() and after_cancel() that only keep notes. The methods
    below run the app's own code on it, the same as _AppStandIn in
    test_settings_apply.py. gui.app is imported inside them, like there."""

    PLACEMENT_SETTLE_MS = 300

    def __init__(self, store, size="1000x650+20+30", state="normal", on_screen=None):
        self.settings_store = store
        self.size = size
        self.state_now = state
        self.on_screen = on_screen or (lambda x, y: True)
        self.geometry_calls = []
        self.after_calls = []
        self.cancelled = []
        self._window_size_in_settings = (store.window_width, store.window_height)

    def geometry(self, value=None):
        if value is None:
            return self.size
        self.geometry_calls.append(value)

    def after(self, milliseconds, callback):
        self.after_calls.append((milliseconds, callback))
        return f"after#{len(self.after_calls)}"

    def after_cancel(self, after_id):
        self.cancelled.append(after_id)

    def _window_state(self):
        return self.state_now

    def _screen_pixels(self, size):
        return size

    def _point_is_on_a_screen(self, x, y):
        return self.on_screen(x, y)

    def __getattr__(self, name):
        # Every other method is the app's own, run on this stand-in.
        from gui.app import RSVPApp
        method = getattr(RSVPApp, name)

        def run(*args, **kwargs):
            return method(self, *args, **kwargs)
        run.__name__ = name  # so a test can tell which method was queued
        return run


def _restored(settings, **window_options):
    window = _Window(settings, **window_options)
    window._restore_window_placement()
    return window


def test_the_window_opens_where_it_was(settings):
    settings.set_window_placement(1200, 800, 300, 200, False)
    window = _restored(settings)
    assert window.geometry_calls == ["1200x800+300+200"]
    assert window._normal_window_placement == (1200, 800, 300, 200)
    assert window._window_maximized is False
    assert window.after_calls == []


def test_the_first_launch_leaves_the_placing_to_the_system(settings):
    window = _restored(settings)
    assert window.geometry_calls == ["1000x650"]
    assert window._normal_window_placement == (1000, 650, None, None)


def test_a_position_off_every_screen_is_dropped_but_the_size_kept(settings):
    settings.set_window_placement(1200, 800, -5000, 200, False)
    window = _restored(settings, on_screen=lambda x, y: 0 <= x < 1920 and 0 <= y < 1080)
    assert window.geometry_calls == ["1200x800"]
    assert window._normal_window_placement == (1200, 800, None, None)


def test_the_screen_check_uses_the_width_in_screen_pixels(settings):
    settings.set_window_placement(1000, 650, -1100, 0, False)
    on_screen = lambda x, y: 0 <= x < 1920
    window = _Window(settings, on_screen=on_screen)
    # At 100% none of a 1000 wide window starting at -1100 is on screen. At
    # 200% it is 2000 pixels wide, so its right end is.
    window._screen_pixels = lambda size: size * 2
    window._restore_window_placement()
    assert window.geometry_calls == ["1000x650+-1100+0"]


def test_a_window_closed_maximized_is_maximized_again_once_events_run(settings):
    settings.set_window_placement(1200, 800, 300, 200, True)
    window = _restored(settings)
    # Sized and placed at its normal size first, so un-maximizing goes back
    # to it, and maximized from after(0), not straight away.
    assert window.geometry_calls == ["1200x800+300+200"]
    assert window._window_maximized is True
    assert len(window.after_calls) == 1
    milliseconds, callback = window.after_calls[0]
    assert milliseconds == 0
    assert callback.__name__ == "_maximize_window"


def test_a_normal_window_is_noted_with_its_size_and_position(settings):
    window = _restored(settings, size="1100x700+40+50")
    window._note_window_placement()
    assert window._normal_window_placement == (1100, 700, 40, 50)
    assert window._window_maximized is False


def test_a_maximized_window_keeps_its_normal_size_and_position(settings):
    settings.set_window_placement(1200, 800, 300, 200, False)
    window = _restored(settings, size="1920x1017+-8+-8", state="maximized")
    window._note_window_placement()
    assert window._normal_window_placement == (1200, 800, 300, 200)
    assert window._window_maximized is True


@pytest.mark.parametrize("state", ["minimized", "hidden"])
def test_a_minimized_or_hidden_window_changes_nothing(settings, state):
    settings.set_window_placement(1200, 800, 300, 200, True)
    window = _restored(settings, size="160x30+-32000+-32000", state=state)
    window._note_window_placement()
    assert window._normal_window_placement == (1200, 800, 300, 200)
    assert window._window_maximized is True


def test_un_maximizing_is_noted(settings):
    settings.set_window_placement(1200, 800, 300, 200, True)
    window = _restored(settings, size="1200x800+300+200")
    window._note_window_placement()
    assert window._window_maximized is False


def test_the_window_is_only_noted_once_it_has_stayed_still(settings):
    window = _restored(settings)
    event = type("Event", (), {"widget": window})()
    window._track_window_placement(event)
    window._track_window_placement(event)
    # Each change waits PLACEMENT_SETTLE_MS, and starts that wait again, so
    # the steps of a maximize in between are never noted.
    assert [ms for ms, _ in window.after_calls] == [300, 300]
    assert window.cancelled == ["after#1"]
    assert window._placement_note_after_id == "after#2"
    window.size = "900x600+70+80"
    window.after_calls[-1][1]()
    assert window._normal_window_placement == (900, 600, 70, 80)
    assert window._placement_note_after_id is None


def test_a_change_to_something_inside_the_window_is_ignored(settings):
    window = _restored(settings)
    event = type("Event", (), {"widget": object()})()
    window._track_window_placement(event)
    assert window.after_calls == []


def test_closing_saves_the_window_as_it_is_right_now(settings, tmp_path):
    # Never noted while open, which is what happens on Linux to a window that
    # is never moved, and still saved with its real position.
    window = _restored(settings, size="1100x700+40+50")
    window._save_window_placement()
    again = SettingsStore(str(tmp_path / "settings"))
    assert (again.window_width, again.window_height, again.window_x, again.window_y) == (1100, 700, 40, 50)
    assert again.window_maximized is False


def test_closing_maximized_saves_the_normal_size_and_that_it_was_maximized(settings, tmp_path):
    settings.set_window_placement(1200, 800, 300, 200, False)
    window = _restored(settings, size="1920x1017+-8+-8", state="maximized")
    window._save_window_placement()
    again = SettingsStore(str(tmp_path / "settings"))
    assert (again.window_width, again.window_height, again.window_x, again.window_y) == (1200, 800, 300, 200)
    assert again.window_maximized is True


def test_closing_cancels_a_note_still_waiting(settings):
    window = _restored(settings)
    window._track_window_placement(type("Event", (), {"widget": window})())
    window._save_window_placement()
    assert window.cancelled == ["after#1"]


def test_a_size_outside_the_layout_tabs_range_is_saved_inside_it(settings, tmp_path):
    window = _restored(settings, size="3000x200+0+0")
    window._save_window_placement()
    again = SettingsStore(str(tmp_path / "settings"))
    assert again.window_width == WINDOW_WIDTH_RANGE[1]
    assert again.window_height == WINDOW_HEIGHT_RANGE[0]


def test_a_size_set_on_the_layout_tab_while_maximized_is_the_one_saved(settings, tmp_path):
    settings.set_window_placement(1200, 800, 300, 200, True)
    window = _restored(settings, size="1920x1017+-8+-8", state="maximized")
    window._apply_window_size(1000, 700)
    window._save_window_placement()
    again = SettingsStore(str(tmp_path / "settings"))
    assert (again.window_width, again.window_height, again.window_x, again.window_y) == (1000, 700, 300, 200)
    assert again.window_maximized is True


class _States:
    """A stand-in for _window_state() and _maximize_window(): what Tk says the
    state is, whether Tk is on X11 and its -zoomed flag there, and a record of
    what it was asked to do."""

    def __init__(self, state="normal", x11=False, zoomed=0, fails=False):
        self.state_now, self.x11, self.zoomed, self.fails = state, x11, zoomed, fails
        self.asked = []
        self._maximize_after_id = "after#1"

    def state(self, value=None):
        import tkinter
        if value is None:
            return self.state_now
        if self.fails:
            raise tkinter.TclError("can't")
        self.asked.append(("state", value))

    def attributes(self, name, value=None):
        if value is None:
            return self.zoomed
        self.asked.append(("attributes", name, value))

    def _on_x11(self):
        return self.x11


@pytest.mark.parametrize("state, expected", [
    ("zoomed", "maximized"), ("iconic", "minimized"), ("withdrawn", "hidden"), ("normal", "normal"),
])
def test_tks_state_names_are_read(state, expected):
    from gui.app import RSVPApp
    assert RSVPApp._window_state(_States(state)) == expected


def test_on_linux_maximized_is_a_separate_flag():
    from gui.app import RSVPApp
    assert RSVPApp._window_state(_States("normal", x11=True, zoomed=1)) == "maximized"
    assert RSVPApp._window_state(_States("normal", x11=True, zoomed=0)) == "normal"


def test_maximizing_asks_for_zoomed_or_on_linux_sets_the_flag():
    from gui.app import RSVPApp
    window = _States()
    RSVPApp._maximize_window(window)
    assert window.asked == [("state", "zoomed")]
    assert window._maximize_after_id is None
    window = _States(x11=True)
    RSVPApp._maximize_window(window)
    assert window.asked == [("attributes", "-zoomed", True)]


def test_a_window_that_cannot_be_maximized_just_stays_as_it_is():
    from gui.app import RSVPApp
    RSVPApp._maximize_window(_States(fails=True))  # no error


def test_a_size_is_turned_into_screen_pixels_with_the_display_scaling(monkeypatch):
    import customtkinter as ctk
    from gui.app import RSVPApp
    monkeypatch.setattr(ctk.ScalingTracker, "get_window_scaling", lambda window: 2.0)
    assert RSVPApp._screen_pixels(object(), 500) == 1000
    monkeypatch.setattr(ctk.ScalingTracker, "get_window_scaling", lambda window: 1.25)
    assert RSVPApp._screen_pixels(object(), 1001) == 1251


def test_off_windows_only_the_main_screen_counts(monkeypatch):
    from gui.app import RSVPApp
    monkeypatch.setattr(sys, "platform", "linux")
    screen = type("Screen", (), {"winfo_screenwidth": lambda self: 1920, "winfo_screenheight": lambda self: 1080})()
    assert RSVPApp._point_is_on_a_screen(screen, 0, 0)
    assert RSVPApp._point_is_on_a_screen(screen, 1919, 1079)
    assert not RSVPApp._point_is_on_a_screen(screen, 1920, 10)
    assert not RSVPApp._point_is_on_a_screen(screen, -1, 10)
    assert not RSVPApp._point_is_on_a_screen(screen, 10, 1080)


@pytest.mark.skipif(not ON_WINDOWS, reason="asks Windows itself about the monitors")
def test_windows_knows_a_point_on_the_main_screen_from_one_off_every_screen():
    import ctypes
    from gui.app import RSVPApp
    nobody = type("Nobody", (), {})()  # the Windows answer needs nothing from the window
    width = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN, the main screen
    height = ctypes.windll.user32.GetSystemMetrics(1)
    assert RSVPApp._point_is_on_a_screen(nobody, width // 2, height // 2)
    assert not RSVPApp._point_is_on_a_screen(nobody, -100_000, -100_000)


# ---- the real app ----

_REDIRECT_TARGETS = (
    (storage, "DEFAULT_DATA_DIR"),
    (settings_store, "DEFAULT_DATA_DIR"),
    (settings_store, "SETTINGS_DIR"),
    (transcript_store, "DEFAULT_DATA_DIR"),
)

# Small enough to fit on a screen at 200%, and placed near the top left of the
# main screen, so it is on screen on any machine.
SAVED = (700, 500, 120, 90)


def _all_widgets(widget):
    found = [widget]
    for child in widget.winfo_children():
        found.extend(_all_widgets(child))
    return found


def _settle(widget, milliseconds=800):
    end = time.monotonic() + milliseconds / 1000
    while time.monotonic() < end:
        widget.update()
        time.sleep(0.005)


def _cancel_pending_afters(window):
    """Cancel the timers a settled window still has queued, each through the
    widget that scheduled it. Same as the helper of the same name in
    test_bold_starts_app.py."""
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


@pytest.fixture
def launch(tmp_path, monkeypatch, fresh_widget_image_caches):
    """Builds the real app after saving a window placement for it, and closes
    it the way the window's close button does. Gives back the app and a
    function that reads the saved settings.json. Skips if Tk has no display."""
    import tkinter
    import gui.app as app_module

    for mod, name in _REDIRECT_TARGETS:
        monkeypatch.setattr(mod, name, tmp_path)
    # Closing the app normally takes the app's fonts back off the system,
    # which is for when the app quits, not for the middle of a test run.
    monkeypatch.setattr(app_module, "unregister_fonts", lambda: None)
    built = []

    def build(width, height, x, y, maximized):
        fresh_widget_image_caches()
        SettingsStore().set_window_placement(width, height, x, y, maximized)
        try:
            application = app_module.RSVPApp()
        except tkinter.TclError as exc:
            pytest.skip(f"Tk can't start a display here: {exc}")
        built.append(application)
        _settle(application)
        return application

    def close(application):
        _settle(application, 400)
        _cancel_pending_afters(application)
        application._handle_close()
        built.remove(application)
        saved = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
        return tuple(saved[key] for key in ("window_width", "window_height", "window_x", "window_y", "window_maximized"))

    yield build, close
    for application in built:
        try:
            _cancel_pending_afters(application)
            application.destroy()
        except tkinter.TclError:
            pass  # a test destroyed it already
    fresh_widget_image_caches()


def test_the_app_opens_where_it_was_closed_and_saves_it_again(launch):
    build, close = launch
    application = build(*SAVED, False)
    assert parse_geometry(application.geometry()) == SAVED
    assert close(application) == (*SAVED, False)


@pytest.mark.skipif(not ON_WINDOWS, reason="what Windows does with a maximized window")
def test_on_windows_the_app_opens_maximized_and_keeps_its_normal_size(launch):
    build, close = launch
    application = build(*SAVED, True)
    assert application.state() == "zoomed"
    assert close(application) == (*SAVED, True)


def test_the_window_is_noted_as_it_moves_and_not_while_it_is_minimized(launch):
    build, close = launch
    application = build(*SAVED, False)
    application.geometry("650x450+160+110")
    _settle(application)  # longer than PLACEMENT_SETTLE_MS, so the move is noted
    assert application._normal_window_placement == (650, 450, 160, 110)
    # Minimizing for real needs a window manager, which a test machine may not
    # have, so the window says it is minimized instead. Windows really does
    # move a minimized window, far off to the top left.
    application._window_state = lambda: "minimized"
    application.geometry("650x450+400+300")
    assert close(application) == (650, 450, 160, 110, False)


def test_destroying_the_app_drops_a_note_still_waiting(launch):
    build, _ = launch
    application = build(*SAVED, False)
    application.geometry("650x450+160+110")
    application.update()  # the move arrives and its note starts waiting
    assert application._placement_note_after_id is not None
    _cancel_pending_afters(application)  # CustomTkinter's own timers, which it leaves behind
    application.destroy()
    assert application._placement_note_after_id is None
