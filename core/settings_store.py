import json
from pathlib import Path
from dataclasses import dataclass, asdict, field

from core.storage import DEFAULT_DATA_DIR

SETTINGS_DIR = DEFAULT_DATA_DIR
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# Shared validation/slider ranges — imported by both SettingsWindow (typed
# field validation, slider bounds) and the main app window (clamping live
# free-form drag resizing), so both enforcement points can never drift
# out of sync with each other.
WINDOW_WIDTH_RANGE = (500, 2000)
WINDOW_HEIGHT_RANGE = (400, 1400)
SIDEBAR_WIDTH_RANGE = (120, 500)
HEADER_HEIGHT_RANGE = (30, 120)
BOTTOM_BAND_HEIGHT_RANGE = (80, 400)
WPM_RANGE = (100, 1000)


@dataclass
class AppSettings:
    window_width: int = 1000
    window_height: int = 650
    sidebar_width: int = 220
    header_height: int = 50
    bottom_band_height: int = 150
    default_wpm: int = 300
    default_font_color: str = "#FFFFFF"
    default_highlight_color: str = "#E74C3C"
    default_background_color: str = "#1E1E1E"
    data_directory: str = field(default_factory=lambda: str(DEFAULT_DATA_DIR))
    freeform_resize_enabled: bool = False


class SettingsStore:
    """Persists app-level settings — window/layout sizes, new-transcript
    defaults, the transcript data folder, and the free-form resize
    preference — to their own file, separate from transcript/space data."""

    def __init__(self):
        self._settings = self._load()

    def _load(self) -> AppSettings:
        if not SETTINGS_FILE.exists():
            return AppSettings()
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return AppSettings(**data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return AppSettings()

    def _save(self) -> None:
        SETTINGS_DIR.mkdir(exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(asdict(self._settings), indent=2), encoding="utf-8")

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
    def header_height(self) -> int:
        return self._settings.header_height

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
    def data_directory(self) -> str:
        return self._settings.data_directory

    @property
    def freeform_resize_enabled(self) -> bool:
        return self._settings.freeform_resize_enabled

    def set_window_size(self, width: int, height: int) -> None:
        self._settings.window_width = width
        self._settings.window_height = height
        self._save()

    def set_layout_sizes(self, sidebar_width: int, header_height: int, bottom_band_height: int) -> None:
        self._settings.sidebar_width = sidebar_width
        self._settings.header_height = header_height
        self._settings.bottom_band_height = bottom_band_height
        self._save()

    def set_defaults(self, wpm: int, font_color: str, highlight_color: str, background_color: str) -> None:
        self._settings.default_wpm = wpm
        self._settings.default_font_color = font_color
        self._settings.default_highlight_color = highlight_color
        self._settings.default_background_color = background_color
        self._save()

    def set_data_directory(self, directory: str) -> None:
        self._settings.data_directory = directory
        self._save()

    def set_freeform_resize_enabled(self, enabled: bool) -> None:
        self._settings.freeform_resize_enabled = enabled
        self._save()