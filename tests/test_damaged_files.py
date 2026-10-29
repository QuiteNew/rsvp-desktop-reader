"""Tests for keeping a copy of a save file that can't be read: the copy itself
(core/storage.py), the two stores that find such a file
(core/transcript_store.py for data.json, core/settings_store.py for
settings.json) and the message the app shows about it (gui/app.py).

What was agreed: when data.json or settings.json is there but can't be read,
the app copies it aside before anything saves over it, and says so at launch.
On top of that: a file that isn't text at all (half-written bytes after a
crash) no longer stops the app from starting, and the same damaged file read
several times gets one copy, not one per read.

The message is tested on a stand-in, the same way as test_settings_apply.py
tests the app, plus one test with the real app at the end."""

import json
import time
from datetime import datetime
from pathlib import Path

import pytest

import core.storage as storage
import core.settings_store as settings_store
import core.transcript_store as transcript_store
from core.settings_store import SettingsStore
from core.storage import DamagedFile, keep_damaged_copy, load_state, read_state, save_state
from core.transcript_store import TranscriptStore

NOON = datetime(2026, 10, 29, 12, 0, 5)

# Ways a save file turns out to be damaged. Each is written as raw bytes.
DAMAGED = {
    "cut off": b'{"next_id": 3, "spaces": ["General"], "transcr',
    "not text": b'{"next_id": \xff\xfe\x00 3}',
    "empty": b"",
    "a list": b"[1, 2, 3]",
    "the wrong object": b'{"something": "else"}',
}
DAMAGED_DATA = dict(DAMAGED, **{
    "transcripts that are numbers": b'{"next_id": 3, "current_space_index": 0, "spaces": ["General"], "transcripts": [1, 2]}',
})


def _valid_data():
    return {
        "next_id": 2, "current_space_index": 0, "spaces": ["General"],
        "transcripts": [{"id": 1, "title": "Lecture", "space": "General"}],
    }


# ---- the copy (core/storage.py) ----

def test_the_copy_is_named_after_the_file_and_the_time(tmp_path):
    original = tmp_path / "data.json"
    original.write_bytes(b"broken")
    copy = keep_damaged_copy(original, now=NOON)
    assert copy == tmp_path / "data.damaged-20261029-120005.json"


def test_the_copy_is_the_file_exactly_and_the_file_is_left_alone(tmp_path):
    original = tmp_path / "settings.json"
    original.write_bytes(b'{"a": \xff broken')
    copy = keep_damaged_copy(original, now=NOON)
    assert copy.read_bytes() == b'{"a": \xff broken'
    assert original.read_bytes() == b'{"a": \xff broken'


def test_the_same_damaged_file_is_only_copied_once(tmp_path):
    original = tmp_path / "data.json"
    original.write_bytes(b"broken")
    first = keep_damaged_copy(original, now=NOON)
    again = keep_damaged_copy(original, now=datetime(2026, 10, 30, 9, 0, 0))
    assert again == first
    assert len(list(tmp_path.glob("data.damaged-*.json"))) == 1


def test_a_differently_damaged_file_gets_a_copy_of_its_own(tmp_path):
    original = tmp_path / "data.json"
    original.write_bytes(b"broken one way")
    first = keep_damaged_copy(original, now=NOON)
    original.write_bytes(b"broken another way")
    second = keep_damaged_copy(original, now=NOON)  # the same second, too
    assert second == tmp_path / "data.damaged-20261029-120005-2.json"
    assert first.read_bytes() == b"broken one way"
    assert second.read_bytes() == b"broken another way"


def test_a_copy_that_cannot_be_made_gives_none_and_no_error(tmp_path):
    assert keep_damaged_copy(tmp_path / "gone" / "data.json") is None


# ---- data.json (core/storage.py and core/transcript_store.py) ----

def test_no_data_file_is_not_damage(tmp_path):
    assert read_state(str(tmp_path)) == (None, None)


def test_a_good_data_file_is_read_and_nothing_is_copied(tmp_path):
    (tmp_path / "data.json").write_text(json.dumps(_valid_data()), encoding="utf-8")
    state, damaged = read_state(str(tmp_path))
    assert state["transcripts"][0].title == "Lecture"
    assert damaged is None
    assert list(tmp_path.glob("*.damaged-*")) == []


@pytest.mark.parametrize("contents", DAMAGED_DATA.values(), ids=DAMAGED_DATA.keys())
def test_a_damaged_data_file_is_copied_aside(tmp_path, contents):
    (tmp_path / "data.json").write_bytes(contents)
    state, damaged = read_state(str(tmp_path))
    assert state is None
    assert damaged.original == tmp_path / "data.json"
    assert damaged.copy.read_bytes() == contents
    assert load_state(str(tmp_path)) is None  # the old way of asking still works


@pytest.mark.parametrize("contents", DAMAGED_DATA.values(), ids=DAMAGED_DATA.keys())
def test_the_store_starts_empty_and_says_the_file_was_damaged(tmp_path, contents):
    (tmp_path / "data.json").write_bytes(contents)
    store = TranscriptStore(data_directory=str(tmp_path))
    assert store.transcripts == []
    assert store.damaged_file.copy.read_bytes() == contents


def test_the_copy_survives_the_store_saving_over_the_damaged_file(tmp_path):
    (tmp_path / "data.json").write_bytes(DAMAGED["cut off"])
    store = TranscriptStore(data_directory=str(tmp_path))
    store.add_transcript("New", store.current_space)
    assert json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))["transcripts"][0]["title"] == "New"
    assert store.damaged_file.copy.read_bytes() == DAMAGED["cut off"]


def test_a_good_data_file_leaves_the_store_without_damage(tmp_path):
    save_state(str(tmp_path), ["General"], 0, [], 1)
    assert TranscriptStore(data_directory=str(tmp_path)).damaged_file is None


# ---- settings.json (core/settings_store.py) ----

def test_no_settings_file_is_not_damage(tmp_path):
    assert SettingsStore(str(tmp_path)).damaged_file is None


def test_a_good_settings_file_is_read_and_nothing_is_copied(tmp_path):
    SettingsStore(str(tmp_path)).set_defaults(450, "#000000", "#111111", "#222222", 40)
    store = SettingsStore(str(tmp_path))
    assert store.default_wpm == 450
    assert store.damaged_file is None
    assert list(tmp_path.glob("*.damaged-*")) == []


@pytest.mark.parametrize("contents", [v for k, v in DAMAGED.items() if k != "the wrong object"],
                         ids=[k for k in DAMAGED if k != "the wrong object"])
def test_a_damaged_settings_file_is_copied_aside_and_the_defaults_used(tmp_path, contents):
    (tmp_path / "settings.json").write_bytes(contents)
    store = SettingsStore(str(tmp_path))
    assert store.default_wpm == 300
    assert store.damaged_file.original == tmp_path / "settings.json"
    assert store.damaged_file.copy.read_bytes() == contents


def test_a_settings_object_with_unknown_keys_is_not_damage(tmp_path):
    # Unknown keys are dropped on purpose (a newer version's settings, say),
    # so this one reads fine as the defaults and is not copied.
    (tmp_path / "settings.json").write_bytes(DAMAGED["the wrong object"])
    assert SettingsStore(str(tmp_path)).damaged_file is None


def test_reading_the_same_damaged_settings_three_times_makes_one_copy(tmp_path):
    """gui/theme.py reads the settings twice at import, and the app once more."""
    (tmp_path / "settings.json").write_bytes(DAMAGED["not text"])
    stores = [SettingsStore(str(tmp_path)) for _ in range(3)]
    assert len({store.damaged_file.copy for store in stores}) == 1
    assert len(list(tmp_path.glob("settings.damaged-*.json"))) == 1


def test_once_the_settings_are_saved_again_they_are_not_damaged(tmp_path):
    (tmp_path / "settings.json").write_bytes(DAMAGED["cut off"])
    SettingsStore(str(tmp_path)).flush()
    assert SettingsStore(str(tmp_path)).damaged_file is None


# ---- the message at launch (gui/app.py) ----

class _App:
    """Just enough of the app to tell about damaged files: the two stores'
    damaged_file, whether the window is on screen, and after() that only keeps
    notes. Every other method is the app's own, run on this stand-in."""

    def __init__(self, settings_damage=None, data_damage=None, viewable=True):
        self.settings_store = type("Settings", (), {"damaged_file": settings_damage})()
        self.store = type("Transcripts", (), {"damaged_file": data_damage})()
        self.viewable = viewable
        self.after_calls = []
        self.shown = []
        self._damaged_notice_after_id = None

    def winfo_viewable(self):
        return self.viewable

    def after(self, milliseconds, callback):
        self.after_calls.append((milliseconds, callback))
        return f"after#{len(self.after_calls)}"

    def _show_notices(self, notices):
        self.shown.append(notices)

    def __getattr__(self, name):
        from gui.app import RSVPApp
        method = getattr(RSVPApp, name)

        def run(*args, **kwargs):
            return method(self, *args, **kwargs)
        run.__name__ = name
        return run


SETTINGS_COPY = DamagedFile(Path("/x/settings.json"), Path("/x/settings.damaged-20261029-120005.json"))
DATA_COPY = DamagedFile(Path("/x/data.json"), Path("/x/data.damaged-20261029-120005.json"))


def test_nothing_is_queued_when_both_files_were_fine():
    app = _App()
    app._tell_about_damaged_files()
    assert app.after_calls == []
    assert app._damaged_notice_after_id is None


def test_each_damaged_file_gets_a_message_settings_first():
    notices = _App(SETTINGS_COPY, DATA_COPY)._damaged_file_notices()
    assert [title for title, _ in notices] == ["Couldn't read your settings", "Couldn't read your transcripts"]


def test_the_message_says_what_happened_and_names_the_copy_on_a_line_of_its_own():
    (_, message), = _App(data_damage=DATA_COPY)._damaged_file_notices()
    assert message.startswith("Your saved transcripts couldn't be read, so the list starts empty.")
    assert message.endswith("\n\ndata.damaged-20261029-120005.json")
    assert "/x" not in message  # just the name: a whole path doesn't fit the box


def test_a_copy_that_failed_is_said_plainly():
    (_, message), = _App(settings_damage=DamagedFile(Path("/x/settings.json"), None))._damaged_file_notices()
    assert message.startswith("Your settings couldn't be read, so the app is using its default settings.")
    assert "will be replaced the next time the app saves" in message


def test_the_message_is_never_shown_straight_away_even_on_a_window_on_screen():
    """The window is already up when __init__ ends, and on Windows it is hidden
    and shown once more when mainloop() starts."""
    app = _App(data_damage=DATA_COPY, viewable=True)
    app._tell_about_damaged_files()
    assert app.shown == []
    assert [(ms, callback.__name__) for ms, callback in app.after_calls] == [(100, "_show_damaged_file_notices")]
    assert app._damaged_notice_after_id == "after#1"


def test_the_message_waits_until_the_window_is_on_screen():
    app = _App(data_damage=DATA_COPY, viewable=False)
    app._show_damaged_file_notices()
    assert app.shown == []
    assert [ms for ms, _ in app.after_calls] == [100]
    assert app._damaged_notice_after_id == "after#1"
    app.viewable = True
    app.after_calls[0][1]()
    assert app.shown == [[("Couldn't read your transcripts", app._damaged_file_notices()[0][1])]]
    assert app._damaged_notice_after_id is None


def test_closing_one_message_opens_the_next(monkeypatch):
    import gui.app as app_module
    from gui.app import RSVPApp

    dialogs = []

    class _Dialog:
        def __init__(self, master, title, message, on_close=None):
            self.title, self.on_close = title, on_close
            dialogs.append(self)

    monkeypatch.setattr(app_module, "MessageDialog", _Dialog)
    app = type("App", (), {"_show_notices": lambda self, n: RSVPApp._show_notices(self, n)})()
    app._show_notices([("First", "one"), ("Second", "two")])
    assert [d.title for d in dialogs] == ["First"]
    dialogs[0].on_close()
    assert [d.title for d in dialogs] == ["First", "Second"]
    dialogs[1].on_close()
    assert len(dialogs) == 2


# ---- the real app ----

_REDIRECT_TARGETS = (
    (storage, "DEFAULT_DATA_DIR"),
    (settings_store, "DEFAULT_DATA_DIR"),
    (settings_store, "SETTINGS_DIR"),
    (transcript_store, "DEFAULT_DATA_DIR"),
)


def _settle(widget, milliseconds=800):
    end = time.monotonic() + milliseconds / 1000
    while time.monotonic() < end:
        widget.update()
        time.sleep(0.005)


def _all_widgets(widget):
    found = [widget]
    for child in widget.winfo_children():
        found.extend(_all_widgets(child))
    return found


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


def test_the_app_starts_with_a_damaged_data_file_and_says_so(tmp_path, monkeypatch, fresh_widget_image_caches):
    import tkinter
    from gui.components.message_dialog import MessageDialog

    for mod, name in _REDIRECT_TARGETS:
        monkeypatch.setattr(mod, name, tmp_path)
    (tmp_path / "data.json").write_bytes(DAMAGED["not text"])
    fresh_widget_image_caches()

    from gui.app import RSVPApp

    try:
        application = RSVPApp()
    except tkinter.TclError as exc:
        pytest.skip(f"Tk can't start a display here: {exc}")
    try:
        _settle(application)
        dialogs = [w for w in application.winfo_children() if isinstance(w, MessageDialog)]
        assert [dialog.title() for dialog in dialogs] == ["Couldn't read your transcripts"]
        assert application.store.transcripts == []
        dialogs[0]._handle_dismiss()
        _settle(application, 300)
    finally:
        _cancel_pending_afters(application)
        application.destroy()
        fresh_widget_image_caches()
    assert len(list(tmp_path.glob("data.damaged-*.json"))) == 1


def test_destroying_the_app_drops_a_message_still_waiting(tmp_path, monkeypatch, fresh_widget_image_caches):
    """A window that never comes on screen never gets the message, and the
    check that keeps waiting for it ends with the window.

    The window says it isn't on screen rather than really being hidden: on
    Linux, destroying an app that was hidden with withdraw() makes the next
    window that takes the keyboard focus crash Tk, in whatever test comes
    next."""
    import tkinter

    for mod, name in _REDIRECT_TARGETS:
        monkeypatch.setattr(mod, name, tmp_path)
    (tmp_path / "data.json").write_bytes(DAMAGED["cut off"])
    fresh_widget_image_caches()

    from gui.app import RSVPApp

    try:
        application = RSVPApp()
    except tkinter.TclError as exc:
        pytest.skip(f"Tk can't start a display here: {exc}")
    application.winfo_viewable = lambda: False
    try:
        _settle(application, 300)
        assert application._damaged_notice_after_id is not None
    finally:
        _cancel_pending_afters(application)
        application.destroy()
        fresh_widget_image_caches()
    assert application._damaged_notice_after_id is None
