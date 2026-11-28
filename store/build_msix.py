"""Builds the Microsoft Store package (.msix) from the PyInstaller build.

Run it on Windows from the project root, after building the app:

    pyinstaller RSVPReader.spec --noconfirm --clean
    python store/build_msix.py

It needs MakeAppx and MakePri from the Windows SDK, which it finds on its own
under C:\\Program Files (x86)\\Windows Kits\\10\\bin, taking the newest version
there.

What it does, all inside build/msix:

1. Lays out the package in build/msix/layout: the PyInstaller folder under
   RSVPReader, minus the one folder a package can't hold (see
   LEFT_OUT_OF_PACKAGE), the logos in Assets (drawn by make_icons.py), and
   AppxManifest.xml with the version filled in.
2. Runs MakePri to write resources.pri. The manifest names plain logo files
   like Assets\\Square44x44Logo.png, while the real files carry a scale or a
   size in their names, and resources.pri is how Windows finds the right one.
3. Runs MakeAppx to pack the layout into build/msix/RSVPReader-<version>-x64.msix.

The package isn't signed. The Store signs it when it's uploaded. To try it on
this computer first, register the layout folder instead of installing the
package (this needs Developer Mode, in Settings, System, For developers):

    Add-AppxPackage -Register build\\msix\\layout\\AppxManifest.xml

The version comes from APP_VERSION in core/app_info.py, with a 0 added as the
fourth number, because the Store keeps that one for itself and turns a package
down if it isn't 0. The app itself never imports this file, and the build
doesn't copy it."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "store"
MANIFEST_TEMPLATE = STORE / "AppxManifest.xml"
VERSION_PLACEHOLDER = "__VERSION__"

# The folder and the program PyInstaller makes. RSVPReader.spec names both,
# and the manifest's Executable points at RSVPReader\RSVPReader.exe.
APP_FOLDER = "RSVPReader"
APP_EXE = "RSVPReader.exe"
DIST_FOLDER = ROOT / "dist" / APP_FOLDER
OUT_FOLDER = ROOT / "build" / "msix"

SDK_BIN = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")

# Folders of the PyInstaller build that are left out of the package, relative
# to the RSVPReader folder. python-docx ships the unpacked source of its own
# default.docx in default-docx-template, with files named like a Word file's
# insides ([Content_Types].xml, _rels\.rels). An .msix is built the same way as
# a Word file, so those names clash with the package's own, and MakeAppx stops
# with 0x8007007b, "The filename, directory name, or volume label syntax is
# incorrect". Taking the folder out made it pack. python-docx never reads it:
# it opens templates\default.docx, which stays. The other builds keep it.
LEFT_OUT_OF_PACKAGE = (
    Path("_internal") / "docx" / "templates" / "default-docx-template",
)

# Each of the four numbers in a package version has to fit in 16 bits.
LARGEST_VERSION_PART = 65535


def _load_make_icons():
    """make_icons.py sits next to this file but outside the app's packages,
    so it's loaded by its path."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("make_icons", STORE / "make_icons.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def app_version() -> str:
    """APP_VERSION from core/app_info.py, the one place the version lives."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from core.app_info import APP_VERSION

    return APP_VERSION


def package_version(version: str) -> str:
    """The app's three part version as the four part one a package needs:
    4.2.0 becomes 4.2.0.0. Anything that isn't three plain numbers is turned
    down here, before a package with a broken version gets built."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"the app version {version!r} isn't three numbers like 4.2.0")
    parts = [int(part) for part in version.split(".")]
    if any(part > LARGEST_VERSION_PART for part in parts):
        raise ValueError(f"each number in {version!r} has to be at most {LARGEST_VERSION_PART}")
    return ".".join(str(part) for part in parts) + ".0"


def manifest_text(version: str) -> str:
    """The manifest with the package version filled in."""
    template = MANIFEST_TEMPLATE.read_text(encoding="utf-8")
    if template.count(VERSION_PLACEHOLDER) != 1:
        raise ValueError(f"the manifest should hold {VERSION_PLACEHOLDER} exactly once")
    return template.replace(VERSION_PLACEHOLDER, package_version(version))


def package_name(version: str) -> str:
    return f"RSVPReader-{version}-x64.msix"


def find_sdk_tool(name: str, sdk_bin: Path = SDK_BIN) -> Path:
    """The x64 copy of a Windows SDK tool, from the newest SDK version that
    has it. The SDK keeps each version in a folder named after it, like
    10.0.26100.0, and an older one can sit next to a newer one."""
    found = []
    if sdk_bin.is_dir():
        for folder in sdk_bin.iterdir():
            if re.fullmatch(r"\d+(\.\d+)*", folder.name) and (folder / "x64" / name).is_file():
                found.append((tuple(int(part) for part in folder.name.split(".")), folder / "x64" / name))
    if not found:
        raise FileNotFoundError(
            f"{name} isn't in {sdk_bin}. It comes with the Windows SDK: install its "
            f"Signing Tools for Desktop Apps."
        )
    return max(found)[1]


def lay_out(dist_folder: Path, out_folder: Path, version: str) -> Path:
    """Builds the package's folder from scratch and returns it. Anything left
    from an earlier run is removed first, so an old file can't end up in the
    package."""
    if not (dist_folder / APP_EXE).is_file():
        raise FileNotFoundError(
            f"{dist_folder / APP_EXE} isn't there. Build the app first: "
            f"pyinstaller RSVPReader.spec --noconfirm --clean"
        )
    if out_folder.exists():
        shutil.rmtree(out_folder)
    layout = out_folder / "layout"
    shutil.copytree(dist_folder, layout / APP_FOLDER)
    for folder in LEFT_OUT_OF_PACKAGE:
        # Not there if a later python-docx drops it, which is fine too.
        shutil.rmtree(layout / APP_FOLDER / folder, ignore_errors=True)
    _load_make_icons().write_msix_logos(layout / "Assets")
    (layout / "AppxManifest.xml").write_text(manifest_text(version), encoding="utf-8")

    # MakePri reads only this folder, which holds just the logos. Pointed at
    # the whole layout it would also go through every file PyInstaller made.
    shutil.copytree(layout / "Assets", out_folder / "pri" / "Assets")
    return layout


def pri_commands(makepri: Path, out_folder: Path) -> list[list[str]]:
    """The two MakePri runs: one writes the settings file it works from, the
    other writes resources.pri into the layout. en-US matches the manifest's
    language, and 10.0.0 is the Windows 10 resource format."""
    config = out_folder / "priconfig.xml"
    layout = out_folder / "layout"
    return [
        [str(makepri), "createconfig", "/cf", str(config), "/dq", "en-US", "/pv", "10.0.0", "/o"],
        [
            str(makepri), "new",
            "/pr", str(out_folder / "pri"),
            "/cf", str(config),
            "/mn", str(layout / "AppxManifest.xml"),
            "/of", str(layout / "resources.pri"),
            "/o",
        ],
    ]


def pack_command(makeappx: Path, out_folder: Path, version: str) -> list[str]:
    """MakeAppx packing the layout into the .msix, replacing an old one."""
    return [
        str(makeappx), "pack",
        "/d", str(out_folder / "layout"),
        "/p", str(out_folder / package_name(version)),
        "/o",
    ]


def main(argv: list[str], run=subprocess.run, sdk_bin: Path = SDK_BIN,
         dist_folder: Path = DIST_FOLDER, out_folder: Path = OUT_FOLDER) -> int:
    if sys.platform != "win32" and run is subprocess.run:
        print("The Store package is built on Windows, with the Windows SDK.")
        return 1
    try:
        version = app_version()
        makepri = find_sdk_tool("makepri.exe", sdk_bin)
        makeappx = find_sdk_tool("makeappx.exe", sdk_bin)
        lay_out(dist_folder, out_folder, version)
    except (FileNotFoundError, ValueError) as problem:
        print(problem)
        return 1

    for command in [*pri_commands(makepri, out_folder), pack_command(makeappx, out_folder, version)]:
        print(">", " ".join(command))
        result = run(command)
        if result.returncode != 0:
            print(f"{Path(command[0]).name} stopped with exit code {result.returncode}, see above.")
            return 1

    print(f"Built {out_folder / package_name(version)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
