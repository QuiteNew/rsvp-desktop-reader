"""Tests for gui/chime_player.py: making the chime files in the background,
playing them, staying silent where there's no sound, never raising, and
cleaning up.

Nothing here makes a real sound. The player is given a stand-in that records
what it was asked to play, and the Windows layer is checked against a
stand-in winsound module with the same names. The real sound is checked by
hand on Windows."""

import os
import threading
from types import SimpleNamespace

import pytest

from core.chime import CHANGE_PATTERN, CHIME_STYLES, SPEAKER_PATTERNS, chime_wav
from gui import chime_player
from gui.chime_player import ChimePlayer, WinsoundBackend, chime_file_name, default_backend

ALL_PATTERNS = SPEAKER_PATTERNS + (CHANGE_PATTERN,)


class FakeBackend:
    """Records what it was asked to play and stop, and can be told to fail
    the way a missing sound device does."""

    def __init__(self, fail=False):
        self.played = []
        self.stopped = 0
        self.fail = fail

    def play(self, path):
        # Every attempt is recorded, the way the real winsound would be
        # called, with the file's bytes at that moment (None if it isn't
        # there), so a test can see the file was whole when it was played.
        data = None
        if os.path.exists(path):
            with open(path, "rb") as file:
                data = file.read()
        self.played.append((path, data))
        if self.fail:
            raise RuntimeError("no sound device")

    def stop(self):
        self.stopped += 1


@pytest.fixture
def backend():
    return FakeBackend()


@pytest.fixture
def player(backend, tmp_path):
    p = ChimePlayer(backend=backend, folder=tmp_path / "chimes")
    yield p
    p.close()


def _wav_files(folder):
    return sorted(name for name in os.listdir(folder) if name.endswith(".wav")) if folder.exists() else []


# ---- File names ----

def test_a_file_name_holds_the_style_and_the_notes():
    assert chime_file_name((523.25,), "bell") == "bell-52325.wav"
    assert chime_file_name((523.25, 783.99), "glass") == "glass-52325-78399.wav"

def test_every_chime_of_every_style_has_its_own_file_name():
    names = {chime_file_name(notes, style) for style in CHIME_STYLES for notes in ALL_PATTERNS}
    assert len(names) == len(CHIME_STYLES) * len(ALL_PATTERNS) == 24


# ---- Making the files ----

@pytest.mark.parametrize("style", CHIME_STYLES)
def test_prepare_makes_every_chime_of_a_style(player, tmp_path, style):
    player.prepare(style)
    player.wait_until_prepared()
    folder = tmp_path / "chimes"
    assert _wav_files(folder) == sorted(chime_file_name(notes, style) for notes in ALL_PATTERNS)
    for notes in ALL_PATTERNS:
        assert (folder / chime_file_name(notes, style)).read_bytes() == chime_wav(notes, style)
        assert player.is_ready(notes, style)

def test_prepare_works_in_the_background(tmp_path, backend):
    # The work happens on another thread, so prepare() returns before the
    # files are made. A gate holds the background thread until the test says.
    gate = threading.Event()
    real = chime_player.chime_wav

    def slow_chime_wav(*args, **kwargs):
        gate.wait(5)
        return real(*args, **kwargs)

    player = ChimePlayer(backend=backend, folder=tmp_path / "chimes")
    chime_player.chime_wav, saved = slow_chime_wav, chime_player.chime_wav
    try:
        player.prepare("bell")
        assert not player.is_ready(SPEAKER_PATTERNS[0], "bell")
        gate.set()
        player.wait_until_prepared()
        assert player.is_ready(SPEAKER_PATTERNS[0], "bell")
    finally:
        chime_player.chime_wav = saved
        player.close()

def test_preparing_twice_leaves_the_files_alone(player, tmp_path):
    player.prepare("bell")
    player.wait_until_prepared()
    folder = tmp_path / "chimes"
    times = {name: os.stat(folder / name).st_mtime_ns for name in _wav_files(folder)}
    player.prepare("bell")
    player.wait_until_prepared()
    assert {name: os.stat(folder / name).st_mtime_ns for name in _wav_files(folder)} == times

def test_two_styles_live_side_by_side(player, tmp_path):
    player.prepare("bell")
    player.prepare("wood")
    player.wait_until_prepared()
    assert len(_wav_files(tmp_path / "chimes")) == 12

def test_no_half_written_files_are_left_behind(player, tmp_path):
    player.prepare("glass")
    player.wait_until_prepared()
    assert [name for name in os.listdir(tmp_path / "chimes") if not name.endswith(".wav")] == []

def test_nothing_is_ready_before_anything_is_made(backend):
    made = []
    player = ChimePlayer(backend=backend, make_folder=lambda: made.append(1) or "x")
    assert not player.is_ready(SPEAKER_PATTERNS[0], "bell")
    # Asking doesn't make the folder.
    assert made == []


# ---- Playing ----

def test_a_ready_chime_plays_its_own_file(player, backend, tmp_path):
    player.prepare("bell")
    player.wait_until_prepared()
    assert player.play(SPEAKER_PATTERNS[1], "bell")
    path, data = backend.played[-1]
    assert path == str(tmp_path / "chimes" / chime_file_name(SPEAKER_PATTERNS[1], "bell"))
    assert data == chime_wav(SPEAKER_PATTERNS[1], "bell")

def test_a_chime_that_is_not_ready_is_skipped_and_made_for_next_time(player, backend):
    assert not player.play(SPEAKER_PATTERNS[0], "soft")
    assert backend.played == []
    player.wait_until_prepared()
    assert player.is_ready(SPEAKER_PATTERNS[0], "soft")
    assert player.is_ready(CHANGE_PATTERN, "soft")
    assert player.play(SPEAKER_PATTERNS[0], "soft")

def test_the_preview_makes_the_chime_there_and_then(player, backend):
    assert player.play(SPEAKER_PATTERNS[4], "glass", wait=True)
    assert backend.played[-1][1] == chime_wav(SPEAKER_PATTERNS[4], "glass")

def test_a_missing_sound_device_means_silence_not_an_error(tmp_path):
    backend = FakeBackend(fail=True)
    player = ChimePlayer(backend=backend, folder=tmp_path / "chimes")
    try:
        assert not player.play(CHANGE_PATTERN, "bell", wait=True)
        assert len(backend.played) == 1  # it was tried
    finally:
        player.close()

def test_a_chime_that_cannot_be_made_means_silence_not_an_error(player, backend):
    # A note too high for a file to hold: core/chime.py refuses it.
    assert not player.play((30000.0,), "bell", wait=True)
    assert backend.played == []

def test_a_folder_that_cannot_be_written_means_silence_not_an_error(tmp_path, backend):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("a file where the folder should be")
    player = ChimePlayer(backend=backend, folder=blocker)
    try:
        assert not player.play(CHANGE_PATTERN, "bell", wait=True)
        player.prepare("bell")
        player.wait_until_prepared()
        assert not player.play(CHANGE_PATTERN, "bell")
        assert backend.played == []
    finally:
        player.close()

def test_a_folder_that_cannot_be_made_means_silence_not_an_error(backend):
    def refuse():
        raise OSError("no room")
    player = ChimePlayer(backend=backend, make_folder=refuse)
    try:
        assert not player.play(CHANGE_PATTERN, "bell", wait=True)
        player.prepare("bell")
        player.wait_until_prepared()
        assert not player.is_ready(CHANGE_PATTERN, "bell")
        assert backend.played == []
    finally:
        player.close()

def test_a_file_another_writer_put_in_place_first_still_counts(player, tmp_path, monkeypatch):
    # Windows won't rename over a file that's being played, so a second
    # writer can fail after the first already succeeded. That's still a
    # chime ready to play.
    folder = tmp_path / "chimes"
    folder.mkdir()
    target = folder / chime_file_name(CHANGE_PATTERN, "bell")
    target.write_bytes(chime_wav(CHANGE_PATTERN, "bell"))

    def refuse(*args):
        raise PermissionError("in use")
    monkeypatch.setattr(chime_player.os, "replace", refuse)
    assert player._write(target, CHANGE_PATTERN, "bell")
    assert [name for name in os.listdir(folder) if not name.endswith(".wav")] == []

def test_a_failed_write_with_nothing_in_place_is_a_failure(player, tmp_path, monkeypatch):
    def refuse(*args):
        raise PermissionError("in use")
    monkeypatch.setattr(chime_player.os, "replace", refuse)
    target = tmp_path / "chimes" / chime_file_name(CHANGE_PATTERN, "bell")
    assert not player._write(target, CHANGE_PATTERN, "bell")
    assert [name for name in os.listdir(tmp_path / "chimes")] == []


# ---- No sound on this system ----

def test_without_a_backend_nothing_is_available(tmp_path):
    player = ChimePlayer(backend=None, folder=tmp_path / "chimes")
    assert not player.available
    assert not player.play(CHANGE_PATTERN, "bell", wait=True)
    player.prepare("bell")
    player.wait_until_prepared()
    assert not (tmp_path / "chimes").exists()
    player.close()

def test_without_a_backend_no_folder_is_ever_made():
    made = []
    player = ChimePlayer(backend=None, make_folder=lambda: made.append(1) or "x")
    player.prepare("bell")
    player.play(CHANGE_PATTERN, "bell", wait=True)
    player.close()
    assert made == []


# ---- Closing ----

def test_closing_stops_the_sound_and_removes_a_folder_it_made(tmp_path, backend):
    folder = tmp_path / "made-by-the-player"
    player = ChimePlayer(backend=backend, make_folder=lambda: (folder.mkdir(), str(folder))[1])
    player.prepare("bell")
    player.wait_until_prepared()
    assert folder.exists()
    player.close()
    assert backend.stopped == 1
    assert not folder.exists()

def test_closing_leaves_a_folder_it_was_given(player, backend, tmp_path):
    player.prepare("bell")
    player.wait_until_prepared()
    player.close()
    assert (tmp_path / "chimes").exists()

def test_nothing_plays_after_closing(player, backend):
    player.prepare("bell")
    player.wait_until_prepared()
    player.close()
    assert not player.available
    assert not player.play(CHANGE_PATTERN, "bell")
    assert backend.played == []

def test_closing_twice_is_harmless(player, backend):
    player.close()
    player.close()
    assert backend.stopped == 1

def test_a_sound_device_that_fails_to_stop_does_not_stop_the_closing(tmp_path):
    class StopFails(FakeBackend):
        def stop(self):
            raise RuntimeError("no sound device")
    folder = tmp_path / "made"
    player = ChimePlayer(backend=StopFails(), make_folder=lambda: (folder.mkdir(), str(folder))[1])
    player.play(CHANGE_PATTERN, "bell", wait=True)
    player.close()
    assert not folder.exists()

def test_closing_waits_for_the_background_work_and_stops_it(tmp_path, backend, monkeypatch):
    # The background thread is held at a gate inside its first chime, so the
    # test knows exactly where it is when close() is called.
    gate = threading.Event()
    started = threading.Event()
    made = []
    real = chime_player.chime_wav

    def held_chime_wav(*args, **kwargs):
        made.append(args)
        started.set()
        gate.wait(5)
        return real(*args, **kwargs)

    monkeypatch.setattr(chime_player, "chime_wav", held_chime_wav)
    folder = tmp_path / "made"
    player = ChimePlayer(backend=backend, make_folder=lambda: (folder.mkdir(), str(folder))[1])
    player.prepare("glass")
    assert started.wait(5)
    closing = threading.Thread(target=player.close)
    closing.start()
    closing.join(0.3)
    assert closing.is_alive(), "close() waits for the chime being made"
    gate.set()
    closing.join(5)
    assert not closing.is_alive()
    # Only the chime already under way was made; the rest were dropped.
    assert len(made) == 1
    # And the folder is gone, with nothing written into it afterwards.
    assert not folder.exists()

def test_the_folder_is_made_in_the_temporary_folder_by_default(backend):
    player = ChimePlayer(backend=backend)
    try:
        assert player.play(CHANGE_PATTERN, "bell", wait=True)
        path = backend.played[-1][0]
        assert os.path.basename(os.path.dirname(path)).startswith("rsvp-reader-chimes-")
        assert os.path.exists(path)
    finally:
        player.close()
    assert not os.path.exists(path)


# ---- The Windows layer ----

def _fake_winsound():
    calls = []
    return SimpleNamespace(
        SND_FILENAME=0x20000, SND_ASYNC=0x1, SND_NODEFAULT=0x2,
        PlaySound=lambda sound, flags: calls.append((sound, flags)),
        calls=calls,
    )

def test_windows_plays_a_file_without_waiting_and_never_the_default_sound():
    fake = _fake_winsound()
    WinsoundBackend(fake).play("C:\\chimes\\bell-44000.wav")
    assert fake.calls == [("C:\\chimes\\bell-44000.wav", 0x20000 | 0x1 | 0x2)]

def test_windows_stops_with_no_sound():
    fake = _fake_winsound()
    WinsoundBackend(fake).stop()
    assert fake.calls == [(None, 0)]

@pytest.mark.parametrize("platform", ["linux", "darwin", "cygwin"])
def test_no_backend_outside_windows(platform, monkeypatch):
    # Even with a winsound module around, only Windows uses it.
    monkeypatch.setitem(__import__("sys").modules, "winsound", _fake_winsound())
    assert default_backend(platform) is None

def test_windows_gets_winsound(monkeypatch):
    fake = _fake_winsound()
    monkeypatch.setitem(__import__("sys").modules, "winsound", fake)
    backend = default_backend("win32")
    assert isinstance(backend, WinsoundBackend)
    backend.play("x.wav")
    assert fake.calls == [("x.wav", 0x20000 | 0x1 | 0x2)]

def test_windows_without_winsound_has_no_backend(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "winsound", None)
    assert default_backend("win32") is None

def test_the_default_player_uses_this_systems_backend(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(chime_player, "default_backend", lambda: sentinel)
    player = ChimePlayer()
    assert player.available
    assert player._backend is sentinel
