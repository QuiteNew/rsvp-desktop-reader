"""Export Data and Import Data, from the Settings window to the closed app.

core/data_bundle.py has its own tests for building, reading and applying a
bundle. This file is about what the app does around them: asking for a file,
writing it, telling the person when something went wrong, leaving everything
alone when the file is no good, and, after a confirmed import, applying it and
closing the app.

The system's file dialogs can't be driven, so the Settings window gets a
stand-in that hands back whatever path a test sets. Everything else is the real
thing: the real Settings window, the real buttons, the real message and
Replace/Expand/Cancel windows. Importing always closes the app, so those tests
look at what was saved to disk once it has gone.
"""
import json
import tkinter

import customtkinter as ctk
import pytest

import gui.components.settings_window as settings_window_module
from core import data_bundle
from core.settings_store import SettingsStore
from core.transcript_store import TranscriptStore
from gui.components.import_confirm_dialog import ImportConfirmDialog
from gui.components.message_dialog import MessageDialog
from tk_helpers import all_widgets, click_button, settle

WORDS = "word " * 400


# ---- stand-in for the system's file dialogs ----

class FileDialogs:
    """Stands in for tkinter's filedialog in the Settings window: hands back
    save_path or open_path (empty for Cancel) and notes how it was asked."""

    def __init__(self):
        self.save_path = ""
        self.open_path = ""
        self.save_calls = []
        self.open_calls = []

    def asksaveasfilename(self, **kwargs):
        self.save_calls.append(kwargs)
        return self.save_path

    def askopenfilename(self, **kwargs):
        self.open_calls.append(kwargs)
        return self.open_path


@pytest.fixture(autouse=True)
def file_dialogs(monkeypatch):
    """In every test here, so a mistake can never open a real dialog and sit
    waiting for someone to answer it."""
    stand_in = FileDialogs()
    monkeypatch.setattr(settings_window_module, "filedialog", stand_in)
    return stand_in


# ---- helpers ----

def _button(window, text):
    return next(w for w in all_widgets(window) if isinstance(w, ctk.CTkButton) and w.cget("text") == text)


def _windows(app, cls):
    """The dialogs of one kind open over the Settings window."""
    return [w for w in app._settings_window.winfo_children() if isinstance(w, cls)]


def _only(app, cls):
    (found,) = _windows(app, cls)
    return found


def _says(dialog):
    """What the dialog's text says."""
    return next(w.cget("text") for w in all_widgets(dialog) if isinstance(w, ctk.CTkLabel))


def _open_settings(app):
    app._open_settings_window()
    settle(app, 300)
    app._settings_window.tabview.set("Storage")
    settle(app, 100)


def _press_in_settings(app, text):
    click_button(_button(app._settings_window, text))
    settle(app, 300)


def _dismiss(app, dialog, button="OK"):
    click_button(_button(dialog, button))
    settle(app, 200)


def _bundle_text(tmp_path, wpm=410, mutate=None):
    """A bundle as another machine would have exported it: two spaces, two
    transcripts (numbered from 1, like any fresh data) and its own settings.
    That machine's stores are kept in a folder of their own under tmp_path."""
    other_machine = tmp_path / "other machine"
    other_machine.mkdir(exist_ok=True)
    transcripts = TranscriptStore(data_directory=str(other_machine))
    transcripts.add_space("Imported space")
    first = transcripts.add_transcript("Imported one", "General")
    transcripts.set_transcript_draft_text(first.id, "imported draft one")
    second = transcripts.add_transcript("Imported two", "Imported space")
    transcripts.set_transcript_draft_text(second.id, "imported draft two")
    bundle = data_bundle.build_bundle(transcripts, SettingsStore(settings_directory=str(other_machine)))
    bundle["settings"]["default_wpm"] = wpm
    if mutate:
        mutate(bundle)
    return json.dumps(bundle)


def _write(tmp_path, text, name="bundle.json"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _snapshot(app):
    """Enough of the app's data to see whether anything changed."""
    return (
        app.store.export_state(),
        app.settings_store.export_settings(),
    )


def _without_window_placement(settings):
    """Closing the app saves where its window is, which is not an import's doing."""
    return {key: value for key, value in settings.items() if not key.startswith("window_")}


def _app_has_closed(app):
    try:
        app.winfo_exists()
    except tkinter.TclError:
        return True
    return False


def _on_disk(directory):
    return TranscriptStore(data_directory=str(directory)), SettingsStore(settings_directory=str(directory))


def _titles(store):
    return [t.title for t in store.transcripts]


def _import_with(app, tmp_path, file_dialogs, choice, text=None):
    """Settings → Import Data… → the given choice, up to and including the
    "Import complete" message, which is left open. Returns that message."""
    file_dialogs.open_path = _write(tmp_path, text if text is not None else _bundle_text(tmp_path))
    _open_settings(app)
    _press_in_settings(app, "Import Data…")
    _press_in_confirm(app, choice)
    return _only(app, MessageDialog)


def _press_in_confirm(app, choice):
    click_button(_button(_only(app, ImportConfirmDialog), choice))
    settle(app, 300)


@pytest.fixture
def data_dir(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    return folder


def _two_transcripts(app):
    """Two transcripts of the app's own. The first is numbered 1, the same as the
    first one in the imported bundle."""
    mine = app.store.add_transcript("Mine", app.store.current_space)
    app.store.set_transcript_draft_text(mine.id, "my draft")
    other = app.store.add_transcript("Other mine", app.store.current_space)
    app.store.set_transcript_draft_text(other.id, "other draft")
    app._refresh_transcript_list()
    settle(app, 200)
    assert mine.id == 1, "the clash between ids is what several of these tests are about"
    return mine, other


# ---- export ----

def test_export_writes_everything_to_the_chosen_file_and_says_where(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        _two_transcripts(app)
        target = str(tmp_path / "backup.json")
        file_dialogs.save_path = target
        _open_settings(app)

        _press_in_settings(app, "Export Data…")

        (asked,) = file_dialogs.save_calls
        assert asked["title"] == "Export Data"
        assert asked["initialfile"] == "rsvp-reader-export.json"
        assert asked["defaultextension"] == ".json"
        bundle = data_bundle.parse_bundle((tmp_path / "backup.json").read_text(encoding="utf-8"))
        assert [t.title for t in bundle["data"]["transcripts"]] == ["Mine", "Other mine"]
        assert bundle["settings"] == app.settings_store.export_settings()
        message = _only(app, MessageDialog)
        assert message.title() == "Export complete"
        assert _says(message) == f"Your data was exported to:\n\n{target}"
        assert not _app_has_closed(app), "exporting doesn't close the app"
        _dismiss(app, message)
        assert _windows(app, MessageDialog) == []


def test_cancelling_the_save_dialog_writes_nothing_and_says_nothing(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        file_dialogs.save_path = ""
        _open_settings(app)

        _press_in_settings(app, "Export Data…")

        assert len(file_dialogs.save_calls) == 1
        assert _windows(app, MessageDialog) == []
        assert list(tmp_path.glob("*.json")) == []


def test_a_file_that_cant_be_written_is_reported(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        file_dialogs.save_path = str(tmp_path / "no such folder" / "backup.json")
        _open_settings(app)

        _press_in_settings(app, "Export Data…")

        message = _only(app, MessageDialog)
        assert message.title() == "Export failed"
        assert _says(message).startswith("Couldn't write the export file:\n\n")
        assert not (tmp_path / "no such folder").exists()
        assert not _app_has_closed(app)


# ---- import: files that can't be used ----

def test_cancelling_the_open_dialog_does_nothing(data_dir, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        _two_transcripts(app)
        before = _snapshot(app)
        file_dialogs.open_path = ""
        _open_settings(app)

        _press_in_settings(app, "Import Data…")

        (asked,) = file_dialogs.open_calls
        assert asked["title"] == "Import Data"
        assert _windows(app, MessageDialog) == []
        assert _windows(app, ImportConfirmDialog) == []
        assert _snapshot(app) == before


def test_files_that_cant_be_imported_are_reported_and_nothing_changes(data_dir, tmp_path, open_real_app, file_dialogs):
    def _without(key):
        return lambda bundle: bundle.pop(key)

    def _version_99(bundle):
        bundle["bundle_format"] = 99

    cases = {
        "not there": str(tmp_path / "missing.json"),
        "not json": _write(tmp_path, "this is not json", "a.json"),
        "not a bundle": _write(tmp_path, json.dumps({"hello": 1}), "b.json"),
        "other version": _write(tmp_path, _bundle_text(tmp_path, mutate=_version_99), "c.json"),
        "no data": _write(tmp_path, _bundle_text(tmp_path, mutate=_without("data")), "d.json"),
        "no settings": _write(tmp_path, _bundle_text(tmp_path, mutate=_without("settings")), "e.json"),
    }
    with open_real_app(data_dir) as app:
        _two_transcripts(app)
        before = _snapshot(app)
        _open_settings(app)

        for name, path in cases.items():
            file_dialogs.open_path = path
            _press_in_settings(app, "Import Data…")

            message = _only(app, MessageDialog)
            assert message.title() == "Import failed", name
            if name == "not there":
                assert _says(message).startswith("Couldn't read that file:\n\n")
            else:
                text = open(path, encoding="utf-8").read()
                with pytest.raises(data_bundle.BundleFormatError) as why:
                    data_bundle.parse_bundle(text)
                assert _says(message) == str(why.value), name
            assert _windows(app, ImportConfirmDialog) == [], name
            assert _snapshot(app) == before, name
            assert not _app_has_closed(app), name
            _dismiss(app, message)


# ---- import: a good file ----

def test_a_good_file_asks_how_to_import_and_changes_nothing_until_answered(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        _two_transcripts(app)
        before = _snapshot(app)
        file_dialogs.open_path = _write(tmp_path, _bundle_text(tmp_path))
        _open_settings(app)

        _press_in_settings(app, "Import Data…")

        confirm = _only(app, ImportConfirmDialog)
        assert _windows(app, MessageDialog) == []
        assert _snapshot(app) == before, "nothing is applied before Replace or Expand"

        _dismiss(app, confirm, "Cancel")

        assert _windows(app, ImportConfirmDialog) == []
        assert _windows(app, MessageDialog) == []
        assert _snapshot(app) == before
        assert not _app_has_closed(app)


def test_expand_adds_the_imported_transcripts_keeps_the_settings_and_closes_the_app(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        _two_transcripts(app)
        settings_before = _without_window_placement(app.settings_store.export_settings())

        message = _import_with(app, tmp_path, file_dialogs, "Expand")

        assert message.title() == "Import complete"
        assert _says(message) == "Your data was imported. RSVP Reader will now close! Reopen it to see the change."
        assert not _app_has_closed(app), "it closes once the message is dismissed"
        assert _titles(app.store) == ["Mine", "Other mine", "Imported one", "Imported two"]
        assert [t.id for t in app.store.transcripts] == [1, 2, 3, 4], "the imported ones are numbered after ours"
        assert "Imported space" in app.store.spaces

        _dismiss(app, message)

        assert _app_has_closed(app)
    transcripts, settings = _on_disk(data_dir)
    assert _titles(transcripts) == ["Mine", "Other mine", "Imported one", "Imported two"]
    assert transcripts.spaces[-1] == "Imported space"
    assert _without_window_placement(settings.export_settings()) == settings_before, "Expand leaves the settings alone"


def test_replace_swaps_in_the_imported_data_and_settings_but_not_the_data_folder_and_closes_the_app(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        _two_transcripts(app)
        folder = app.settings_store.data_directory
        assert app.settings_store.default_wpm != 410

        message = _import_with(app, tmp_path, file_dialogs, "Replace")

        assert message.title() == "Import complete"
        assert _titles(app.store) == ["Imported one", "Imported two"]
        assert app.settings_store.default_wpm == 410
        assert app.settings_store.data_directory == folder, "the imported data goes where this machine keeps its data"
        assert not _app_has_closed(app)

        _dismiss(app, message)

        assert _app_has_closed(app)
    transcripts, settings = _on_disk(data_dir)
    assert _titles(transcripts) == ["Imported one", "Imported two"]
    assert transcripts.spaces == ["General", "Imported space"]
    assert settings.default_wpm == 410
    assert settings.data_directory == folder


# ---- import while something is open ----
#
# The open transcript is saved by its id, while it is read and when the app
# closes. After a Replace the imported transcripts are numbered from 1 as well,
# so a transcript that was still open could be written onto an imported one.

def _open_with_text(app, transcript, settle_ms=200):
    app._handle_open_transcript(transcript)
    settle(app, settle_ms)


def test_replace_while_a_transcript_is_being_edited_leaves_the_imported_one_as_it_was_exported(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        mine, _ = _two_transcripts(app)
        _open_with_text(app, mine)
        app.canvas.input_view.textbox.insert("end", " typed just before")
        settle(app, 100)

        message = _import_with(app, tmp_path, file_dialogs, "Replace")

        assert app._current_transcript is None, "the old transcript is closed before the data is swapped"
        assert app.canvas.current_transcript is None
        _dismiss(app, message)
    transcripts, _ = _on_disk(data_dir)
    assert [(t.id, t.title, t.draft_text) for t in transcripts.transcripts] == [
        (1, "Imported one", "imported draft one"),
        (2, "Imported two", "imported draft two"),
    ]


def test_replace_while_a_transcript_is_being_read_credits_the_reading_to_nobody(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        mine, _ = _two_transcripts(app)
        app.store.set_transcript_text(mine.id, WORDS)
        app.store.set_transcript_paused(mine.id, False)
        _open_with_text(app, mine, settle_ms=1500)

        message = _import_with(app, tmp_path, file_dialogs, "Replace")
        settle(app, 500)

        assert app.canvas.reader_display.session is None, "the reading has stopped"
        _dismiss(app, message)
    transcripts, _ = _on_disk(data_dir)
    assert [(t.id, t.times_read, t.total_words_read, t.position) for t in transcripts.transcripts] == [
        (1, 0, 0, 0),
        (2, 0, 0, 0),
    ]


def test_replace_while_a_transcript_is_detached_closes_that_window_too(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        mine, other = _two_transcripts(app)
        app.store.set_transcript_text(mine.id, WORDS)
        app.store.set_transcript_paused(mine.id, False)
        _open_with_text(app, mine)
        app.canvas._handle_detach()
        settle(app, 1500)
        _open_with_text(app, other)
        assert app.canvas._detached_window is not None

        message = _import_with(app, tmp_path, file_dialogs, "Replace")

        assert app.canvas._detached_window is None
        _dismiss(app, message)
    transcripts, _ = _on_disk(data_dir)
    assert [(t.id, t.draft_text, t.times_read, t.total_words_read) for t in transcripts.transcripts] == [
        (1, "imported draft one", 0, 0),
        (2, "imported draft two", 0, 0),
    ]


def test_expand_while_a_transcript_is_being_edited_still_saves_the_edit(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        mine, _ = _two_transcripts(app)
        _open_with_text(app, mine)
        app.canvas.input_view.textbox.insert("end", " typed just before")
        settle(app, 100)

        message = _import_with(app, tmp_path, file_dialogs, "Expand")

        assert app._current_transcript is mine, "nothing is closed, the old data is all still right"
        _dismiss(app, message)
    transcripts, _ = _on_disk(data_dir)
    saved = {t.title: t for t in transcripts.transcripts}
    assert saved["Mine"].draft_text == "my draft typed just before"
    assert saved["Imported one"].draft_text == "imported draft one"


def test_expand_while_a_transcript_is_being_read_still_saves_the_reading(data_dir, tmp_path, open_real_app, file_dialogs):
    with open_real_app(data_dir) as app:
        mine, _ = _two_transcripts(app)
        app.store.set_transcript_text(mine.id, WORDS)
        app.store.set_transcript_paused(mine.id, False)
        _open_with_text(app, mine, settle_ms=1500)

        message = _import_with(app, tmp_path, file_dialogs, "Expand")
        _dismiss(app, message)
    transcripts, _ = _on_disk(data_dir)
    saved = {t.title: t for t in transcripts.transcripts}
    assert (saved["Mine"].times_read, saved["Mine"].total_words_read > 0) == (1, True)
    assert (saved["Imported one"].times_read, saved["Imported one"].total_words_read) == (0, 0)
