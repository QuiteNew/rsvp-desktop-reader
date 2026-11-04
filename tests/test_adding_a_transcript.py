"""Tests for adding a transcript from the sidebar's "+" (gui/app.py,
_open_add_transcript_chooser(), _create_transcript() and
_handle_add_from_file_requested()): a blank one, and one made from a file.

A new transcript starts with the Defaults tab's speed, word size and chunking,
and with the reading colours that go with the theme the app is running in (see
test_reading_colours_follow_theme.py for what happens to those later). A file
is read at once, so one that can't be used fails with a message before the
person is asked for a title. A usable one comes up in the same New Transcript
window, with the title taken from the file's name. What was read goes in as an
unstarted draft, the way a pasted text sits before Start reading, and a very
long file gets a warning in that window but is never refused.

Each test builds the real app with open_real_app (conftest.py) and presses the
real buttons. The system's file picker can't be driven, so it's swapped for a
stand-in that hands back the path the test chose. The files are real ones in the
test's own folder, and the importers read them for real, since what's tested
here is what the app does with their answer. The "Importing..." window is the
real one, only watched, so the test can see that it came up before the import and
was gone before anything else opened."""

import customtkinter as ctk
import pytest

import gui.app
from core import importers
from gui.components.add_transcript_chooser_dialog import AddTranscriptChooserDialog
from gui.components.add_transcript_dialog import AddTranscriptDialog
from gui.components.importing_dialog import ImportingDialog
from gui.theme import DARK_READING_BACKGROUND_COLOR, DARK_READING_FONT_COLOR, DARK_READING_HIGHLIGHT_COLOR

from tk_helpers import all_widgets, click_button, settle

# What Settings -> Defaults is set to in the tests that need to see it used:
# none of it is what a new install starts with.
DEFAULTS = dict(wpm=410, font_color="#111111", highlight_color="#222222", background_color="#333333", font_size=48)
CHUNKING = dict(enabled=True, size=3, mode="adaptive", char_target=24)


def windows(app, cls):
    return [w for w in app.winfo_children() if isinstance(w, cls)]


def button(window, text):
    return next(w for w in all_widgets(window) if isinstance(w, ctk.CTkButton) and w.cget("text") == text)


def press_plus(app):
    plus = next(w for w in app.list_header.winfo_children() if isinstance(w, ctk.CTkButton))
    click_button(plus)
    settle(app, 400)


def choose(app, text):
    """Click one of the two choices in the window the "+" opens."""
    (chooser,) = windows(app, AddTranscriptChooserDialog)
    click_button(button(chooser, text))
    settle(app, 400)


def the_new_transcript_window(app):
    (dialog,) = windows(app, AddTranscriptDialog)
    return dialog


def set_defaults(app):
    app.settings_store.set_defaults(**DEFAULTS)
    app.settings_store.set_chunking_defaults(**CHUNKING)


# ---- the window the "+" opens ----

def test_the_plus_offers_a_blank_transcript_or_one_from_a_file(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        press_plus(app)

        (chooser,) = windows(app, AddTranscriptChooserDialog)
        texts = [w.cget("text") for w in all_widgets(chooser) if isinstance(w, ctk.CTkButton)]
        assert texts == ["Blank transcript", "Add from file…"]
        assert app.store.transcripts == []


def test_choosing_blank_closes_that_window_and_asks_for_a_title_and_space(tmp_path, open_real_app, picker):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        app._handle_new_space("Work")  # also switches to it, so the default isn't just the first space
        settle(app, 200)
        press_plus(app)

        choose(app, "Blank transcript")

        assert windows(app, AddTranscriptChooserDialog) == []
        assert picker.calls == [], "Blank transcript shouldn't ask for a file"
        dialog = the_new_transcript_window(app)
        assert dialog.title() == "New Transcript"
        assert dialog.title_entry.get() == ""
        assert dialog.space_menu.get() == "Work"
        assert list(dialog.space_menu.cget("values")) == [first, "Work"]


# ---- a blank transcript ----

@pytest.mark.parametrize("mode, expected", [
    ("Light", ("#111111", "#222222", "#333333")),
    ("Dark", (DARK_READING_FONT_COLOR, DARK_READING_HIGHLIGHT_COLOR, DARK_READING_BACKGROUND_COLOR)),
], ids=["light", "dark"])
def test_a_blank_transcript_starts_with_the_defaults_and_the_themes_colours(tmp_path, open_real_app, monkeypatch, mode, expected):
    monkeypatch.setattr(gui.app, "CTK_APPEARANCE_MODE", mode)
    with open_real_app(tmp_path) as app:
        set_defaults(app)
        press_plus(app)
        choose(app, "Blank transcript")
        dialog = the_new_transcript_window(app)
        dialog.title_entry.insert(0, "  Lecture 3  ")

        click_button(button(dialog, "Create"))
        settle(app, 300)

        (transcript,) = app.store.transcripts
        assert transcript.title == "Lecture 3"
        assert transcript.space == app.store.current_space
        assert (transcript.font_color, transcript.highlight_color, transcript.background_color) == expected
        assert transcript.font_color_is_default and transcript.highlight_color_is_default and transcript.background_color_is_default
        assert (transcript.wpm, transcript.font_size) == (DEFAULTS["wpm"], DEFAULTS["font_size"])
        assert (transcript.chunking_enabled, transcript.chunk_size) == (CHUNKING["enabled"], CHUNKING["size"])
        assert (transcript.chunk_mode, transcript.chunk_char_target) == (CHUNKING["mode"], CHUNKING["char_target"])
        assert (transcript.raw_text, transcript.draft_text) == ("", "")
        assert list(app.list_body._rows) == [transcript.id]
        assert windows(app, AddTranscriptDialog) == []
        assert app._current_transcript is None, "adding one shouldn't open it"


def test_a_transcript_goes_in_the_space_that_was_picked(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        first = app.store.current_space
        app._handle_new_space("Work")
        app._handle_space_selected(first)
        settle(app, 200)
        press_plus(app)
        choose(app, "Blank transcript")
        dialog = the_new_transcript_window(app)
        dialog.title_entry.insert(0, "Elsewhere")
        dialog.space_menu.set("Work")

        click_button(button(dialog, "Create"))
        settle(app, 300)

        (transcript,) = app.store.transcripts
        assert transcript.space == "Work"
        assert list(app.list_body._rows) == [], "it isn't in the space on screen"
        assert app.store.transcripts_in_space("Work") == [transcript]


def test_without_a_title_nothing_is_created_and_cancel_adds_nothing(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        press_plus(app)
        choose(app, "Blank transcript")
        dialog = the_new_transcript_window(app)
        dialog.title_entry.insert(0, "   ")

        click_button(button(dialog, "Create"))
        settle(app, 200)

        assert dialog.winfo_exists(), "it should stay open for a title"
        assert app.store.transcripts == []

        click_button(button(dialog, "Cancel"))
        settle(app, 200)

        assert windows(app, AddTranscriptDialog) == []
        assert app.store.transcripts == []


# ---- from a file ----

class Picker:
    """Stands in for tkinter's filedialog: hands back .path (empty for Cancel)
    and notes how it was asked."""

    def __init__(self):
        self.path = ""
        self.calls = []

    def askopenfilename(self, **kwargs):
        self.calls.append(kwargs)
        return self.path


@pytest.fixture(autouse=True)
def picker(monkeypatch):
    """In every test here, not only the file ones. If something opened the real
    picker by mistake, the whole run would sit waiting for someone to answer it,
    when it should fail."""
    stand_in = Picker()
    monkeypatch.setattr(gui.app, "filedialog", stand_in)
    return stand_in


@pytest.fixture
def events(monkeypatch):
    """Notes, in order, what the app puts on screen while it adds a file: the
    "Importing..." window coming up and going, and any message. The window is the
    real one, only watched."""
    log = []

    class WatchedImportingDialog(ImportingDialog):
        def __init__(self, master, filename):
            super().__init__(master, filename)
            said = next(w.cget("text") for w in all_widgets(self) if isinstance(w, ctk.CTkLabel))
            log.append(("importing", filename, said))

        def finish(self):
            log.append(("finished", self.winfo_exists()))
            super().finish()

    def message(master, title, text):
        log.append(("message", title, text))

    monkeypatch.setattr(gui.app, "ImportingDialog", WatchedImportingDialog)
    monkeypatch.setattr(gui.app, "MessageDialog", message)
    return log


def _file(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_cancelling_the_file_picker_does_nothing(tmp_path, open_real_app, picker, events):
    with open_real_app(tmp_path) as app:
        press_plus(app)

        choose(app, "Add from file…")

        assert windows(app, AddTranscriptChooserDialog) == []
        (asked,) = picker.calls
        assert asked["title"] == "Add from File"
        everything = dict(asked["filetypes"])["Supported documents"].split()
        assert sorted(everything) == sorted(f"*{ext}" for ext in importers.SUPPORTED_EXTENSIONS)
        assert events == []
        assert windows(app, AddTranscriptDialog) == []
        assert app.store.transcripts == []


def test_a_file_that_cant_be_read_is_reported_before_any_title_is_asked_for(tmp_path, open_real_app, picker, events):
    picker.path = _file(tmp_path, "empty.txt", "   \n  ")
    with open_real_app(tmp_path) as app:
        press_plus(app)

        choose(app, "Add from file…")

        assert [e[0] for e in events] == ["importing", "finished", "message"], "the Importing window should be gone first"
        assert events[0][:2] == ("importing", "empty.txt")
        assert events[1] == ("finished", True)
        assert events[2][1] == "Couldn't add that file"
        assert "empty.txt didn't contain any readable text" in events[2][2]
        assert windows(app, ImportingDialog) == []
        assert windows(app, AddTranscriptDialog) == []
        assert app.store.transcripts == []


def test_a_file_comes_up_in_the_new_transcript_window_and_is_added_as_an_unstarted_draft(tmp_path, open_real_app, picker, events):
    text = "Alpha beta gamma delta. Epsilon zeta eta theta."
    picker.path = _file(tmp_path, "notes.txt", text)
    with open_real_app(tmp_path) as app:
        set_defaults(app)
        first = app.store.current_space
        app._handle_new_space("Work")  # also switches to it, so the default isn't just the first space
        settle(app, 200)
        press_plus(app)

        choose(app, "Add from file…")

        assert [e[0] for e in events] == ["importing", "finished"]
        assert "“notes.txt”" in events[0][2], "the Importing window should name the file"
        assert windows(app, ImportingDialog) == []
        dialog = the_new_transcript_window(app)
        assert dialog.title() == "Add Transcript from File"
        assert dialog.title_entry.get() == "notes"
        assert dialog.space_menu.get() == "Work"
        assert not any(isinstance(w, ctk.CTkLabel) and w.cget("text").startswith("Heads up") for w in all_widgets(dialog))
        assert app.store.transcripts == [], "nothing is added until Create"

        dialog.title_entry.delete(0, "end")
        dialog.title_entry.insert(0, "Week 1 notes")
        dialog.space_menu.set(first)
        click_button(button(dialog, "Create"))
        settle(app, 300)

        (transcript,) = app.store.transcripts
        assert (transcript.title, transcript.space) == ("Week 1 notes", first)
        assert transcript.draft_text == importers.import_file(picker.path) == text
        assert transcript.raw_text == ""
        assert (transcript.wpm, transcript.font_size) == (DEFAULTS["wpm"], DEFAULTS["font_size"])
        assert app._current_transcript is None

        app._handle_space_selected(first)
        settle(app, 200)
        app._handle_open_transcript(transcript)
        settle(app, 300)
        assert app.canvas._input_currently_shown, "it should open on the text, to be looked over before reading"
        assert app.canvas.input_view.get_text().strip() == text


@pytest.mark.parametrize("extra, warned", [(0, False), (1, True)], ids=["at_the_limit", "one_over"])
def test_a_very_long_file_gets_a_warning_but_is_still_added(tmp_path, open_real_app, picker, events, extra, warned):
    with open_real_app(tmp_path) as app:
        words = app.LARGE_IMPORT_WORD_WARNING_THRESHOLD + extra
        picker.path = _file(tmp_path, "book.txt", " ".join(["word"] * words))
        press_plus(app)

        choose(app, "Add from file…")

        dialog = the_new_transcript_window(app)
        warnings = [
            w.cget("text") for w in all_widgets(dialog)
            if isinstance(w, ctk.CTkLabel) and w.cget("text").startswith("Heads up")
        ]
        if warned:
            (warning,) = warnings
            assert f"about {words:,} words long" in warning
        else:
            assert warnings == []

        click_button(button(dialog, "Create"))
        settle(app, 400)

        (transcript,) = app.store.transcripts
        assert len(transcript.draft_text.split()) == words
