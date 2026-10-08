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
"""
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