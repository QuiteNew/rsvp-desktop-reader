"""Tests for the Microsoft Store package: store/AppxManifest.xml and
store/build_msix.py.

MakeAppx and MakePri only exist on Windows with the SDK installed, so these
tests don't run them. They check everything around them instead: that the
manifest holds the identity Partner Center gave the app, that the version
comes from APP_VERSION with the 0 the Store wants at the end, that the logos
the manifest names are ones make_icons.py draws, that the package folder is
laid out the way the manifest expects, without the one folder MakeAppx turns
down, and that the tools are run with the right arguments, in the right order,
stopping at the first one that fails."""

import importlib.util
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.app_info import APP_NAME, APP_VERSION

ROOT = Path(__file__).resolve().parent.parent

NS = {
    "m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
    "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
    "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities",
}


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "store" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


msix = _load("build_msix")
icons = _load("make_icons")


@pytest.fixture(scope="module")
def manifest():
    return ET.fromstring(msix.manifest_text(APP_VERSION))


# ---- The manifest ----

def test_the_identity_is_the_one_partner_center_gave_the_app(manifest):
    """Written out in full: a wrong character here and the Store turns the
    upload down, so a change has to be on purpose."""
    identity = manifest.find("m:Identity", NS)
    assert identity.get("Name") == "QuiteNew.RSVPReader"
    assert identity.get("Publisher") == "CN=B3731F9D-170C-4DED-8F8B-5051D9BDE67E"
    assert manifest.find("m:Properties/m:PublisherDisplayName", NS).text == "QuiteNew"


def test_the_version_is_the_apps_own_with_a_zero_added(manifest):
    assert manifest.find("m:Identity", NS).get("Version") == APP_VERSION + ".0"


def test_the_version_placeholder_is_gone_from_the_filled_in_manifest():
    assert msix.VERSION_PLACEHOLDER not in msix.manifest_text(APP_VERSION)


def test_the_name_everywhere_is_the_apps_own(manifest):
    """The Store listing, the Start menu and the app's title bar all say the
    same thing."""
    assert manifest.find("m:Properties/m:DisplayName", NS).text == APP_NAME
    visual = manifest.find("m:Applications/m:Application/uap:VisualElements", NS)
    assert visual.get("DisplayName") == APP_NAME


def test_it_starts_the_program_pyinstaller_builds_as_a_full_trust_app(manifest):
    application = manifest.find("m:Applications/m:Application", NS)
    assert application.get("Executable") == f"{msix.APP_FOLDER}\\{msix.APP_EXE}"
    assert application.get("EntryPoint") == "Windows.FullTrustApplication"
    capabilities = [c.get("Name") for c in manifest.findall("m:Capabilities/rescap:Capability", NS)]
    assert capabilities == ["runFullTrust"]


def test_the_program_name_matches_the_pyinstaller_spec():
    spec = (ROOT / "RSVPReader.spec").read_text(encoding="utf-8")
    assert re.findall(r"name='RSVPReader'", spec), "RSVPReader.spec no longer names the build RSVPReader"
    assert msix.APP_FOLDER == "RSVPReader"
    assert msix.APP_EXE == "RSVPReader.exe"


def test_it_is_a_64_bit_package_for_windows_10_and_11(manifest):
    assert manifest.find("m:Identity", NS).get("ProcessorArchitecture") == "x64"
    family = manifest.find("m:Dependencies/m:TargetDeviceFamily", NS)
    assert family.get("Name") == "Windows.Desktop"
    lowest = tuple(int(part) for part in family.get("MinVersion").split("."))
    tested = tuple(int(part) for part in family.get("MaxVersionTested").split("."))
    assert (10, 0, 17763, 0) <= lowest <= tested


def test_every_logo_the_manifest_names_is_one_make_icons_draws(manifest):
    """The manifest names plain files like Assets\\Square44x44Logo.png and
    Windows looks for the scaled ones next to them, so each name needs a set
    of .scale-NNN files, the 100 and 200 percent ones at least."""
    visual = manifest.find("m:Applications/m:Application/uap:VisualElements", NS)
    named = [
        manifest.find("m:Properties/m:Logo", NS).text,
        visual.get("Square150x150Logo"),
        visual.get("Square44x44Logo"),
    ]
    drawn = icons.msix_logo_sizes()
    for path in named:
        folder, file_name = path.split("\\")
        assert folder == "Assets"
        base = file_name.removesuffix(".png")
        for percent in (100, 200):
            assert f"{base}.scale-{percent}.png" in drawn, f"no {percent}% file for {path}"


def test_the_small_logo_has_its_plain_backed_taskbar_sizes():
    drawn = icons.msix_logo_sizes()
    for size in (16, 24, 32, 48, 256):
        assert f"Square44x44Logo.targetsize-{size}_altform-unplated.png" in drawn


def test_the_manifest_template_holds_the_placeholder_once():
    template = msix.MANIFEST_TEMPLATE.read_text(encoding="utf-8")
    assert template.count(msix.VERSION_PLACEHOLDER) == 1


def test_a_template_without_the_placeholder_is_turned_down(tmp_path, monkeypatch):
    broken = tmp_path / "AppxManifest.xml"
    broken.write_text('<Package Version="1.0.0.0"/>', encoding="utf-8")
    monkeypatch.setattr(msix, "MANIFEST_TEMPLATE", broken)
    with pytest.raises(ValueError, match="exactly once"):
        msix.manifest_text("1.0.0")


# ---- The version ----

@pytest.mark.parametrize("version, expected", [
    ("4.2.0", "4.2.0.0"),
    ("4.1.1", "4.1.1.0"),
    ("10.0.12", "10.0.12.0"),
    ("1.02.3", "1.2.3.0"),
    ("65535.0.0", "65535.0.0.0"),
])
def test_the_package_version_is_the_app_version_with_a_zero_added(version, expected):
    assert msix.package_version(version) == expected


@pytest.mark.parametrize("version", ["4.2", "4.2.0.1", "v4.2.0", "4.2.0-beta", "", "4..0", "65536.0.0"])
def test_a_version_that_cant_be_a_package_version_is_turned_down(version):
    with pytest.raises(ValueError):
        msix.package_version(version)


def test_the_fourth_number_is_always_zero_for_the_store():
    assert msix.package_version(APP_VERSION).endswith(".0")
    assert msix.package_version(APP_VERSION).count(".") == 3


def test_the_package_file_is_named_after_the_version():
    assert msix.package_name("4.2.0") == "RSVPReader-4.2.0-x64.msix"


# ---- Finding the Windows SDK tools ----

def _sdk(tmp_path, versions_with_tool, tool="makeappx.exe"):
    sdk_bin = tmp_path / "bin"
    for version in versions_with_tool:
        (sdk_bin / version / "x64").mkdir(parents=True)
        (sdk_bin / version / "x64" / tool).write_bytes(b"")
    return sdk_bin


def test_it_takes_the_tool_from_the_newest_sdk(tmp_path):
    """Compared as numbers: 10.0.28000.0 is newer than 10.0.9200.0 even though
    it sorts first as text."""
    sdk_bin = _sdk(tmp_path, ["10.0.9200.0", "10.0.28000.0", "10.0.17134.0"])
    assert msix.find_sdk_tool("makeappx.exe", sdk_bin) == sdk_bin / "10.0.28000.0" / "x64" / "makeappx.exe"


def test_it_skips_sdk_folders_without_the_tool_and_ones_that_arent_versions(tmp_path):
    sdk_bin = _sdk(tmp_path, ["10.0.17134.0"])
    (sdk_bin / "10.0.28000.0" / "x64").mkdir(parents=True)  # newer, but no tool in it
    (sdk_bin / "x64").mkdir()
    (sdk_bin / "x64" / "makeappx.exe").write_bytes(b"")  # not a version folder
    assert msix.find_sdk_tool("makeappx.exe", sdk_bin) == sdk_bin / "10.0.17134.0" / "x64" / "makeappx.exe"


def test_a_missing_tool_says_what_to_install(tmp_path):
    with pytest.raises(FileNotFoundError, match="Signing Tools for Desktop Apps"):
        msix.find_sdk_tool("makepri.exe", tmp_path / "nowhere")


# ---- Laying out the package ----

def _dist(tmp_path):
    dist = tmp_path / "dist" / "RSVPReader"
    (dist / "_internal").mkdir(parents=True, exist_ok=True)
    (dist / "RSVPReader.exe").write_bytes(b"program")
    (dist / "_internal" / "python313.dll").write_bytes(b"library")
    # python-docx as PyInstaller copies it: the default.docx it opens, and the
    # unpacked source of that file, which a package can't hold.
    templates = dist / "_internal" / "docx" / "templates"
    (templates / "default-docx-template" / "_rels").mkdir(parents=True, exist_ok=True)
    (templates / "default.docx").write_bytes(b"word file")
    (templates / "default-docx-template" / "[Content_Types].xml").write_text("<Types/>", encoding="utf-8")
    (templates / "default-docx-template" / "_rels" / ".rels").write_text("<Relationships/>", encoding="utf-8")
    return dist


def test_the_layout_has_the_program_the_logos_and_the_manifest(tmp_path):
    out = tmp_path / "msix"
    layout = msix.lay_out(_dist(tmp_path), out, "4.2.0")
    assert (layout / "RSVPReader" / "RSVPReader.exe").read_bytes() == b"program"
    assert (layout / "RSVPReader" / "_internal" / "python313.dll").is_file()
    assert sorted(p.name for p in (layout / "Assets").iterdir()) == sorted(icons.msix_logo_sizes())
    written = ET.fromstring((layout / "AppxManifest.xml").read_text(encoding="utf-8"))
    assert written.find("m:Identity", NS).get("Version") == "4.2.0.0"


def test_the_layout_holds_nothing_else_at_its_top(tmp_path):
    """MakeAppx packs everything in the folder, so the working files (the
    MakePri settings and its copy of the logos) stay beside it, not in it."""
    layout = msix.lay_out(_dist(tmp_path), tmp_path / "msix", "4.2.0")
    assert sorted(p.name for p in layout.iterdir()) == ["AppxManifest.xml", "Assets", "RSVPReader"]


def test_makepri_gets_a_folder_with_only_the_logos(tmp_path):
    out = tmp_path / "msix"
    msix.lay_out(_dist(tmp_path), out, "4.2.0")
    assert [p.name for p in (out / "pri").iterdir()] == ["Assets"]
    assert sorted(p.name for p in (out / "pri" / "Assets").iterdir()) == sorted(icons.msix_logo_sizes())


def test_a_second_run_starts_from_a_clean_folder(tmp_path):
    out = tmp_path / "msix"
    msix.lay_out(_dist(tmp_path), out, "4.2.0")
    (out / "layout" / "RSVPReader" / "left-over.txt").write_text("old", encoding="utf-8")
    msix.lay_out(_dist(tmp_path), out, "4.2.0")
    assert not (out / "layout" / "RSVPReader" / "left-over.txt").exists()


def test_the_unpacked_word_template_is_left_out_and_default_docx_stays(tmp_path):
    """MakeAppx turned the package down with that folder in it (0x8007007b)
    and packed it once the folder was gone. python-docx only opens
    default.docx, so that one has to stay."""
    layout = msix.lay_out(_dist(tmp_path), tmp_path / "msix", "4.2.0")
    templates = layout / "RSVPReader" / "_internal" / "docx" / "templates"
    assert not (templates / "default-docx-template").exists()
    assert (templates / "default.docx").read_bytes() == b"word file"


def test_no_file_named_like_a_packages_own_insides_is_left(tmp_path):
    layout = msix.lay_out(_dist(tmp_path), tmp_path / "msix", "4.2.0")
    names = [path.name for path in layout.rglob("*")]
    assert "[Content_Types].xml" not in names
    assert ".rels" not in names


def test_the_left_out_folder_is_only_taken_from_the_package(tmp_path):
    """The PyInstaller build itself keeps it, so the zip and folder builds
    stay exactly as they were."""
    dist = _dist(tmp_path)
    msix.lay_out(dist, tmp_path / "msix", "4.2.0")
    assert (dist / "_internal" / "docx" / "templates" / "default-docx-template" / "[Content_Types].xml").is_file()


def test_a_build_without_the_template_folder_still_lays_out(tmp_path):
    dist = _dist(tmp_path)
    shutil.rmtree(dist / "_internal" / "docx" / "templates" / "default-docx-template")
    layout = msix.lay_out(dist, tmp_path / "msix", "4.2.0")
    assert (layout / "RSVPReader" / "RSVPReader.exe").is_file()


def test_without_a_build_it_says_how_to_make_one(tmp_path):
    with pytest.raises(FileNotFoundError, match="pyinstaller RSVPReader.spec"):
        msix.lay_out(tmp_path / "dist" / "RSVPReader", tmp_path / "msix", "4.2.0")


# ---- Running the tools ----

def test_makepri_writes_its_settings_then_resources_pri_into_the_layout(tmp_path):
    first, second = msix.pri_commands(Path("makepri.exe"), tmp_path)
    assert first == ["makepri.exe", "createconfig", "/cf", str(tmp_path / "priconfig.xml"),
                     "/dq", "en-US", "/pv", "10.0.0", "/o"]
    assert second == ["makepri.exe", "new",
                      "/pr", str(tmp_path / "pri"),
                      "/cf", str(tmp_path / "priconfig.xml"),
                      "/mn", str(tmp_path / "layout" / "AppxManifest.xml"),
                      "/of", str(tmp_path / "layout" / "resources.pri"),
                      "/o"]


def test_makeappx_packs_the_layout_into_the_named_package(tmp_path):
    assert msix.pack_command(Path("makeappx.exe"), tmp_path, "4.2.0") == [
        "makeappx.exe", "pack",
        "/d", str(tmp_path / "layout"),
        "/p", str(tmp_path / "RSVPReader-4.2.0-x64.msix"),
        "/o",
    ]


def _run_main(tmp_path, exit_codes):
    """main() with the SDK, the build and the tools all stood in for. Each
    tool call gets the next exit code from the list."""
    sdk_bin = _sdk(tmp_path, ["10.0.28000.0"])
    (sdk_bin / "10.0.28000.0" / "x64" / "makepri.exe").write_bytes(b"")
    calls = []
    codes = iter(exit_codes)

    def run(command):
        calls.append(command)
        return SimpleNamespace(returncode=next(codes))

    result = msix.main(["build_msix.py"], run=run, sdk_bin=sdk_bin,
                       dist_folder=_dist(tmp_path), out_folder=tmp_path / "msix")
    return result, [Path(command[0]).name + " " + command[1] for command in calls]


def test_it_runs_makepri_twice_then_makeappx(tmp_path, capsys):
    result, calls = _run_main(tmp_path, [0, 0, 0])
    assert result == 0
    assert calls == ["makepri.exe createconfig", "makepri.exe new", "makeappx.exe pack"]
    assert f"RSVPReader-{APP_VERSION}-x64.msix" in capsys.readouterr().out


def test_it_stops_at_the_first_tool_that_fails(tmp_path, capsys):
    result, calls = _run_main(tmp_path, [0, 3])
    assert result == 1
    assert calls == ["makepri.exe createconfig", "makepri.exe new"]
    assert "exit code 3" in capsys.readouterr().out


def test_without_the_sdk_it_says_so_and_runs_nothing(tmp_path, capsys):
    calls = []
    result = msix.main(["build_msix.py"], run=lambda command: calls.append(command),
                       sdk_bin=tmp_path / "no-sdk", dist_folder=_dist(tmp_path), out_folder=tmp_path / "msix")
    assert result == 1
    assert calls == []
    assert "Windows SDK" in capsys.readouterr().out


@pytest.mark.skipif(sys.platform == "win32", reason="checks what happens away from Windows")
def test_away_from_windows_it_says_the_package_is_built_on_windows(capsys):
    assert msix.main(["build_msix.py"], run=subprocess.run) == 1
    assert "Windows" in capsys.readouterr().out


# ---- It stays out of the app ----

def test_the_app_never_imports_the_packaging_script():
    sources = [ROOT / "main.py", *(ROOT / "core").rglob("*.py"), *(ROOT / "gui").rglob("*.py")]
    for source in sources:
        assert "build_msix" not in source.read_text(encoding="utf-8"), source
