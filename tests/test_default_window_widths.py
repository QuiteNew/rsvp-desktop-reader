"""The detached transcript window, and the window a detached selection opens in,
are wide enough at the size they open at for everything above the reader.

Both used to open 500 pixels wide while the row above the reader (the scrubber on
the left, the toolbar on the right) asked for 555 to 600. The pack manager
quietly gave the missing space to the left-hand widgets first, so the restart
button, and the bookmarks button in the detached window, were not shown at all
and the pause button was squeezed to a sliver. A person had to drag the window
wider to find them.

These tests open each window and change nothing about its size. They then check
that every control is on screen, inside the window, and has the width it asked
for, and that the scrubber and the toolbar do not run into each other. They run
at a few display scalings, because CustomTkinter scales the window and its
widgets together and the fit has to hold at every one.
"""
import pytest

from tk_helpers import click_button, settle

WORDS = " ".join(f"w{number}" for number in range(200))

SCALINGS = [1.0, 1.25, 1.5]


def _controls(window):
    """The toolbar's widgets that show above the reader, by name. The bookmarks
    button is only in the detached transcript window."""
    names = ["skip_back_button", "pause_button", "skip_forward_button", "restart_button",
             "time_readout", "percent_readout"]
    if getattr(window.toolbar, "bookmark_button", None) is not None:
        names.append("bookmark_button")
    return {name: getattr(window.toolbar, name) for name in names}


def _assert_everything_fits(window):
    settle(window, 300)
    window_left = window.winfo_rootx()
    window_right = window_left + window.winfo_width()
    for name, widget in _controls(window).items():
        assert widget.winfo_ismapped(), f"{name} is not shown"
        assert widget.winfo_width() >= widget.winfo_reqwidth(), f"{name} is squeezed"
        assert widget.winfo_rootx() >= window_left, f"{name} sticks out on the left"
        assert widget.winfo_rootx() + widget.winfo_width() <= window_right, f"{name} sticks out on the right"
    scrubber = window.scrub_bar
    assert scrubber.winfo_width() >= scrubber.winfo_reqwidth(), "the scrubber is squeezed"
    toolbar_left = min(widget.winfo_rootx() for widget in _controls(window).values())
    assert scrubber.winfo_rootx() + scrubber.winfo_width() <= toolbar_left, "the scrubber and the toolbar overlap"


@pytest.mark.parametrize("factor", SCALINGS)
def test_the_detached_transcript_window_shows_every_button_when_it_opens(tmp_path, open_real_app, scaling, factor):
    scaling(factor)
    with open_real_app(tmp_path) as app:
        transcript = app.store.add_transcript("Book", app.store.current_space, wpm=300)
        app.store.set_transcript_text(transcript.id, WORDS)
        app.store.set_transcript_paused(transcript.id, True)
        app._refresh_transcript_list()
        settle(app, 200)
        app._handle_open_transcript(transcript)
        settle(app, 300)

        click_button(app.canvas.toolbar.detach_button)
        settle(app, 700)

        window = app.canvas._detached_window
        assert window is not None
        _assert_everything_fits(window)


@pytest.mark.parametrize("factor", SCALINGS)
def test_the_selection_window_shows_every_button_once_it_is_reading(tmp_path, open_real_app, scaling, factor):
    scaling(factor)
    with open_real_app(tmp_path) as app:
        transcript = app.store.add_transcript("Book", app.store.current_space, wpm=300)
        app.store.set_transcript_text(transcript.id, WORDS)
        app.store.set_transcript_stopped(transcript.id, True)
        app._refresh_transcript_list()
        settle(app, 200)
        app._handle_open_transcript(transcript)
        settle(app, 300)

        app.canvas.open_selection_preview(" ".join(WORDS.split()[:80]))
        settle(app, 500)
        window = app.canvas._selection_previews[-1][0]
        click_button(window.input_view.start_button)

        _assert_everything_fits(window)
