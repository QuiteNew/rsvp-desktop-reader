import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict, field

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
GUIDE_MARK_THICKNESS_RANGE = (2, 6)  # 1px is deliberately excluded -- confirmed that a 1px-thick
                                      # CTkFrame doesn't render a visible fill in this app (the
                                      # same rendering quirk that was hiding the horizontal guide
                                      # lines), so allowing 1 here would let a user silently make
                                      # the vertical marks disappear too.
GUIDE_MARK_LENGTH_PERCENT_RANGE = (15, 60)

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
    font_size_step: int = 1
    highlight_offset_px: int = 0  # global, not per-transcript — positive = up, negative = down
    data_directory: str = field(default_factory=lambda: str(DEFAULT_DATA_DIR))
    freeform_resize_enabled: bool = False
    skip_word_count: int = 10
    pause_on_skip: bool = False
    appearance_mode: str = "light"
    guide_mark_horizontal_enabled: bool = False  # global, not per-transcript — fixed-style crosshair ticks, on/off only
    guide_mark_thickness_px: int = 2  # global, not per-transcript — width of the vertical guide marks
    guide_mark_length_percent: int = 35  # global, not per-transcript — length as % of current word size
    guide_mark_color: str = "#3B2E27"  # global, not per-transcript — no longer follows the transcript's font colour
    guide_mark_color_is_default: bool = True  # whether guide_mark_color is still tracking the app-wide Light/Dark
                                               # default rather than something picked by hand in Settings -- see
                                               # SettingsStore.set_guide_mark_color() / resync_guide_mark_color_default()

class SettingsStore:
    """Persists app-level settings to their own file, separate from
    transcript/space data."""

    def __init__(self, settings_directory: str | None = None):
        self._settings_dir = Path(settings_directory) if settings_directory else SETTINGS_DIR
        self._settings_file = self._settings_dir / "settings.json"
        self._settings = self._load()
        # 0.0 rather than time.monotonic() at startup -- see the matching
        # comment on TranscriptStore._last_live_save.
        self._last_live_save = 0.0

    def _load(self) -> AppSettings:
        if not self._settings_file.exists():
            return AppSettings()
        try:
            data = json.loads(self._settings_file.read_text(encoding="utf-8"))
            data.pop("header_height", None)
            # guide_mark_color predates guide_mark_color_is_default. For an
            # old settings.json missing the flag, infer it from whether the
            # stored color still equals the one-and-only historical default
            # ("#3B2E27") -- if so, treat it as still-default (will be fixed
            # by the resync below); if the user had already changed it to
            # something else, treat it as already-customized (frozen).
            if "guide_mark_color_is_default" not in data:
                data["guide_mark_color_is_default"] = (
                    data.get("guide_mark_color", AppSettings.guide_mark_color) == AppSettings.guide_mark_color
                )
            return AppSettings(**data)
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
        """Force an immediate save, bypassing the live-update throttle --
        see TranscriptStore.flush() for the full reasoning. Called from
        gui/app.py on app close, to catch a throttled-but-not-yet-written
        skip_word_count change from set_skip_word_count_live()."""
        self._last_live_save = time.monotonic()
        self._save()

    def export_settings(self) -> dict:
        """Return every setting except data_directory as a plain dict --
        used to build an export bundle (see core/data_bundle.py).
        Excluded deliberately: data_directory is a raw OS-specific
        filesystem path, meaningless (or actively wrong) on a different
        machine, so it must never travel inside a bundle -- see
        replace_from_bundle()."""
        data = asdict(self._settings)
        data.pop("data_directory")
        return data

    def replace_from_bundle(self, settings: dict) -> None:
        """Replace every setting with the given dict (the "settings"
        section of an import bundle, as export_settings() produces it --
        see core/data_bundle.py), except data_directory, which always
        stays whatever this machine already has configured. Used for the
        "Replace" import mode; there's no "Expand"/merge equivalent for
        settings -- they're scalar preferences (a single WPM default, a
        single window size), not a collection, so there's nothing
        sensible to merge. "Expand" imports leave settings untouched
        entirely."""
        merged = {**settings, "data_directory": self._settings.data_directory}
        self._settings = AppSettings(**merged)
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
        """Used by Settings' Apply button and the pause_on_skip switch --
        both discrete, one-shot actions, so this always saves immediately.
        The skip-amount slider's own live drag callback goes through
        set_skip_word_count_live() instead, which is throttled; see there
        for why the two need to be kept separate."""
        self._settings.skip_word_count = word_count
        self._settings.pause_on_skip = pause_on_skip
        self._save()

    def set_skip_word_count_live(self, word_count: int) -> None:
        """Same field as set_skip_behavior(), but for the Settings skip-
        amount slider's live drag callback specifically, which can fire
        many times across a single drag -- throttled the same way
        TranscriptStore throttles position/WPM writes (see
        LIVE_SAVE_INTERVAL_SECONDS in core/storage.py). Deliberately a
        separate method rather than throttling set_skip_behavior() itself,
        since that one is also called from the Apply button and the
        pause_on_skip switch, both discrete actions that must always save
        immediately -- throttling it there could delay a switch toggle
        behind an unrelated slider drag that happened moments earlier."""
        self._settings.skip_word_count = word_count
        self._save_throttled()

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
        # Called only from Settings' own color picker -- a genuine manual
        # change, so it retires guide_mark_color from theme-tracking. Only
        # clears the flag if the color actually changed, so re-applying the
        # same color twice doesn't accidentally freeze it (see
        # resync_guide_mark_color_default()).
        if color != self._settings.guide_mark_color:
            self._settings.guide_mark_color_is_default = False
        self._settings.guide_mark_color = color
        self._save()

    def resync_guide_mark_color_default(self, color: str) -> None:
        """Update guide_mark_color to the given value only if it's still
        tracking the app-wide theme default (guide_mark_color_is_default --
        see AppSettings). Called once at app startup with whichever color
        matches the CURRENT theme -- the same "takes effect on next launch"
        timing as TranscriptStore.resync_default_reading_colors()."""
        if self._settings.guide_mark_color_is_default and self._settings.guide_mark_color != color:
            self._settings.guide_mark_color = color
            self._save()