"""Tests for the app's checks before deleting a space or moving a transcript to
another space (gui/app.py, _handle_space_delete_requested(),
_handle_space_delete_confirmed(), _handle_move_requested() and
_handle_move_confirmed()).

A space can't be deleted while it's the only one, or while transcripts are still
in it, and the app says why instead of quietly doing nothing. Only an empty
space among others gets the confirmation. A transcript can't be moved when there
is no other space to move it to, and otherwise the move offers every space but
its own. A moved transcript leaves the list but, if it's open, stays open.

The dialogs themselves are tested in test_dialog_keys.py. Here the question is
which one the app opens, so the three it might open are swapped for stand-ins
that note how they were called. Each test builds the real app with
open_real_app (conftest.py), and the space picker is the real one, since the
messages about a space are shown over it."""

import pytest

from tk_helpers import settle


class Opened:
    """Stands in for a dialog class and notes each time it's opened, with
    the parent it was given and everything else it was called with."""

    def __init__(self):
        self.calls = []

    def __call__(self, master, *args, **kwargs):
        self.calls.append((master, args, kwargs))
        return self


@pytest.fixture
def dialogs(monkeypatch):
    import gui.app

    opened = {name: Opened() for name in ("MessageDialog", "DeleteSpaceDialog", "MoveTranscriptDialog")}
    for name, stand_in in opened.items():
        monkeypatch.setattr(gui.app, name, stand_in)
    return opened


def _add_space(app, name):
    app._handle_new_space(name)
    settle(app, 100)


def _add_transcript(app, title, space=None):
    store = app.store
    transcript = store.add_transcript(title, space or store.current_space)
    store.set_transcript_text(transcript.id, "one two three four five six")
    store.set_transcript_paused(transcript.id, True)
    app._refresh_transcript_list()
    settle(app, 200)
    return transcript


def _open_space_picker(app):
    app._open_space_selection_dialog()
    settle(app, 300)
    return app._space_selection_dialog


def _message(dialogs):
    """The parent, title and message of the one message shown."""
    assert len(dialogs["MessageDialog"].calls) == 1
    master, args, _ = dialogs["MessageDialog"].calls[0]
    title, message = args
    return master, title, message


# ---- deleting a space ----

def test_the_only_space_cant_be_deleted(tmp_path, open_real_app, dialogs):
    with open_real_app(tmp_path) as app:
        only = app.store.current_space
        picker = _open_space_picker(app)

        app._handle_space_delete_requested(only)

        master, title, message = _message(dialogs)
        assert master is picker
        assert title == "Can't delete this space"
        assert "only space" in message
        assert dialogs["DeleteSpaceDialog"].calls == []
        assert app.store.spaces == [only]


@pytest.mark.parametrize("count, says", [(1, "1 transcript in it"), (2, "2 transcripts in it")], ids=["one", "two"])
def test_a_space_with_transcripts_in_it_cant_be_deleted(tmp_path, open_real_app, dialogs, count, says):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        _add_space(app, "Work")
        for number in range(count):
            _add_transcript(app, f"T{number}", space="Work")
        picker = _open_space_picker(app)

        app._handle_space_delete_requested("Work")

        master, title, message = _message(dialogs)
        assert master is picker
        assert title == "Can't delete this space"
        assert '"Work"' in message and says in message
        assert dialogs["DeleteSpaceDialog"].calls == []
        assert app.store.spaces == [first, "Work"]


def test_an_empty_space_asks_before_it_goes(tmp_path, open_real_app, dialogs):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        _add_space(app, "Work")
        picker = _open_space_picker(app)

        app._handle_space_delete_requested("Work")

        assert dialogs["MessageDialog"].calls == []
        (master, _, kwargs), = dialogs["DeleteSpaceDialog"].calls
        assert master is picker
        assert kwargs["space_name"] == "Work"
        assert app.store.spaces == [first, "Work"], "deleted before it was confirmed"


def test_confirming_deletes_the_space_and_shows_where_you_are_now(tmp_path, open_real_app, dialogs):
    """Work is the space open when it's deleted, so the app moves to the first
    space: the label below the list names it, the list shows its
    transcripts, and the space picker closes."""
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        kept = _add_transcript(app, "In the first space")
        _add_space(app, "Work")
        assert app.store.current_space == "Work"
        assert list(app.list_body._rows) == []
        picker = _open_space_picker(app)
        app._handle_space_delete_requested("Work")
        _, _, kwargs = dialogs["DeleteSpaceDialog"].calls[0]

        kwargs["on_confirm"]()
        settle(app, 300)

        assert app.store.spaces == [first]
        assert app.store.current_space == first
        assert app.spaces.name_label.cget("text") == first
        assert list(app.list_body._rows) == [kept.id]
        assert not picker.winfo_exists()


# ---- moving a transcript ----

def test_a_transcript_cant_be_moved_when_there_is_no_other_space(tmp_path, open_real_app, dialogs):
    with open_real_app(tmp_path) as app:
        only = app.store.current_space
        transcript = _add_transcript(app, "A")

        app._handle_move_requested(transcript)

        master, title, message = _message(dialogs)
        assert master is app
        assert title == "No other spaces"
        assert "Create another one first" in message
        assert dialogs["MoveTranscriptDialog"].calls == []
        assert transcript.space == only


def test_a_move_offers_every_space_but_its_own(tmp_path, open_real_app, dialogs):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        _add_space(app, "Work")
        _add_space(app, "Home")
        transcript = _add_transcript(app, "A", space="Work")

        app._handle_move_requested(transcript)

        assert dialogs["MessageDialog"].calls == []
        (master, _, kwargs), = dialogs["MoveTranscriptDialog"].calls
        assert master is app
        assert kwargs["transcript_title"] == "A"
        assert kwargs["other_spaces"] == [first, "Home"]


def test_a_moved_transcript_leaves_the_list_but_stays_open(tmp_path, open_real_app, dialogs):
    """It's moved out of the space on screen, so it drops out of the sidebar,
    but the reading session it's open in carries on undisturbed."""
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        _add_space(app, "Work")
        app._handle_space_selected(first)
        settle(app, 200)
        a = _add_transcript(app, "A")
        b = _add_transcript(app, "B")
        app._handle_open_transcript(a)
        settle(app, 300)
        session = app.canvas.reader_display.session

        app._handle_move_requested(a)
        _, _, kwargs = dialogs["MoveTranscriptDialog"].calls[0]
        kwargs["on_select"]("Work")
        settle(app, 300)

        assert a.space == "Work"
        assert app.store.transcripts_in_space("Work") == [a]
        assert list(app.list_body._rows) == [b.id]
        assert app.canvas.current_transcript is a
        assert app.canvas.reader_display.session is session
        assert app.header._full_title == "A"