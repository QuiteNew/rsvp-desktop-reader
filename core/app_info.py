"""App identity: the name, version and project links shown in the Settings
window's About dialog (gui/components/about_dialog.py).

Pure data, no GUI dependency, which is why it lives in core/ rather than next
to the dialog itself. The GUI just reads these constants and lays them out.

APP_VERSION has no other source of truth. It is not read from a git tag, a
packaging file, or anything else that updates on its own: bump it by hand
here, as the last step before tagging a release, so the number shown inside
the running app always matches the tag the build was cut from."""

APP_NAME = "RSVP Reader"
APP_VERSION = "3.6.0"
REPO_URL = "https://github.com/QuiteNew/rsvp-desktop-reader"
LICENSE_NAME = "MIT"