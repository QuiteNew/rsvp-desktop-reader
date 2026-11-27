"""Tests for third_party_licenses.py and THIRD_PARTY_NOTICES.md.

The build copies a licence text into the app for every package it ships, and
the risk is the list quietly falling behind: a new import in the app, a new
dependency pulled in by Dependabot, or a package that stops shipping its
licence file. Each of those should fail here, on the next test run, rather
than produce a release that's missing a text.

What the build really bundles was found by building the app and reading
PyInstaller's list. These tests can't build the app, so they check the same
thing from the other end: every package the app's own code imports, and
everything those packages ask for in turn, has to be either in
BUNDLED_PACKAGES or explained in NOT_BUNDLED."""

import ast
import re
import sys
from importlib.metadata import distribution, packages_distributions
from pathlib import Path

import pytest
from packaging.requirements import Requirement

import third_party_licenses as licences

ROOT = Path(__file__).resolve().parent.parent
NOTICES = ROOT / "THIRD_PARTY_NOTICES.md"
ROBOTO_LICENCE = ROOT / licences.LICENSES_FOLDER / "Roboto-Apache-2.0.txt"


def _canonical(name: str) -> str:
    """A package name the way pip compares them: Pillow, pillow and
    python_docx, python-docx are the same package."""
    return re.sub(r"[-_.]+", "-", name).lower()


BUNDLED = {_canonical(name) for name in licences.BUNDLED_PACKAGES}
LEFT_OUT = {_canonical(name) for name in licences.NOT_BUNDLED}


def _imported_top_level_names() -> set[str]:
    """Every top-level module name the app's own code imports, anywhere in
    core/, gui/ and main.py, including imports inside functions."""
    files = [ROOT / "main.py", *(ROOT / "core").rglob("*.py"), *(ROOT / "gui").rglob("*.py")]
    names = set()
    for file in files:
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


def _requirements_of(package: str) -> set[str]:
    """What an installed package asks pip for on this machine and Python,
    leaving out optional extras."""
    needed = set()
    for line in distribution(package).requires or ():
        requirement = Requirement(line)
        if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
            needed.add(_canonical(requirement.name))
    return needed


# ---- The lists themselves ----

def test_no_package_is_both_bundled_and_left_out():
    assert not BUNDLED & LEFT_OUT


def test_every_left_out_package_says_why():
    for package, reason in licences.NOT_BUNDLED.items():
        assert reason.strip(), f"{package} needs a reason for being left out"


@pytest.mark.parametrize("package", licences.BUNDLED_PACKAGES)
def test_every_bundled_package_is_installed_with_a_licence_file(package):
    files = licences.licence_files(package)
    assert files, f"{package} has no licence file in its .dist-info folder"
    for file in files:
        assert file.is_file()
        assert file.read_text(encoding="utf-8", errors="replace").strip()


# ---- Nothing the app ships is missing from the list ----

def test_every_package_the_app_imports_is_bundled():
    owners = packages_distributions()
    missing = set()
    for name in _imported_top_level_names():
        if name in sys.stdlib_module_names or name in ("core", "gui", "main"):
            continue
        for package in owners.get(name, []):
            if _canonical(package) not in BUNDLED:
                missing.add(package)
    assert not missing, (
        f"The app imports {sorted(missing)}, which aren't in BUNDLED_PACKAGES in "
        f"third_party_licenses.py, so the build wouldn't carry their licence"
    )


def test_everything_the_bundled_packages_need_is_bundled_or_explained():
    unaccounted = {}
    for package in licences.BUNDLED_PACKAGES:
        for needed in _requirements_of(package) - BUNDLED - LEFT_OUT:
            unaccounted.setdefault(needed, []).append(package)
    assert not unaccounted, (
        f"These are needed by bundled packages but are neither in BUNDLED_PACKAGES "
        f"nor in NOT_BUNDLED: {unaccounted}"
    )


# ---- What the build gets ----

def test_python_has_a_licence_file_to_ship():
    licence = licences.python_licence_file()
    assert licence is not None, "this Python has no LICENSE.txt, so a build would stop"
    assert "PYTHON SOFTWARE FOUNDATION LICENSE" in licence.read_text(encoding="utf-8", errors="replace")


@pytest.mark.skipif(sys.platform != "win32", reason="only Python's Windows installer adds the other licences to this file")
def test_pythons_windows_licence_file_covers_what_python_brings_with_it():
    """THIRD_PARTY_NOTICES.md says this file also covers the Microsoft
    runtime, bzip2, libffi, OpenSSL, Tcl and Tk. Not every text carries its
    name, so each one is found by a line it's known to have. Line breaks are
    flattened first, because a phrase can wrap across two lines."""
    text = " ".join(licences.python_licence_file().read_text(encoding="utf-8", errors="replace").split())
    assert "Microsoft Distributable Code" in text
    assert "Julian R Seward" in text, "bzip2"
    assert "libffi - Copyright" in text
    assert "Apache License Version 2.0, January 2004" in text, "OpenSSL"
    assert text.count("copyrighted by the Regents of the University of California") >= 2, "Tcl and Tk"


def test_every_file_the_build_gets_is_really_there():
    datas = licences.bundle_datas()
    for source, _folder in datas:
        assert Path(source).exists(), source
    folders = {folder for _source, folder in datas}
    assert "." in folders
    assert f"{licences.LICENSES_FOLDER}/python" in folders
    for package in licences.BUNDLED_PACKAGES:
        assert f"{licences.LICENSES_FOLDER}/{package}" in folders


def test_the_build_stops_when_a_package_has_no_licence_file(monkeypatch):
    monkeypatch.setattr(licences, "licence_files", lambda package: [])
    with pytest.raises(RuntimeError, match="without a licence file"):
        licences.bundle_datas()


def test_the_build_stops_when_python_has_no_licence_file(monkeypatch):
    monkeypatch.setattr(licences, "python_licence_file", lambda: None)
    with pytest.raises(RuntimeError, match="no LICENSE.txt"):
        licences.bundle_datas()


def test_the_app_licence_and_the_notices_go_in_the_build():
    sources = {Path(source).name for source, folder in licences.bundle_datas() if folder == "."}
    assert sources == {"LICENSE", "THIRD_PARTY_NOTICES.md"}


def test_the_spec_adds_the_licences_to_the_build():
    spec = (ROOT / "RSVPReader.spec").read_text(encoding="utf-8")
    assert "from third_party_licenses import bundle_datas" in spec
    assert "datas += bundle_datas()" in spec


# ---- Roboto, the one text kept in the repository ----

def test_the_roboto_licence_is_the_apache_licence():
    text = ROBOTO_LICENCE.read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "END OF TERMS AND CONDITIONS" in text


def test_the_roboto_fonts_customtkinter_ships_still_say_apache():
    """The Roboto licence is kept here because CustomTkinter ships the fonts
    without it. If a new CustomTkinter swaps the fonts or their licence, this
    notice needs another look. Fonts store their licence line as plain text
    or as UTF-16, so both are searched for."""
    import customtkinter

    fonts = sorted((Path(customtkinter.__file__).parent / "assets" / "fonts" / "Roboto").glob("*.ttf"))
    assert fonts, "CustomTkinter no longer ships Roboto, so the notice about it is out of date"
    phrase = "Licensed under the Apache License, Version 2.0"
    for font in fonts:
        data = font.read_bytes()
        assert phrase.encode("ascii") in data or phrase.encode("utf-16-be") in data, font.name


# ---- The notices page ----

def test_the_notices_page_names_every_bundled_package():
    text = NOTICES.read_text(encoding="utf-8")
    for package in licences.BUNDLED_PACKAGES:
        assert f"`{licences.LICENSES_FOLDER}/{package}/`" in text, f"{package} is missing from THIRD_PARTY_NOTICES.md"
    assert f"`{licences.LICENSES_FOLDER}/python/LICENSE.txt`" in text
    assert f"`{licences.LICENSES_FOLDER}/{ROBOTO_LICENCE.name}`" in text


def test_the_notices_page_points_at_font_licences_that_exist():
    text = NOTICES.read_text(encoding="utf-8")
    for path in re.findall(r"`(assets/fonts/[^`]+)`", text):
        assert (ROOT / path).is_file(), path


def test_the_notices_page_names_no_package_that_is_not_bundled():
    text = NOTICES.read_text(encoding="utf-8")
    named = set(re.findall(rf"`{licences.LICENSES_FOLDER}/([^/`]+)/`", text))
    assert named <= set(licences.BUNDLED_PACKAGES), named - set(licences.BUNDLED_PACKAGES)