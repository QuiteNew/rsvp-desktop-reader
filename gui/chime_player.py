"""Plays the Speaker cues chimes that core/chime.py makes.

On Windows the sound goes through winsound, which comes with Python, so there
is nothing extra to install or bundle. winsound can only play a sound without
holding up the app when the sound is a file on disk (playing from memory
can't be asynchronous), so the chimes are written as WAV files into a folder
of their own in the system's temporary folder, made the first time one is
needed and removed when the app closes.

Making a chime takes a few tens of milliseconds, too long to do at the moment
a new speaker starts without the reader stalling on that word. So prepare()
makes every chime of a style in the background as soon as the style is
known, and play() only plays a chime that is ready. One that isn't ready yet
is skipped rather than waited for: a missed chime is better than a stuck
reader. play(..., wait=True) is for the Settings preview button, where the
person has just asked to hear it and a short wait is fine.

On Linux and macOS there is no sound for now: available is False and nothing
here does anything. The Settings window says so.

Nothing here ever raises. A missing sound device, a full disk or a folder
that can't be made all mean the chime is silent, never that reading stops.

Lives in gui/ rather than core/ because it touches the sound system and the
disk; what the chimes sound like is decided in core/chime.py."""

import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable, Sequence

from core.chime import CHANGE_PATTERN, SPEAKER_PATTERNS, chime_wav


class WinsoundBackend:
    """The Windows sound player: winsound, passed in so tests can hand over a
    stand-in with the same names."""

    def __init__(self, winsound_module):
        self._winsound = winsound_module

    def play(self, path: str) -> None:
        """Start playing a WAV file and return at once. A sound already
        playing is stopped. Never falls back to the system's default sound if
        the file can't be played."""
        w = self._winsound
        w.PlaySound(path, w.SND_FILENAME | w.SND_ASYNC | w.SND_NODEFAULT)

    def stop(self) -> None:
        """Stop whatever this app is playing."""
        self._winsound.PlaySound(None, 0)


def default_backend(platform: str = sys.platform):
    """The sound player for this system, or None where there's none yet
    (everything but Windows)."""
    if platform != "win32":
        return None
    try:
        import winsound
    except ImportError:
        return None
    return WinsoundBackend(winsound)


def chime_file_name(notes: Sequence[float], style: str) -> str:
    """The file name a chime is kept under: its style and its notes, in
    hundredths of a hertz so every note gets a whole number."""
    return f"{style}-" + "-".join(str(round(note * 100)) for note in notes) + ".wav"


class ChimePlayer:
    """Makes the chime files when they're needed, and plays them.

    backend is what actually plays a file (see WinsoundBackend). Leave it out
    to use this system's own, which is None everywhere but Windows. folder is
    where the files go; leave it out to make a new one in the temporary
    folder the first time it's needed. make_folder is how that folder is
    made, and is there so a test can make it fail."""

    def __init__(self, backend=..., folder: str | Path | None = None,
                 make_folder: Callable[[], str] = lambda: tempfile.mkdtemp(prefix="rsvp-reader-chimes-")):
        self._backend = default_backend() if backend is ... else backend
        self._folder = Path(folder) if folder is not None else None
        self._make_folder = make_folder
        self._made_folder = False
        self._closed = False
        self._lock = threading.Lock()
        self._threads: list[threading.Thread] = []

    @property
    def available(self) -> bool:
        """Whether this system can play the chimes at all."""
        return self._backend is not None and not self._closed

    def prepare(self, style: str) -> None:
        """Start making every chime of this style (each speaker's pattern and
        the change chime) in the background, so they're ready by the time
        reading reaches a new speaker. Chimes already made are left as they
        are. Does nothing where chimes can't be played."""
        if not self.available:
            return
        thread = threading.Thread(
            target=self._make_all, args=(style,), name=f"chimes-{style}", daemon=True)
        with self._lock:
            self._threads = [t for t in self._threads if t.is_alive()]
            self._threads.append(thread)
        thread.start()

    def wait_until_prepared(self, timeout: float | None = None) -> None:
        """Wait for chimes being made in the background to be done. Reading
        never needs this; tests and closing the app do."""
        with self._lock:
            threads = list(self._threads)
        for thread in threads:
            thread.join(timeout)

    def is_ready(self, notes: Sequence[float], style: str) -> bool:
        """Whether this chime's file has been made."""
        path = self._path_for(notes, style, make=False)
        return path is not None and path.exists()

    def play(self, notes: Sequence[float], style: str, wait: bool = False) -> bool:
        """Play this chime. True if it started playing.

        If it hasn't been made yet, wait=False (reading) skips it and starts
        making this style in the background for next time, while wait=True
        (the Settings preview) makes it there and then. False whenever
        nothing could be played, never an error."""
        if not self.available:
            return False
        path = self._path_for(notes, style, make=True)
        if path is None:
            return False
        if not path.exists():
            if not wait:
                self.prepare(style)
                return False
            if not self._write(path, notes, style):
                return False
        try:
            self._backend.play(str(path))
        except Exception:
            # A missing or busy sound device, or a file Windows won't play.
            return False
        return True

    def close(self) -> None:
        """Stop any chime, wait for the background work, and remove the
        folder if this player made it. Called when the app closes. Safe to
        call twice; nothing plays afterwards."""
        if self._closed:
            return
        self._closed = True
        if self._backend is not None:
            try:
                self._backend.stop()
            except Exception:
                pass
        self.wait_until_prepared(timeout=5)
        if self._made_folder and self._folder is not None:
            shutil.rmtree(self._folder, ignore_errors=True)

    def _path_for(self, notes: Sequence[float], style: str, make: bool) -> Path | None:
        """Where this chime's file lives, making the folder first if make is
        True and it doesn't exist yet. None if there's no folder and it
        couldn't be made, or make is False."""
        with self._lock:
            if self._folder is None:
                if not make:
                    return None
                try:
                    self._folder = Path(self._make_folder())
                    self._made_folder = True
                except OSError:
                    return None
            return self._folder / chime_file_name(notes, style)

    def _make_all(self, style: str) -> None:
        for notes in SPEAKER_PATTERNS + (CHANGE_PATTERN,):
            if self._closed:
                return
            path = self._path_for(notes, style, make=True)
            if path is None:
                return
            if not path.exists():
                self._write(path, notes, style)

    def _write(self, path: Path, notes: Sequence[float], style: str) -> bool:
        """Make one chime and write it, first under a temporary name and then
        renamed into place, so play() never finds a half-written file. True
        if the file is there afterwards, including when another writer put it
        there first and this one's rename failed (Windows won't replace a
        file that is being played)."""
        try:
            data = chime_wav(notes, style)
            path.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(dir=path.parent, suffix=".part")
            try:
                with os.fdopen(handle, "wb") as file:
                    file.write(data)
                os.replace(temporary, path)
            except BaseException:
                try:
                    os.remove(temporary)
                except OSError:
                    pass
                raise
        except Exception:
            return path.exists()
        return True
