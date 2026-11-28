"""App identity: the name, version and links shown in the Settings window's
About dialog (gui/components/about_dialog.py).

Pure data, no GUI dependency, which is why it lives in core/ rather than next
to the dialog itself. The GUI just reads these constants and lays them out.

APP_VERSION has no other source of truth. It is not read from a git tag, a
packaging file, or anything else that updates on its own: bump it by hand
here, as the last step before tagging a release, so the number shown inside
the running app always matches the tag the build was cut from.

PRIVACY_URL is the privacy policy page on the docs site, built from
docs/privacy.md. The Microsoft Store asks for the same address when the app is
submitted, so if the docs site ever moves, this and the Store listing both
need the new one."""

APP_NAME = "RSVP Reader"
APP_VERSION = "4.2.0"
REPO_URL = "https://github.com/QuiteNew/rsvp-desktop-reader"
PRIVACY_URL = "https://quitenew.github.io/rsvp-desktop-reader/privacy/"
LICENSE_NAME = "MIT"