# -*- mode: python ; coding: utf-8 -*-

import sys

from PyInstaller.utils.hooks import collect_data_files

# customtkinter ships its own non-Python data files (theme JSON, bundled
# fonts, its own default icon) that PyInstaller's automatic dependency
# analysis doesn't know to include, since they're only ever read at
# runtime via a __file__-relative path inside the package, not imported.
# collect_data_files() walks the installed package and returns the right
# (source, dest) pairs automatically -- portable across your different
# machines, unlike hardcoding an absolute site-packages path. See
# https://customtkinter.tomschimansky.com/documentation/packaging/
datas = collect_data_files('customtkinter')

# Our own app assets. Destination paths ('assets/fonts', 'assets/icons')
# mirror the source layout exactly -- gui/theme.py locates these at
# runtime via a __file__-relative path (two directories up from
# gui/theme.py, then into assets/...), and PyInstaller preserves that
# math for frozen builds as long as the bundle's own layout matches, so
# this needs no source-code change.
datas += [
    ('assets/fonts', 'assets/fonts'),
    ('assets/icons', 'assets/icons'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    # darkdetect (used only for "System" theme detection, see
    # gui/theme.py's _detect_system_prefers_dark()) has a documented,
    # unresolved history of PyInstaller builds not finding it even when
    # installed -- see https://github.com/TomSchimansky/CustomTkinter/issues/2779.
    # Naming it here is a real, standard mitigation, not a guaranteed
    # fix. Worth knowing either way: _detect_system_prefers_dark()
    # already wraps the import in try/except, so even if this doesn't
    # fully resolve it, the worst case is "System" mode silently
    # defaulting to the Light look, not a crash.
    hiddenimports=['darkdetect'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Icon format is platform-specific: Windows wants a multi-resolution
# .ico, macOS wants .icns (built on the runner from assets/icons/app.png
# by .github/workflows/build-release.yml's macOS job -- see that file),
# and on Linux this EXE-level icon= is simply ignored by PyInstaller,
# since Linux has no equivalent embedded-executable-icon mechanism; the
# actual window icon there is set at runtime instead, cross-platform,
# by gui/theme.py's apply_app_icon().
if sys.platform == "win32":
    _icon = ['assets/icons/app.ico']
elif sys.platform == "darwin":
    _icon = ['assets/icons/app.icns']
else:
    _icon = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RSVPReader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RSVPReader',
)

# macOS only: wraps the onedir COLLECT output in a proper RSVPReader.app
# bundle, so the result behaves like a normal Mac application (Finder
# icon, Dock icon, double-clickable) rather than the Windows/Linux-style
# "folder full of files plus a loose binary" layout. This block has no
# effect on Windows/Linux -- BUNDLE() only does anything on macOS.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name='RSVPReader.app',
        icon='assets/icons/app.icns',
        bundle_identifier='com.rsvpreader.app',
    )