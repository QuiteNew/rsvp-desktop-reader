"""Shared pytest fixtures for the whole suite.

The one thing worth centralizing: making sure no test can ever read or write
the real ~/.rsvp_reader. Tests that build a store with an explicit tmp_path are
already isolated, but a store constructed with no arguments falls back to the
on-disk default location. This points those fallbacks at a throwaway session
temp directory, as a safety net, so a no-argument SettingsStore() or
TranscriptStore() in any test (today or later) stays off your real data.

It deliberately leaves core.storage.DEFAULT_DATA_DIR itself untouched, so
test_storage.py's check that the default sits under the home directory still
sees the real value.

It also holds fresh_widget_image_caches, which a test module that builds the
toolbar (so, a Canvas or the whole app) asks for when it makes a Tk root of its
own, and wait_until_shown, for a test that needs a window to actually be on
screen. See each fixture for why.
"""
import time

import pytest

import core.settings_store as settings_store
import core.transcript_store as transcript_store


# The module-level names the no-argument store constructors actually read:
#   SettingsStore()   -> settings_store.SETTINGS_DIR
#   AppSettings()     -> settings_store.DEFAULT_DATA_DIR  (data_directory default)
#   TranscriptStore() -> transcript_store.DEFAULT_DATA_DIR
# core.storage.DEFAULT_DATA_DIR is the original these were copied from; it is
# left alone on purpose, so test_storage.py still sees the real home path.
_FALLBACK_LOCATION_NAMES = (
    (settings_store, "DEFAULT_DATA_DIR"),
    (settings_store, "SETTINGS_DIR"),
    (transcript_store, "DEFAULT_DATA_DIR"),
)


@pytest.fixture(scope="session", autouse=True)
def _never_touch_real_user_data(tmp_path_factory):
    """Redirect the on-disk default data location to a session temp folder for
    every test, then restore it when the session ends."""
    safe_dir = tmp_path_factory.mktemp("rsvp_no_real_data")
    originals = [(mod, name, getattr(mod, name)) for mod, name in _FALLBACK_LOCATION_NAMES]
    for mod, name in _FALLBACK_LOCATION_NAMES:
        setattr(mod, name, safe_dir)
    try:
        yield
    finally:
        for mod, name, value in originals:
            setattr(mod, name, value)


def _forget_cached_widget_images() -> None:
    """Empty the module-level caches that hold a picture made for one Tk root."""
    from gui import theme
    from gui.components import canvas_toolbar

    canvas_toolbar._BOOKMARK_IMAGE = None
    theme._icon_photo_image = None


@pytest.fixture(scope="module")
def fresh_widget_image_caches():
    """For a test module that makes its own Tk root and builds the toolbar.

    The toolbar's bookmark picture (and, off Windows, the window icon) is made
    once and kept in a module-level variable, and a picture belongs to the Tk
    root that was running when it was made. A second root in the same process
    then fails with "image pyimageN doesn't exist" the moment it builds a toolbar,
    and a root that is gone leaves its picture behind for the next module to trip
    over. test_gui_smoke.py avoids it by sharing one root for the whole module.
    A module that cannot share that root empties the caches here, before its own
    root is made and again after it is destroyed. Only the modules that ask for
    it are affected.

    What the fixture hands back is the function that empties them, for a module
    that makes more than one root in turn (a fixture with several parameters):
    call it before each new root is made and after each one is destroyed."""
    _forget_cached_widget_images()
    yield _forget_cached_widget_images
    _forget_cached_widget_images()


@pytest.fixture
def wait_until_shown():
    """For a test that needs a window on screen. Hands back a function that
    runs the event loop until the window is shown and has had time to lay
    itself out, and fails with the window's state if that doesn't happen.

    A fixed wait isn't enough on Windows. A new CTkToplevel hides itself to
    colour its title bar and comes back on a timer, and Settings does that
    twice. How long that takes changes from run to run: the same Settings
    window sometimes wasn't back after 300 ms and sometimes was.

    The loop runs in steps of 300 ms and stops at the end of a step where the
    window is shown. Stopping as soon as it shows would be too early, because
    the second round of hiding can still be coming."""
    def wait(window, timeout=5.0, step=0.3):
        deadline = time.monotonic() + timeout
        while True:
            end = time.monotonic() + step
            while time.monotonic() < end:
                window.update()
                time.sleep(0.005)
            if window.winfo_ismapped():
                return
            if time.monotonic() > deadline:
                owner = window.master.winfo_toplevel()
                raise AssertionError(
                    f"{type(window).__name__} did not appear within {timeout} s: "
                    f"its state is {window.state()!r}, its owner's is {owner.state()!r} "
                    f"and the owner is {'shown' if owner.winfo_ismapped() else 'not shown'}"
                )

    return wait