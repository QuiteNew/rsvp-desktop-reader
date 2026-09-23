import time
from dataclasses import asdict

from core.models import Transcript
from core.storage import save_state, load_state, DEFAULT_DATA_DIR, LIVE_SAVE_INTERVAL_SECONDS

DEFAULT_SPACE = "General"


class TranscriptStore:
    """In-memory store for spaces and transcripts, backed by a JSON file
    in a configurable directory."""

    # Floor below which a finished reading session doesn't count toward
    # times_read -- filters out things like opening a transcript and
    # immediately clicking away, without discarding the words/time it did
    # accumulate (see add_session_stats()). A starting guess, like
    # gui/app.py's LARGE_IMPORT_WORD_WARNING_THRESHOLD -- not measured
    # against real usage yet, just long enough to rule out an accidental
    # open-and-leave, short enough not to exclude a genuine brief skim.
    MIN_ACTIVE_SECONDS_TO_COUNT_AS_READ = 3

    def __init__(self, data_directory: str | None = None):
        self._data_directory = data_directory or str(DEFAULT_DATA_DIR)

        loaded = load_state(self._data_directory)
        if loaded:
            self._spaces = loaded["spaces"]
            self._current_space_index = min(loaded["current_space_index"], len(self._spaces) - 1)
            self._transcripts = loaded["transcripts"]
            self._next_id = loaded["next_id"]
        else:
            self._spaces: list[str] = [DEFAULT_SPACE]
            self._current_space_index = 0
            self._transcripts: list[Transcript] = []
            self._next_id = 1

        # 0.0 rather than time.monotonic() at startup -- guarantees the very
        # first throttled write after launch always goes straight through
        # instead of waiting out a throttle window against a startup time
        # it has no real relationship to.
        self._last_live_save = 0.0

    def _save(self) -> None:
        save_state(self._data_directory, self._spaces, self._current_space_index, self._transcripts, self._next_id)

    def set_data_directory(self, directory: str) -> None:
        self._data_directory = directory
        self._save()

    def export_state(self) -> dict:
        """Return this store's full state as a plain dict, in the same
        shape save_state() writes to data.json -- used to build an export
        bundle (see core/data_bundle.py)."""
        return {
            "next_id": self._next_id,
            "current_space_index": self._current_space_index,
            "spaces": list(self._spaces),
            "transcripts": [asdict(t) for t in self._transcripts],
        }

    def replace_all(self, state: dict) -> None:
        """Wholesale-replace every space and transcript with the given
        state (the "data" section of an import bundle -- see
        core/data_bundle.py). state must already be normalized by
        core.storage.parse_data() -- i.e. "transcripts" holds real
        Transcript objects, not dicts. Used for the "Replace" import
        mode."""
        self._spaces = list(state["spaces"]) or [DEFAULT_SPACE]
        self._current_space_index = min(state["current_space_index"], len(self._spaces) - 1)
        self._transcripts = list(state["transcripts"])
        self._next_id = state["next_id"]
        self._save()

    def merge_all(self, state: dict) -> None:
        """Add every space and transcript from the given state (already
        normalized by core.storage.parse_data()) to what's already here,
        instead of replacing it -- used for the "Expand" import mode.

        Spaces are merged by name: any space in the incoming state that
        doesn't already exist locally is appended, in the order it
        appears in state["spaces"]. The current space selection is left
        untouched -- importing shouldn't change what's currently open.

        Incoming transcripts keep every field except id, which is
        reassigned starting from this store's own next_id -- the two
        stores being merged each numbered their transcripts
        independently from 1, so incoming ids can (and typically will)
        collide with ids already in use here. Their "space" field is
        left as-is; it's guaranteed to exist locally as a space name
        after the merge above runs first."""
        for space in state["spaces"]:
            if space not in self._spaces:
                self._spaces.append(space)

        for t in state["transcripts"]:
            t.id = self._next_id
            self._next_id += 1
            self._transcripts.append(t)

        self._save()

    @property
    def spaces(self) -> list[str]:
        return list(self._spaces)

    @property
    def default_space(self) -> str:
        return self._spaces[0]

    @property
    def current_space(self) -> str:
        return self._spaces[self._current_space_index]

    @property
    def transcripts(self) -> list[Transcript]:
        return list(self._transcripts)

    def transcripts_in_space(self, name: str) -> list[Transcript]:
        return [t for t in self._transcripts if t.space == name]

    @property
    def transcripts_in_current_space(self) -> list[Transcript]:
        return self.transcripts_in_space(self.current_space)

    def add_space(self, name: str) -> str:
        name = name.strip()
        if name and name not in self._spaces:
            self._spaces.append(name)
            self._current_space_index = len(self._spaces) - 1
            self._save()
        return self.current_space

    def switch_to_space(self, name: str) -> str:
        if name in self._spaces:
            self._current_space_index = self._spaces.index(name)
            self._save()
        return self.current_space

    def rename_space(self, old_name: str, new_name: str) -> bool:
        """Rename a space, reassigning every transcript currently in it to
        the new name in the same call -- spaces are identified purely by
        their string name (see self._spaces), not a separate stable id,
        so a transcript whose .space field wasn't also updated here would
        silently fall out of the renamed space (transcripts_in_space()
        filters by exact string match).

        Silently rejects (same permissive-on-invalid-input convention as
        add_space()) and returns False if old_name doesn't exist, new_name
        is blank or unchanged, or new_name is already used by a DIFFERENT
        space -- space names must stay unique, same as add_space() already
        enforces for a brand-new space. Returns True only for a rename
        that actually happened, so a caller (see gui/app.py's
        _handle_space_rename_requested() and
        gui/components/space_selection_dialog.py's commit_rename()) can
        tell a genuine rename apart from a rejected one and only update
        its own displayed text for the former -- otherwise the dialog
        could end up showing a name that was never actually applied.

        Renaming the CURRENT space is fine without any extra handling:
        it's renamed in place at the same index, so current_space just
        reads back the new name automatically afterward."""
        new_name = new_name.strip()
        if old_name not in self._spaces:
            return False
        if not new_name or new_name == old_name:
            return False
        if new_name in self._spaces:
            return False
        index = self._spaces.index(old_name)
        self._spaces[index] = new_name
        for t in self._transcripts:
            if t.space == old_name:
                t.space = new_name
        self._save()
        return True

    def delete_space(self, name: str) -> bool:
        """Delete a space by name -- but only if it's empty (no
        transcripts currently assigned to it) and it isn't the only space
        left (there always has to be at least one). Returns whether the
        delete actually happened, so a caller (see gui/app.py's
        _handle_space_delete_requested(), which does its own upfront
        checks and only ever calls this once it already expects True) can
        tell an accepted delete apart from a silently-refused one.

        If the deleted space was the current one, falls back to whichever
        space is now first -- there's nothing special about index 0
        beyond that (default_space is unused outside the tests, per a
        repo-wide check), so "the first remaining space" is just a
        simple, predictable choice, not a protected default. Re-derives
        the new current_space_index from the PREVIOUS current space's
        name (found again after the removal) rather than adjusting the
        old index by hand, so this is correct regardless of whether the
        deleted space came before or after the current one in the list."""
        if name not in self._spaces or len(self._spaces) <= 1:
            return False
        if self.transcripts_in_space(name):
            return False
        current_name = self.current_space
        self._spaces.remove(name)
        if current_name == name:
            self._current_space_index = 0
        else:
            self._current_space_index = self._spaces.index(current_name)
        self._save()
        return True

    def add_transcript(
        self,
        title: str,
        space: str,
        wpm: int = 300,
        font_color: str = "#FFFFFF",
        highlight_color: str = "#E74C3C",
        background_color: str = "#1E1E1E",
        font_size: int = 32,
    ) -> Transcript:
        transcript = Transcript(
            id=self._next_id, title=title, space=space,
            wpm=wpm, font_color=font_color,
            highlight_color=highlight_color, background_color=background_color,
            font_size=font_size,
        )
        self._next_id += 1
        self._transcripts.append(transcript)
        self._save()
        return transcript

    def _find_transcript(self, transcript_id: int) -> Transcript | None:
        for t in self._transcripts:
            if t.id == transcript_id:
                return t
        return None

    def set_transcript_title(self, transcript_id: int, title: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.title = title
            self._save()

    def set_transcript_text(self, transcript_id: int, raw_text: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.raw_text = raw_text
            self._save()

    def set_transcript_position(self, transcript_id: int, position: int) -> None:
        """Update the transcript's position and persist it -- but the disk
        write itself is throttled (see LIVE_SAVE_INTERVAL_SECONDS in
        core/storage.py), since this is called on every word during
        playback. The in-memory value is always current regardless; call
        flush() to force an immediate write of whatever's still pending."""
        t = self._find_transcript(transcript_id)
        if t:
            t.position = position
            self._save_throttled()

    def _save_throttled(self) -> None:
        now = time.monotonic()
        if now - self._last_live_save >= LIVE_SAVE_INTERVAL_SECONDS:
            self._last_live_save = now
            self._save()

    def flush(self) -> None:
        """Force an immediate save, bypassing the live-update throttle.
        Every OTHER setter in this class already calls _save() directly
        and unconditionally (pause, stop, skip's pause-toggle, colors,
        etc.), so those already double as safe checkpoints for whatever
        position/WPM was last recorded in memory -- this is only needed to
        guarantee a throttled-but-not-yet-written update actually reaches
        disk when nothing else is going to save afterward. Called from
        gui/app.py on app close."""
        self._last_live_save = time.monotonic()
        self._save()

    def set_transcript_paused(self, transcript_id: int, is_paused: bool) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.is_paused = is_paused
            self._save()

    def set_transcript_wpm(self, transcript_id: int, wpm: int) -> None:
        """Update the transcript's WPM and persist it -- throttled the same
        way set_transcript_position() is, since this is the footer WPM
        slider's live drag callback and can fire dozens of times across a
        single drag. This is currently WPM's only caller, so no separate
        discrete/unthrottled variant is needed the way skip_word_count
        needed one in SettingsStore (see set_skip_word_count_live() there)."""
        t = self._find_transcript(transcript_id)
        if t:
            t.wpm = wpm
            self._save_throttled()

    def set_transcript_font_color(self, transcript_id: int, color: str) -> None:
        # Called only from the footer's own color picker -- a genuine
        # manual change, so it retires this transcript's font color from
        # theme-tracking. Only clears the flag if the color actually
        # changed, so re-picking the same color twice doesn't accidentally
        # freeze it (see resync_default_reading_colors()).
        t = self._find_transcript(transcript_id)
        if t:
            if color != t.font_color:
                t.font_color_is_default = False
            t.font_color = color
            self._save()

    def set_transcript_highlight_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            if color != t.highlight_color:
                t.highlight_color_is_default = False
            t.highlight_color = color
            self._save()

    def set_transcript_background_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            if color != t.background_color:
                t.background_color_is_default = False
            t.background_color = color
            self._save()

    def resync_default_reading_colors(self, font_color: str, highlight_color: str, background_color: str) -> None:
        """Update every transcript whose reading colors are still tracking
        the app-wide default (font_color_is_default etc. -- see
        core/models.py) to the given values, leaving any transcript with
        its own deliberately-picked color untouched. Called once at app
        startup (see gui/app.py) with whichever color set matches the
        CURRENT theme -- the same "takes effect on next launch" timing the
        rest of the theme system already uses, not a live update."""
        changed = False
        for t in self._transcripts:
            if t.font_color_is_default and t.font_color != font_color:
                t.font_color = font_color
                changed = True
            if t.highlight_color_is_default and t.highlight_color != highlight_color:
                t.highlight_color = highlight_color
                changed = True
            if t.background_color_is_default and t.background_color != background_color:
                t.background_color = background_color
                changed = True
        if changed:
            self._save()

    def set_transcript_font_size(self, transcript_id: int, font_size: int) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.font_size = font_size
            self._save()

    def set_transcript_draft_text(self, transcript_id: int, draft_text: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.draft_text = draft_text
            self._save()

    def set_transcript_stopped(self, transcript_id: int, is_stopped: bool) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.is_stopped = is_stopped
            self._save()

    def add_session_stats(self, transcript_id: int, words_read: int, active_seconds: float) -> None:
        """Roll one finished reading session's numbers into this
        transcript's running totals -- called once a session actually
        ends (stopped, finished, switched away from, or the app closing
        mid-read; see gui/components/reader_display.py's
        finalize_session()), never for a session still in progress.

        times_read only increments if active_seconds clears
        MIN_ACTIVE_SECONDS_TO_COUNT_AS_READ -- otherwise opening a
        transcript and immediately clicking away would count as a read.
        words_read and active_seconds are still added to the running
        totals regardless of that floor: a few seconds of real reading
        still happened even if it's short of counting as a whole "time
        read," so the totals themselves never silently drop numbers the
        floor was never meant to touch.

        words_read of 0 is a normal, expected call (e.g. a session ended
        without ever advancing past the first word) -- nothing special
        happens for it beyond times_read's own floor check above."""
        t = self._find_transcript(transcript_id)
        if t is None:
            return
        if active_seconds >= self.MIN_ACTIVE_SECONDS_TO_COUNT_AS_READ:
            t.times_read += 1
        t.total_words_read += words_read
        t.total_time_spent_seconds += round(active_seconds)
        self._save()

    def delete_transcript(self, transcript_id: int) -> None:
        self._transcripts = [t for t in self._transcripts if t.id != transcript_id]
        self._save()