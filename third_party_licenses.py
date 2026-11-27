"""Which licence texts go into the built app, and where each one comes from.

The app ships other people's code: Python itself, the packages in
requirements.txt that it imports, and a few fonts. Their licences say their
text has to go along with every copy, so a release build has to carry them,
not just the source repository.

Most of the texts are copied at build time from the packages installed on the
build machine, so they always match the versions actually being shipped, even
after Dependabot moves one on. The one text kept in the repository is the
Apache licence for the Roboto fonts that CustomTkinter brings along, because
CustomTkinter doesn't ship it.

RSVPReader.spec calls bundle_datas() to add everything to the build, and
tests/test_third_party_licenses.py checks the lists here against what is
really installed. Nothing in the running app imports this file, which is why
it sits next to the spec rather than in core/.

When a new package is added to requirements.txt and the app imports it, it
goes in BUNDLED_PACKAGES, and THIRD_PARTY_NOTICES.md gets a line for it. The
test fails until both are done."""

import re
import sys
import sysconfig
from importlib.metadata import distribution
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Every installed package PyInstaller puts into the build, by the name pip
# knows it by. Found by building the app and reading the packages in
# build/RSVPReader/Analysis-00.toc: the ones the app imports itself, and the
# ones those pull in.
BUNDLED_PACKAGES = (
    "customtkinter",
    "darkdetect",
    "packaging",
    "pillow",
    "pypdf",
    "python-docx",
    "lxml",
    "typing_extensions",
    "cryptography",
    "cffi",
)

# Packages one of the above asks for that never end up in the build, and why.
# Listed so the test can tell "left out on purpose" from "forgotten".
NOT_BUNDLED = {
    "pycparser": "cffi only uses it to read C declarations when something is "
                 "compiled against cffi, never while the app is running",
}

# Where the texts go inside the build, next to the app's own files.
LICENSES_FOLDER = "licenses"

# A licence file inside a package's .dist-info folder: LICENSE, LICENCE,
# COPYING or NOTICE, with or without an ending such as .txt or .APACHE.
_LICENCE_FILE_NAME = re.compile(r"^(licen[cs]e|copying|notice)", re.IGNORECASE)


def licence_files(package: str) -> list[Path]:
    """The licence files an installed package came with, from its .dist-info
    folder, in a fixed order. Empty if it came with none."""
    found = []
    for file in distribution(package).files or ():
        if file.parts and file.parts[0].endswith(".dist-info") and _LICENCE_FILE_NAME.match(file.name):
            found.append(Path(file.locate()))
    return sorted(found)


def python_licence_file() -> Path | None:
    """Python's own LICENSE.txt, or None if this Python doesn't have one.

    The Windows installer from python.org puts it in the install folder, and
    on Windows it also holds the licences of what Python brings with it: the
    Microsoft C runtime, bzip2, libffi, OpenSSL, Tcl and Tk. Python built from
    source, as the setup-python action does on Linux and macOS, puts it in the
    standard library folder. Some Linux distributions remove it, which is
    why this can come back empty."""
    for folder in (Path(sys.base_prefix), Path(sysconfig.get_path("stdlib"))):
        candidate = folder / "LICENSE.txt"
        if candidate.is_file():
            return candidate
    return None


def bundle_datas() -> list[tuple[str, str]]:
    """Every licence file for the build, as the (source, folder in the build)
    pairs PyInstaller's datas list takes. Raises if a text can't be found, so
    a build can never quietly go out without one."""
    datas = [
        (str(ROOT / "LICENSE"), "."),
        (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
        (str(ROOT / LICENSES_FOLDER), LICENSES_FOLDER),
    ]
    for package in BUNDLED_PACKAGES:
        files = licence_files(package)
        if not files:
            raise RuntimeError(f"{package} is installed without a licence file, so its text can't go in the build")
        datas += [(str(file), f"{LICENSES_FOLDER}/{package}") for file in files]

    python_licence = python_licence_file()
    if python_licence is None:
        raise RuntimeError(
            "This Python has no LICENSE.txt to put in the build. Build with Python "
            "from python.org, or the setup-python action, which both include it."
        )
    datas.append((str(python_licence), f"{LICENSES_FOLDER}/python"))
    return datas