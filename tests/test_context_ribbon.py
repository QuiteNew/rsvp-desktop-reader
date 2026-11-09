"""The dim ribbon of neighbouring words under the reader ("peripheral context"),
in a real app with the setting on: the word before on its left, the current
word in the middle and the two after on its right.

Earlier tests only ever saw the ribbon on the first word, so the word before,
the end of the transcript and a pan while the ribbon is showing were never
drawn. These move through a transcript with the footer's real skip buttons and
pan with the reader's real scrollbar and the C key, then look at where the
three parts of the ribbon are on screen.
"""
import pytest

from core.settings_store import SettingsStore
from tk_helpers import click_button, settle

WORD_LIST = [f"w{number}" for number in range(20)]
# One word far wider than the reader, so the reader can be panned.
LONG_WORD = "Pneumonoultramicroscopicsilicovolcanoconiosis" * 3
GAP_SLACK = 2


def _open(tmp_path, open_real_app):
    """A real app that starts with the ribbon turned on in its settings."""
    return open_real_app(tmp_path, before_start=lambda: SettingsStore().set_peripheral_context_enabled(True))


def _load(app, words):
    transcript = app.store.add_transcript("Book", app.store.current_space, wpm=60)
    app.store.set_transcript_text(transcript.id, " ".join(words))
    app.store.set_transcript_paused(transcript.id, True)
    app._refresh_transcript_list()
    settle(app, 200)
    app._handle_open_transcript(transcript)
    settle(app, 300)
    app.callback_errors = []
    app.report_callback_exception = lambda *details: app.callback_errors.append(details)
    return transcript


@pytest.fixture
def book(tmp_path, open_real_app):
    with _open(tmp_path, open_real_app) as app:
        _load(app, WORD_LIST)
        yield app
        assert app.callback_errors == []


def _skip_to(app, index):
    """One press of >> or << that lands on index, still paused."""
    reader = app.canvas.reader_display
    distance = index - reader.session.index
    app.settings_store.set_skip_behavior(abs(distance), False)
    app.canvas.set_skip_word_count(abs(distance))
    click_button(app.footer.skip_forward_button if distance > 0 else app.footer.skip_back_button)
    settle(app, 150)
    assert reader.session.index == index


def _ribbon(app):
    """What each part of the ribbon says, or None when it isn't on screen."""
    reader = app.canvas.reader_display
    parts = (reader.context_before, reader.context_current, reader.context_after)
    return tuple(part.cget("text") if part.winfo_ismapped() else None for part in parts)


def _left_right(label):
    return label.winfo_rootx(), label.winfo_rootx() + label.winfo_width()


def _middle_y(label):
    return label.winfo_rooty() + label.winfo_height() / 2


def test_on_the_first_word_there_is_nothing_before_it(book):
    assert _ribbon(book) == (None, "w0", "w1 w2")


def test_further_in_the_word_before_and_the_two_after_sit_either_side(book):
    _skip_to(book, 10)

    assert _ribbon(book) == ("w9", "w10", "w11 w12")
    reader = book.canvas.reader_display
    before, current, after = reader.context_before, reader.context_current, reader.context_after
    gap = reader.PERIPHERAL_CONTEXT_WORD_GAP_PX
    assert abs(_left_right(current)[0] - _left_right(before)[1] - gap) <= GAP_SLACK, "the word before ends just left of it"
    assert abs(_left_right(after)[0] - _left_right(current)[1] - gap) <= GAP_SLACK, "the words after start just right of it"
    assert abs(_middle_y(before) - _middle_y(current)) <= 1
    assert abs(_middle_y(after) - _middle_y(current)) <= 1


def test_on_the_last_word_there_is_nothing_after_it(book):
    _skip_to(book, len(WORD_LIST) - 1)

    assert _ribbon(book) == ("w18", "w19", None)


def test_going_back_from_the_last_word_brings_the_words_after_back(book):
    _skip_to(book, len(WORD_LIST) - 1)
    _skip_to(book, 5)

    assert _ribbon(book) == ("w4", "w5", "w6 w7")


def test_going_back_to_the_first_word_takes_the_word_before_away(book):
    _skip_to(book, 10)
    _skip_to(book, 0)

    assert _ribbon(book) == (None, "w0", "w1 w2")


def test_with_the_ribbon_off_none_of_it_shows(book):
    _skip_to(book, 10)
    book.settings_store.set_peripheral_context_enabled(False)
    book.canvas.set_peripheral_context_enabled(False)
    settle(book, 100)

    assert _ribbon(book) == (None, None, None)


def test_the_ribbon_slides_with_a_pan_and_comes_back_when_centred(tmp_path, open_real_app):
    words = ["w0", "w1", "w2", LONG_WORD, "w4", "w5", "w6"]
    with _open(tmp_path, open_real_app) as app:
        _load(app, words)
        _skip_to(app, 3)
        reader = app.canvas.reader_display
        parts = (reader.context_before, reader.context_current, reader.context_after)
        assert _ribbon(app) == ("w2", LONG_WORD, "w4 w5")
        assert reader._scrollbar_visible, "the long word spills past the reader"
        centred = [part.winfo_rootx() for part in parts]

        # A click at the far right end of the scrollbar's track pans all the way.
        scrollbar = reader._scrollbar
        scrollbar._canvas.event_generate("<Button-1>", x=scrollbar._canvas.winfo_width() - 2, y=3)
        settle(app, 100)

        pan = reader._pan_offset_px
        assert pan < 0, "panned to show the right-hand end"
        for part, x in zip(parts, centred):
            assert abs(part.winfo_rootx() - (x + pan)) <= 1, "each part slid as far as the word"
        assert _ribbon(app) == ("w2", LONG_WORD, "w4 w5")

        app.focus_force()
        settle(app, 100)
        (app.focus_get() or app).event_generate("<c>")
        settle(app, 100)

        assert reader._pan_offset_px == 0
        assert [part.winfo_rootx() for part in parts] == centred
        assert app.callback_errors == []
