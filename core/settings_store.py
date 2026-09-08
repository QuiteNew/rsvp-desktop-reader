import json
from pathlib import Path
from dataclasses import dataclass, asdict

SETTINGS_DIR = Path.home() / ".rsvp_reader"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULT_WIDTH = 1000
DEFAULT_HEIGHT = 650


@dataclass
class AppSettings:
    window_width: int = DEFAULT_WIDTH
    window_height: int = DEFAULT_HEIGHT


class SettingsStore:
    """Persists app-level settings (currently just window size) to their
    own file — a different concern from transcript/space data, so it gets
    its own small store rather than being folded into TranscriptStore."""

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

    def set_window_size(self, width: int, height: int) -> None:
        self._settings.window_width = width
        self._settings.window_height = height
        self._save()