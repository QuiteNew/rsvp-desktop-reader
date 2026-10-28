"""Tests that the test suite itself never reads the app's real settings
(see tests/conftest.py).

gui/theme.py picks the colour theme and the fonts from the saved settings the
moment it is imported, and test files import it while pytest is still loading
them. If that read reached the real ~/.rsvp_reader, the suite would run in
whatever theme and font the app on that machine happens to be set to, and
tests would pass on one machine and fail on another. These check that it runs
on the defaults instead, whatever is saved on the machine."""

from pathlib import Path

# Imported here at the top, while pytest is loading this file, the same way the
# other test files import it. That is when the theme reads the settings, so
# importing it later, inside a test, would miss the problem.
from gui.theme import CTK_APPEARANCE_MODE, DYSLEXIA_FONT_ACTIVE


def test_the_settings_location_is_not_the_real_one():
    import core.settings_store as settings_store
    import core.transcript_store as transcript_store

    real = Path.home() / ".rsvp_reader"
    for location in (settings_store.SETTINGS_DIR, settings_store.DEFAULT_DATA_DIR, transcript_store.DEFAULT_DATA_DIR):
        assert Path(location) != real


def test_the_theme_was_picked_from_the_defaults():
    """The default settings are the Light theme and the standard fonts. A test
    machine with Dark or the OpenDyslexic font switched on in the app must not
    change that for the tests."""
    assert CTK_APPEARANCE_MODE == "Light"
    assert DYSLEXIA_FONT_ACTIVE is False