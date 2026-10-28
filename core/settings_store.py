import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict, field, fields

from core.letter_spacing import MAX_LEVEL
from core.profiles import Profile, ProfileError, clean_name, clean_profile_list, name_problem, sanitize_values
from core.storage import DEFAULT_DATA_DIR, LIVE_SAVE_INTERVAL_SECONDS

SETTINGS_DIR = DEFAULT_DATA_DIR

WINDOW_WIDTH_RANGE = (500, 2000)
WINDOW_HEIGHT_RANGE = (400, 1400)
SIDEBAR_WIDTH_RANGE = (120, 500)
BOTTOM_BAND_HEIGHT_RANGE = (80, 400)
WPM_RANGE = (100, 1000)
SKIP_WORD_COUNT_RANGE = (1, 50)
FONT_SIZE_RANGE = (16, 96)
FONT_SIZE_STEP_RANGE = (1, 10)
HIGHLIGHT_OFFSET_RANGE = (-3, 3)
GUIDE_MARK_THICKNESS_RANGE = (2, 6)  # 1px is deliberately excluded: a 1px-thick CTkFrame
                                      # doesn't render a visible fill in this app, the same
                                      # rendering quirk that hid the horizontal guide lines,
                                      # so allowing 1 here would let a user silently make the
                                      # vertical marks disappear too.
GUIDE_MARK_LENGTH_PERCENT_RANGE = (15, 60)
RESUME_REWIND_WORDS_RANGE = (1, 5)
CHUNK_SIZE_RANGE = (2, 5)  # words flashed together in fixed chunking mode. 1 is excluded
                            # because "off" is the chunking toggle's job, not size 1.
CHUNK_CHAR_TARGET_RANGE = (15, 60)  # adaptive chunking width, in characters (the words plus the
                                     # single spaces between them). It drives adaptive mode the way
                                     # CHUNK_SIZE_RANGE drives fixed mode.
LETTER_SPACING_LEVEL_RANGE = (0, MAX_LEVEL)  # 0 is Off. The top level comes from core/letter_spacing.py, which
                                              # holds the gap size for every level, so the two can't drift apart.

@dataclass
class AppSettings:
    window_width: int = 1000
    window_height: int = 650
    sidebar_width: int = 220
    bottom_band_height: int = 100
    default_wpm: int = 300
    default_font_color: str = "#3B2E27"
    default_highlight_color: str = "#D98A3D"
    default_background_color: str = "#F6EFE3"
    default_font_size: int = 32
    default_chunking_enabled: bool = False  # new-transcript default for multi-word chunking; seeded
                                             # onto Transcript.chunking_enabled at creation.
    default_chunk_size: int = 2  # new-transcript default for Transcript.chunk_size, the number of words
                                  # flashed together in fixed chunking mode. See CHUNK_SIZE_RANGE (2 to 5).
    default_chunk_mode: str = "fixed"  # new-transcript default for Transcript.chunk_mode: "fixed" groups
                                        # chunk_size words, "adaptive" fills each chunk up to
                                        # default_chunk_char_target characters instead.
    default_chunk_char_target: int = 30  # new-transcript default for Transcript.chunk_char_target, the
                                          # adaptive-mode width. See CHUNK_CHAR_TARGET_RANGE (15 to 60).
    font_size_step: int = 1
    highlight_offset_px: int = 0  # global, not per-transcript: positive is up, negative is down
    data_directory: str = field(default_factory=lambda: str(DEFAULT_DATA_DIR))
    freeform_resize_enabled: bool = False
    skip_word_count: int = 10
    pause_on_skip: bool = False
    length_pacing_enabled: bool = False  # global, not per-transcript. See core/reader.py's
                                          # ReaderSession.length_pacing_enabled: slows down long
                                          # words by length band, independent of punctuation pacing.
    appearance_mode: str = "light"
    guide_mark_horizontal_enabled: bool = False  # global, not per-transcript: fixed-style crosshair ticks, on/off only
    guide_mark_thickness_px: int = 2  # global, not per-transcript: width of the vertical guide marks
    guide_mark_length_percent: int = 35  # global, not per-transcript: length as % of current word size
    guide_mark_color: str = "#3B2E27"  # global, not per-transcript: no longer follows the transcript's font colour
    guide_mark_color_is_default: bool = True  # whether guide_mark_color is still tracking the app-wide Light/Dark
                                               # default, or something picked by hand in Settings. See
                                               # SettingsStore.set_guide_mark_color() and resync_guide_mark_color_default().
    split_long_paragraphs_enabled: bool = False  # global, not per-transcript: whether the Normalize button also breaks a
                                                  # long wall of prose into paragraphs at sentence ends. Off by default.
                                                  # See core/normalizer.py's normalize_transcript(split_long_paragraphs=...).
    resume_rewind_enabled: bool = False  # global, not per-transcript: when resuming from a pause, step back a few words
                                          # first for re-entry context. Off by default. See ReaderDisplay.toggle_pause().
    resume_rewind_words: int = 3  # how many words to step back on resume when resume_rewind_enabled is on.
                                   # See RESUME_REWIND_WORDS_RANGE for the allowed range.
    warm_up_enabled: bool = False  # global, not per-transcript: ease in at the start of a reading session,
                                    # ramping from half speed up to the target rate over the first words.
                                    # Off by default. See core/timing.py's warm_up_multiplier().
    scrub_pause_enabled: bool = True  # global, not per-transcript: when on, releasing the progress scrubber
                                       # pauses reading on the word it landed on. On by default. When off,
                                       # reading keeps its prior play state after a scrub (resumes if it was
                                       # playing, stays paused otherwise). See ReaderDisplay.scrub_end().
    peripheral_context_enabled: bool = False  # global, not per-transcript: show a dim line of the surrounding
                                               # words (previous and upcoming) below the focal word, so
                                               # peripheral vision keeps the thread of the sentence. Off by
                                               # default. See gui/components/reader_display.py's
                                               # set_peripheral_context().
    dyslexia_font_enabled: bool = False  # global, not per-transcript: switch every font in the app to OpenDyslexic.
                                          # Off by default. Read once at startup by gui/theme.py, so a change
                                          # takes effect on the next launch, the same as the Light/Dark theme.
    letter_spacing_level: int = 0  # global, not per-transcript: extra room between the letters of the flashing
                                    # word. 0 is Off, up to the top of LETTER_SPACING_LEVEL_RANGE. What each level
                                    # means is in core/letter_spacing.py. Applies live, no restart.
    bold_starts_enabled: bool = False  # global, not per-transcript: draw the start of every word in the edit box in bold.
                                       # Off by default. It is only a look: it never changes the text, and it is not
                                       # part of a reading profile. See core/bold_starts.py.
    reopen_last_transcript: bool = True  # global: at launch, open the transcript that was open when the app was
                                         # last closed. On by default. Not part of a reading profile.
    last_transcript_id: int | None = None  # the transcript open in the reader, kept up to date by the app so the
                                           # one above can find it at the next launch. None when nothing is open.
                                           # Not shown in Settings.
    profiles: list = field(default_factory=list)  # saved reading profiles, each a plain dict with a "name" and a
                                                   # "values" dict (see core/profiles.py). Kept as dicts so
                                                   # they go to settings.json and into export bundles as they
                                                   # are. Use SettingsStore's profile methods, not this list.

# The names of AppSettings' own fields, used by _known_settings() below.
_SETTINGS_FIELDS = {f.name for f in fields(AppSettings)}


def _known_settings(data: dict) -> dict:
    """Keep only the keys AppSettings has a field for.

    A settings dict can carry a key this version does not know: a setting
    added by a newer version of the app (someone going back to an older
    release, or importing a bundle exported by a newer one), a field that was
    removed long ago like header_height, or a typo from editing the file by
    hand. Passing one to AppSettings() raises a TypeError, which used to make
    the whole load fall back to the defaults, and the next change then saved
    those defaults over the real file. Dropping the key instead keeps every
    other setting."""
    return {key: value for key, value in data.items() if key in _SETTINGS_FIELDS}


class SettingsStore:
    """Persists app-level settings to their own file, separate from
    transcript/space data."""

    def __init__(self, settings_directory: str | None = None):
        self._settings_dir = Path(settings_directory) if settings_directory else SETTINGS_DIR
        self._settings_file = self._settings_dir / "settings.json"
        self._settings = self._load()
        # 0.0 rather than time.monotonic() at startup. See the matching
        # comment on TranscriptStore._last_live_save.
        self._last_live_save = 0.0

    def _load(self) -> AppSettings:
        if not self._settings_file.exists():
            return AppSettings()
        try:
            data = json.loads(self._settings_file.read_text(encoding="utf-8"))
            # Valid JSON that is not an object (a list, null, a bare number)
            # cannot be settings, so start from the defaults.
            if not isinstance(data, dict):
                return AppSettings()
            # guide_mark_color predates guide_mark_color_is_default. For an
            # old settings.json missing the flag, infer it from whether the
            # stored color still equals the one-and-only historical default
            # ("#3B2E27"). If so, treat it as still-default, which the
            # resync below will fix; if the user had already changed it to
            # something else, treat it as already customized and frozen.
            if "guide_mark_color_is_default" not in data:
                data["guide_mark_color_is_default"] = (
                    data.get("guide_mark_color", AppSettings.guide_mark_color) == AppSettings.guide_mark_color
                )
            # Clean the saved profiles instead of trusting them. A bad entry
            # is dropped on its own, so one damaged profile can't make the
            # whole load fail and reset every other setting to its default.
            data["profiles"] = clean_profile_list(data.get("profiles"))
            return AppSettings(**_known_settings(data))
        except (json.JSONDecodeError, KeyError, TypeError):
            return AppSettings()

    def _save(self) -> None:
        self._settings_dir.mkdir(exist_ok=True, parents=True)
        self._settings_file.write_text(json.dumps(asdict(self._settings), indent=2), encoding="utf-8")

    def _save_throttled(self) -> None:
        now = time.monotonic()
        if now - self._last_live_save >= LIVE_SAVE_INTERVAL_SECONDS:
            self._last_live_save = now
            self._save()

    def flush(self) -> None:
        """Force an immediate save, bypassing the live-update throttle. See
        TranscriptStore.flush() for the full reasoning. Called from
        gui/app.py on app close, to catch a throttled-but-not-yet-written
        skip_word_count change from set_skip_word_count_live()."""
        self._last_live_save = time.monotonic()
        self._save()

    def export_settings(self) -> dict:
        """Return every setting except data_directory as a plain dict, used
        to build an export bundle (see core/data_bundle.py). data_directory
        is excluded deliberately, since it's a raw OS-specific filesystem
        path that's meaningless, or actively wrong, on a different machine,
        so it must never travel inside a bundle. See replace_from_bundle()."""
        data = asdict(self._settings)
        data.pop("data_directory")
        return data

    def replace_from_bundle(self, settings: dict) -> None:
        """Replace every setting with the given dict, the "settings" section
        of an import bundle as export_settings() produces it (see
        core/data_bundle.py), except data_directory, which always stays
        whatever this machine already has configured. Used for the "Replace"
        import mode. There's no "Expand"/merge equivalent for settings,
        since they're scalar preferences like a single WPM default or window
        size, not a collection, so there's nothing sensible to merge.
        "Expand" imports leave settings untouched entirely.

        Profiles are the one exception to "replace everything". A bundle
        that carries a "profiles" list replaces this machine's profiles like
        any other setting. A bundle exported before profiles existed has no
        such key, and for that one the profiles already on this machine are
        kept, so importing an old backup doesn't wipe them out.

        A key this version does not know is dropped, so a bundle exported by
        a newer version still imports. See _known_settings()."""
        merged = {**settings, "data_directory": self._settings.data_directory}
        if "profiles" in settings:
            merged["profiles"] = clean_profile_list(settings["profiles"])
        else:
            merged["profiles"] = self._settings.profiles
        self._settings = AppSettings(**_known_settings(merged))
        self._save()

    @property
    def window_width(self) -> int:
        return self._settings.window_width

    @property
    def window_height(self) -> int:
        return self._settings.window_height

    @property
    def sidebar_width(self) -> int:
        return self._settings.sidebar_width

    @property
    def bottom_band_height(self) -> int:
        return self._settings.bottom_band_height

    @property
    def default_wpm(self) -> int:
        return self._settings.default_wpm

    @property
    def default_font_color(self) -> str:
        return self._settings.default_font_color

    @property
    def default_highlight_color(self) -> str:
        return self._settings.default_highlight_color

    @property
    def default_background_color(self) -> str:
        return self._settings.default_background_color

    @property
    def default_font_size(self) -> int:
        return self._settings.default_font_size

    @property
    def default_chunking_enabled(self) -> bool:
        return self._settings.default_chunking_enabled

    @property
    def default_chunk_size(self) -> int:
        return self._settings.default_chunk_size

    @property
    def default_chunk_mode(self) -> str:
        return self._settings.default_chunk_mode

    @property
    def default_chunk_char_target(self) -> int:
        return self._settings.default_chunk_char_target

    @property
    def font_size_step(self) -> int:
        return self._settings.font_size_step

    @property
    def highlight_offset_px(self) -> int:
        return self._settings.highlight_offset_px

    @property
    def data_directory(self) -> str:
        return self._settings.data_directory

    @property
    def freeform_resize_enabled(self) -> bool:
        return self._settings.freeform_resize_enabled

    @property
    def skip_word_count(self) -> int:
        return self._settings.skip_word_count

    @property
    def pause_on_skip(self) -> bool:
        return self._settings.pause_on_skip

    @property
    def length_pacing_enabled(self) -> bool:
        return self._settings.length_pacing_enabled

    @property
    def appearance_mode(self) -> str:
        return self._settings.appearance_mode

    @property
    def guide_mark_horizontal_enabled(self) -> bool:
        return self._settings.guide_mark_horizontal_enabled

    @property
    def guide_mark_thickness_px(self) -> int:
        return self._settings.guide_mark_thickness_px

    @property
    def guide_mark_length_percent(self) -> int:
        return self._settings.guide_mark_length_percent

    @property
    def guide_mark_color(self) -> str:
        return self._settings.guide_mark_color

    @property
    def guide_mark_color_is_default(self) -> bool:
        """Whether guide_mark_color is still following the Light/Dark theme
        (True), or was picked by hand (False). A reading profile needs this
        to know what to store for the guide-mark colour."""
        return self._settings.guide_mark_color_is_default

    @property
    def split_long_paragraphs_enabled(self) -> bool:
        return self._settings.split_long_paragraphs_enabled

    @property
    def resume_rewind_enabled(self) -> bool:
        return self._settings.resume_rewind_enabled

    @property
    def resume_rewind_words(self) -> int:
        return self._settings.resume_rewind_words

    @property
    def warm_up_enabled(self) -> bool:
        return self._settings.warm_up_enabled

    @property
    def scrub_pause_enabled(self) -> bool:
        return self._settings.scrub_pause_enabled

    @property
    def peripheral_context_enabled(self) -> bool:
        return self._settings.peripheral_context_enabled

    @property
    def dyslexia_font_enabled(self) -> bool:
        return self._settings.dyslexia_font_enabled

    @property
    def letter_spacing_level(self) -> int:
        return self._settings.letter_spacing_level

    @property
    def bold_starts_enabled(self) -> bool:
        # Strictly True, so a settings file with something odd in this spot
        # ("false" as text, a 1) reads as off, the same care core/font_choice.py
        # takes with the font switch.
        return self._settings.bold_starts_enabled is True

    @property
    def reopen_last_transcript(self) -> bool:
        # On unless it is strictly False, since on is the default: a settings
        # file with something odd in this spot keeps the default.
        return self._settings.reopen_last_transcript is not False

    @property
    def last_transcript_id(self) -> int | None:
        # Only a real whole number is an id. Anything else in the file (text,
        # true/false, a fraction) reads as no transcript.
        value = self._settings.last_transcript_id
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return None

    def set_window_size(self, width: int, height: int) -> None:
        self._settings.window_width = width
        self._settings.window_height = height
        self._save()

    def set_layout_sizes(self, sidebar_width: int, bottom_band_height: int) -> None:
        self._settings.sidebar_width = sidebar_width
        self._settings.bottom_band_height = bottom_band_height
        self._save()

    def set_defaults(self, wpm: int, font_color: str, highlight_color: str, background_color: str, font_size: int) -> None:
        self._settings.default_wpm = wpm
        self._settings.default_font_color = font_color
        self._settings.default_highlight_color = highlight_color
        self._settings.default_background_color = background_color
        self._settings.default_font_size = font_size
        self._save()

    def set_chunking_defaults(
        self, enabled: bool, size: int,
        mode: str | None = None, char_target: int | None = None,
    ) -> None:
        """Set the new-transcript chunking defaults, seeded onto a transcript's
        chunking_enabled / chunk_size / chunk_mode / chunk_char_target at
        creation; changing them never touches transcripts that already exist.

        enabled and size always apply. mode and char_target are optional and
        keep their current stored value when left None, so a caller that only
        has the toggle and the fixed size (an older two-argument call) leaves
        the default mode and adaptive width alone, while a caller that has all
        four passes them all."""
        self._settings.default_chunking_enabled = enabled
        self._settings.default_chunk_size = size
        if mode is not None:
            self._settings.default_chunk_mode = mode
        if char_target is not None:
            self._settings.default_chunk_char_target = char_target
        self._save()

    def set_font_size_step(self, step: int) -> None:
        self._settings.font_size_step = step
        self._save()

    def set_highlight_offset_px(self, offset: int) -> None:
        self._settings.highlight_offset_px = offset
        self._save()

    def set_data_directory(self, directory: str) -> None:
        self._settings.data_directory = directory
        self._save()

    def set_freeform_resize_enabled(self, enabled: bool) -> None:
        self._settings.freeform_resize_enabled = enabled
        self._save()

    def set_skip_behavior(self, word_count: int, pause_on_skip: bool) -> None:
        """Used by Settings' Apply button and the pause_on_skip switch, both
        discrete, one-shot actions, so this always saves immediately. The
        skip-amount slider's own live drag callback goes through
        set_skip_word_count_live() instead, which is throttled; see there
        for why the two need to be kept separate."""
        self._settings.skip_word_count = word_count
        self._settings.pause_on_skip = pause_on_skip
        self._save()

    def set_skip_word_count_live(self, word_count: int) -> None:
        """Same field as set_skip_behavior(), but for the Settings skip-
        amount slider's live drag callback specifically, which can fire many
        times across a single drag. Throttled the same way TranscriptStore
        throttles position and WPM writes (see LIVE_SAVE_INTERVAL_SECONDS in
        core/storage.py). Kept as a separate method rather than throttling
        set_skip_behavior() itself, since that one is also called from the
        Apply button and the pause_on_skip switch, both discrete actions
        that must always save immediately, and throttling it there could
        delay a switch toggle behind an unrelated slider drag from moments
        earlier."""
        self._settings.skip_word_count = word_count
        self._save_throttled()

    def set_length_pacing_enabled(self, enabled: bool) -> None:
        self._settings.length_pacing_enabled = enabled
        self._save()

    def set_split_long_paragraphs_enabled(self, enabled: bool) -> None:
        self._settings.split_long_paragraphs_enabled = enabled
        self._save()

    def set_resume_rewind(self, enabled: bool, words: int) -> None:
        """Set both resume-rewind fields together, since Settings' Apply
        submits them as a pair (the toggle plus its word count)."""
        self._settings.resume_rewind_enabled = enabled
        self._settings.resume_rewind_words = words
        self._save()

    def set_warm_up_enabled(self, enabled: bool) -> None:
        self._settings.warm_up_enabled = enabled
        self._save()

    def set_scrub_pause_enabled(self, enabled: bool) -> None:
        self._settings.scrub_pause_enabled = enabled
        self._save()

    def set_peripheral_context_enabled(self, enabled: bool) -> None:
        self._settings.peripheral_context_enabled = enabled
        self._save()

    def set_dyslexia_font_enabled(self, enabled: bool) -> None:
        self._settings.dyslexia_font_enabled = enabled
        self._save()

    def set_letter_spacing_level(self, level: int) -> None:
        self._settings.letter_spacing_level = level
        self._save()

    def set_bold_starts_enabled(self, enabled: bool) -> None:
        self._settings.bold_starts_enabled = enabled
        self._save()

    def set_reopen_last_transcript(self, enabled: bool) -> None:
        self._settings.reopen_last_transcript = enabled
        self._save()

    def set_last_transcript_id(self, transcript_id: int | None) -> None:
        """Remember which transcript is open, or None for none. Opening the
        same transcript again doesn't write the file again."""
        if self._settings.last_transcript_id == transcript_id:
            return
        self._settings.last_transcript_id = transcript_id
        self._save()

    def set_appearance_mode(self, mode: str) -> None:
        self._settings.appearance_mode = mode
        self._save()

    def set_guide_mark_horizontal_enabled(self, enabled: bool) -> None:
        self._settings.guide_mark_horizontal_enabled = enabled
        self._save()

    def set_guide_mark_thickness_px(self, thickness_px: int) -> None:
        self._settings.guide_mark_thickness_px = thickness_px
        self._save()

    def set_guide_mark_length_percent(self, percent: int) -> None:
        self._settings.guide_mark_length_percent = percent
        self._save()

    def set_guide_mark_color(self, color: str) -> None:
        # Called only from Settings' own color picker, a genuine manual
        # change, so it retires guide_mark_color from theme-tracking.
        # Only clears the flag if the color actually changed, so
        # re-applying the same color twice doesn't accidentally freeze
        # it (see resync_guide_mark_color_default()).
        if color != self._settings.guide_mark_color:
            self._settings.guide_mark_color_is_default = False
        self._settings.guide_mark_color = color
        self._save()

    def restore_guide_mark_color(self, color: str, follows_theme: bool) -> None:
        """Set guide_mark_color and whether it follows the theme in one go,
        for putting back a colour that was recorded earlier (a reading
        profile). set_guide_mark_color() can't do this: it only ever turns
        following off, and only when the colour actually changes. A profile
        has to be able to turn following back on, and to mark a colour as
        picked by hand even when it happens to match the current one."""
        self._settings.guide_mark_color = color
        self._settings.guide_mark_color_is_default = follows_theme
        self._save()

    def resync_guide_mark_color_default(self, color: str) -> None:
        """Update guide_mark_color to the given value only if it's still
        tracking the app-wide theme default (guide_mark_color_is_default, see
        AppSettings). Called once at app startup with whichever color
        matches the current theme, the same "takes effect on next launch"
        timing as TranscriptStore.resync_default_reading_colors()."""
        if self._settings.guide_mark_color_is_default and self._settings.guide_mark_color != color:
            self._settings.guide_mark_color = color
            self._save()

    # ---- Reading profiles ----
    # The saved profiles live in AppSettings.profiles as plain dicts. These
    # methods are the only way in or out. Each change saves straight away,
    # like the other discrete actions here, and any problem with a name or a
    # missing profile raises ProfileError with a message that is fine to show
    # the user as it is. Names are matched without regard to case.

    @property
    def profiles(self) -> list[Profile]:
        """Every saved profile, in the order they were added. These are
        copies, so changing one doesn't touch what is stored."""
        return [Profile(item["name"], dict(item["values"])) for item in self._settings.profiles]

    def get_profile(self, name: str) -> Profile | None:
        """The profile with this name, or None when there isn't one."""
        index = self._profile_index(name)
        if index is None:
            return None
        item = self._settings.profiles[index]
        return Profile(item["name"], dict(item["values"]))

    def add_profile(self, name: str, values: dict) -> Profile:
        """Save a new profile. The name is tidied up first and has to be free
        (see core/profiles.py's name_problem()). Entries in values that a
        profile can't hold are dropped, see sanitize_values()."""
        problem = name_problem(name, self._profile_names())
        if problem:
            raise ProfileError(problem)
        profile = Profile(clean_name(name), sanitize_values(values))
        self._settings.profiles.append(profile.to_dict())
        self._save()
        return profile

    def update_profile(self, name: str, values: dict) -> Profile:
        """Replace the settings held by an existing profile, keeping its name
        and its place in the list."""
        index = self._require_profile(name)
        profile = Profile(self._settings.profiles[index]["name"], sanitize_values(values))
        self._settings.profiles[index] = profile.to_dict()
        self._save()
        return profile

    def rename_profile(self, name: str, new_name: str) -> Profile:
        """Give an existing profile a new name. Changing only the capitals of
        its own name is fine."""
        index = self._require_profile(name)
        current = self._settings.profiles[index]["name"]
        problem = name_problem(new_name, self._profile_names(), own_name=current)
        if problem:
            raise ProfileError(problem)
        profile = Profile(clean_name(new_name), dict(self._settings.profiles[index]["values"]))
        self._settings.profiles[index] = profile.to_dict()
        self._save()
        return profile

    def delete_profile(self, name: str) -> None:
        index = self._require_profile(name)
        del self._settings.profiles[index]
        self._save()

    def _profile_names(self) -> list[str]:
        return [item["name"] for item in self._settings.profiles]

    def _profile_index(self, name: str) -> int | None:
        wanted = clean_name(name).casefold()
        if not wanted:
            return None
        for index, item in enumerate(self._settings.profiles):
            if item["name"].casefold() == wanted:
                return index
        return None

    def _require_profile(self, name: str) -> int:
        index = self._profile_index(name)
        if index is None:
            raise ProfileError(f'There is no profile called "{name}".')
        return index