import json
from pathlib import Path
from dataclasses import dataclass, asdict, field

from core.storage import DEFAULT_DATA_DIR

SETTINGS_DIR = DEFAULT_DATA_DIR

WINDOW_WIDTH_RANGE = (500, 2000)
WINDOW_HEIGHT_RANGE = (400, 1400)
SIDEBAR_WIDTH_RANGE = (120, 500)
BOTTOM_BAND_HEIGHT_RANGE = (80, 400)
WPM_RANGE = (100, 1000)
SKIP_WORD_COUNT_RANGE = (1, 50)
FONT_SIZE_RANGE = (16, 96)
FONT_SIZE_STEP_RANGE = (1, 10)


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
    data_directory: str = field(default_factory=lambda: str(DEFAULT_DATA_DIR))
    freeform_resize_enabled: bool = False
    skip_word_count: int = 10
    pause_on_skip: bool = False
    appearance_mode: str = "light"


class SettingsStore:
    """Persists app-level settings to their own file, separate from
    transcript/space data."""

    def __init__(self, settings_directory: str | None = None):
        self._settings_dir = Path(settings_directory) if settings_directory else SETTINGS_DIR
        self._settings_file = self._settings_dir / "settings.json"
        self._settings = self._load()

    def _load(self) -> AppSettings:
        if not self._settings_file.exists():
            return AppSettings()
        try:
            data = json.loads(self._settings_file.read_text(encoding="utf-8"))
            data.pop("header_height", None)
            return AppSettings(**data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return AppSettings()

    def _save(self) -> None:
        self._settings_dir.mkdir(exist_ok=True, parents=True)
        self._settings_file.write_text(json.dumps(asdict(self._settings), indent=2), encoding="utf-8")

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

    def set_data_directory(self, directory: str) -> None:
        self._settings.data_directory = directory
        self._save()

    def set_freeform_resize_enabled(self, enabled: bool) -> None:
        self._settings.freeform_resize_enabled = enabled
        self._save()

    def set_skip_behavior(self, word_count: int, pause_on_skip: bool) -> None:
        self._settings.skip_word_count = word_count
        self._settings.pause_on_skip = pause_on_skip
        self._save()

    def set_appearance_mode(self, mode: str) -> None:
        self._settings.appearance_mode = mode
        self._save()