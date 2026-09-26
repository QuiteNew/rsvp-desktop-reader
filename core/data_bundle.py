"""Building and applying cross-machine export/import bundles.

A bundle is a single JSON file holding everything TranscriptStore and
SettingsStore know about: transcripts, spaces, and app settings,
except SettingsStore's data_directory, which is a raw OS-specific
filesystem path and would be meaningless, or actively wrong, on a
different machine or platform. Imported data always lands in whatever
directory the importing machine already has configured; see
SettingsStore.replace_from_bundle() and TranscriptStore.replace_all()/
merge_all(), which enforce that at the one place each store's own
persistence is decided.

This module has no GUI dependency (see core/ vs gui/ in the project
brief). gui/components/settings_window.py collects the file path and
the user's Replace/Expand/Cancel choice; gui/app.py calls the
functions here, then closes the app, since an import always requires
a restart. The rest of the running UI, the sidebar list, space
selector, current transcript, and window layout, has no live-reload
path back to a bundle's contents.
"""

import json

from core.settings_store import SettingsStore
from core.storage import parse_data
from core.transcript_store import TranscriptStore

BUNDLE_FORMAT_VERSION = 1


class BundleFormatError(Exception):
    """Raised when a file being imported isn't a valid RSVP Reader export
    bundle: malformed JSON, missing sections, or a bundle_format this
    version of the app doesn't understand. The message is meant to be
    shown to the user as-is."""


def build_bundle(transcript_store: TranscriptStore, settings_store: SettingsStore) -> dict:
    """Assemble an export bundle from the two stores' current state.
    Returns a plain dict; gui/ is responsible for json.dumps()-ing it and
    writing it to the file the user chose."""
    return {
        "bundle_format": BUNDLE_FORMAT_VERSION,
        "data": transcript_store.export_state(),
        "settings": settings_store.export_settings(),
    }


def parse_bundle(json_text: str) -> dict:
    """Parse and validate a bundle file's text. Returns a dict with
    normalized "data" (ready for TranscriptStore.replace_all()/
    merge_all()) and raw "settings" (ready for
    SettingsStore.replace_from_bundle()). Raises BundleFormatError, with
    a message safe to show the user directly, if the file isn't a valid
    bundle this version of the app can read."""
    try:
        raw = json.loads(json_text)
    except json.JSONDecodeError:
        raise BundleFormatError("That file isn't valid JSON, so it can't be an RSVP Reader export.")

    if not isinstance(raw, dict) or "bundle_format" not in raw:
        raise BundleFormatError("That file doesn't look like an RSVP Reader export bundle.")

    version = raw["bundle_format"]
    if version != BUNDLE_FORMAT_VERSION:
        raise BundleFormatError(
            f"This bundle was made by a different version of RSVP Reader (format {version}, "
            f"this app reads format {BUNDLE_FORMAT_VERSION}) and can't be imported here."
        )

    if not isinstance(raw.get("data"), dict) or not isinstance(raw.get("settings"), dict):
        raise BundleFormatError("That file is missing data this app expects in an export bundle.")

    data = parse_data(raw["data"])
    if data is None:
        raise BundleFormatError("The transcript data in that file is malformed and can't be imported.")

    return {"data": data, "settings": raw["settings"]}


def apply_bundle_replace(bundle: dict, transcript_store: TranscriptStore, settings_store: SettingsStore) -> None:
    """Wipe out everything currently stored and replace it wholesale with
    the bundle's contents. The importing machine's own data_directory is
    always kept. See the module docstring."""
    transcript_store.replace_all(bundle["data"])
    settings_store.replace_from_bundle(bundle["settings"])


def apply_bundle_expand(bundle: dict, transcript_store: TranscriptStore) -> None:
    """Add the bundle's spaces and transcripts to what's already stored,
    instead of replacing it. Settings are deliberately left untouched.
    See TranscriptStore.merge_all() and SettingsStore.replace_from_bundle()
    for the reasoning behind each choice."""
    transcript_store.merge_all(bundle["data"])