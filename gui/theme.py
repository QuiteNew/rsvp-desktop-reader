"""Central design tokens for the RSVP reader's "cozy fireside" theme.
Every styled component reads its colors and fonts from here, so a
future palette or font change happens in exactly one place.

Theme switching (Light/Dark/System) is resolved ONCE, here, at import
time — before any other module that reads these constants gets loaded.
That's what lets every component file keep importing plain names like
HEARTH_PAPER unchanged; this file alone decides what they equal."""

import os
import ctypes
import tkinter as tk

# ---- Palettes ----

LIGHT_PALETTE = {
    "hearth_paper": "#F6EFE3",
    "cocoa_ink": "#3B2E27",
    "cocoa_ink_light": "#4A3C33",
    "warm_taupe": "#ECE0CF",
    "warm_mocha": "#B7A38A",
    "dusk_blue": "#6E8496",
    "dusk_blue_hover": "#5C7284",
    "ember_glow": "#D98A3D",
    "ember_glow_hover": "#C17A2F",
    "warm_line": "#D6C4AC",
    "text_on_light": "#3B2E27",
    "text_on_dark": "#F6EFE3",
}

DARK_PALETTE = {
    "hearth_paper": "#1D1712",       # soft near-black, warm brown undertone — never blue
    "cocoa_ink": "#F2E8DC",          # was dark text-on-light; now light text-on-dark
    "cocoa_ink_light": "#D9CBB8",
    "warm_taupe": "#2E2419",         # sidebar/header/entry-field panels — a step lighter than base
    "warm_mocha": "#4A3826",         # Spaces/Footer band — the richest, lightest of the dark surfaces
    "dusk_blue": "#7C93A3",
    "dusk_blue_hover": "#6B7F8C",
    "ember_glow": "#A8672E",         # deliberately darker/more burnt than the light theme's Ember Glow
    "ember_glow_hover": "#BF7A3B",   # hover goes LIGHTER here, not darker — the visible direction on dark UIs
    "warm_line": "#7A6248",          # doubles as border color and inactive-space text — needs to read both ways
    "text_on_light": "#F2E8DC",
    "text_on_dark": "#1D1712",
}


def _detect_system_prefers_dark() -> bool:
    """Best-effort read of the OS's own light/dark preference, used only
    when the appearance mode is set to 'system'."""
    try:
        import darkdetect
        return darkdetect.isDark() is True
    except Exception:
        return False


def _resolve_active_palette():
    """Decide once which palette and CTk appearance-mode string to use,
    based on the saved setting. Falls back to Light on any error (e.g.
    a fresh install with no settings file yet), so a theming problem can
    never prevent the app from launching."""
    mode = "light"
    try:
        from core.settings_store import SettingsStore
        mode = SettingsStore().appearance_mode
    except Exception:
        pass

    if mode == "dark":
        is_dark = True
    elif mode == "system":
        is_dark = _detect_system_prefers_dark()
    else:
        is_dark = False

    palette = DARK_PALETTE if is_dark else LIGHT_PALETTE
    ctk_mode = "Dark" if is_dark else "Light"
    return palette, ctk_mode


_active, CTK_APPEARANCE_MODE = _resolve_active_palette()

# ---- Colors ----

HEARTH_PAPER = _active["hearth_paper"]
COCOA_INK = _active["cocoa_ink"]
COCOA_INK_LIGHT = _active["cocoa_ink_light"]
WARM_TAUPE = _active["warm_taupe"]
WARM_MOCHA = _active["warm_mocha"]
DUSK_BLUE = _active["dusk_blue"]
DUSK_BLUE_HOVER = _active["dusk_blue_hover"]
EMBER_GLOW = _active["ember_glow"]
EMBER_GLOW_HOVER = _active["ember_glow_hover"]
WARM_LINE = _active["warm_line"]
TEXT_ON_LIGHT = _active["text_on_light"]
TEXT_ON_DARK = _active["text_on_dark"]

# ---- Dark-mode reading defaults ----
# A *newly created* transcript's reading colors (font/highlight/background)
# normally come straight from AppSettings.default_* -- plain user-chosen
# hex values, deliberately NOT theme-aware, since per-transcript color
# customization is meant to be independent of everything else (see
# core/settings_store.py). Left alone, that means a transcript created
# while the app is in Dark mode still starts out with the light-mode
# cream/dark-ink defaults, which reads as a jarring, unintended gap next
# to the rest of the now-dark chrome, not a deliberate choice.
#
# These three are an alternative seed used ONLY at the moment a new
# transcript is created (see gui/app.py's _handle_new_transcript()), and
# only when CTK_APPEARANCE_MODE is "Dark" -- never applied retroactively
# to a transcript that already exists, and never used at all in Light
# mode, where AppSettings.default_* still applies exactly as before.
DARK_READING_FONT_COLOR = DARK_PALETTE["cocoa_ink"]        # "#F2E8DC" -- same cream used for every other on-dark text label
DARK_READING_HIGHLIGHT_COLOR = DARK_PALETTE["ember_glow"]  # "#A8672E" -- same accent color used everywhere else in dark mode
DARK_READING_BACKGROUND_COLOR = "#241D17"                  # a small, deliberate step lighter than hearth_paper's dark
                                                             # value ("#1D1712" -- also the transcript-list row color and
                                                             # the color behind the canvas toolbar), so the reading canvas
                                                             # still reads as its own region instead of blending in flat

# The global guide-mark color (AppSettings.guide_mark_color) follows the
# same "still tracking the theme default, unless manually picked" pattern
# as the per-transcript reading colors above, but it's a single app-wide
# value, not seeded per-transcript -- see SettingsStore.guide_mark_color /
# resync_guide_mark_color_default() and gui/app.py's startup resync.
#
# In Light mode the existing default ("#3B2E27") already matches the
# reading font color, so LIGHT_READING_GUIDE_MARK_COLOR is that same value
# named explicitly, for symmetry with the Dark constant below rather than
# leaving the Light case implicit in AppSettings' own dataclass default.
# In Dark mode, the original dark cocoa_ink guide-mark color was reported
# too dark to see against a dark reading background, so this uses the same
# soft off-white/cream already used for every other on-dark text label --
# a real "soft white" as requested, not pure #FFFFFF.
LIGHT_READING_GUIDE_MARK_COLOR = LIGHT_PALETTE["cocoa_ink"]  # "#3B2E27" -- unchanged from the historical default
DARK_READING_GUIDE_MARK_COLOR = DARK_PALETTE["cocoa_ink"]    # "#F2E8DC" -- soft cream/white, visible on a dark background

# ---- Fonts ----

FONT_HEADING = "Fredoka SemiBold"
FONT_BODY = "Quicksand Medium"

_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
_FONT_FILES = ["Fredoka-SemiBold.ttf", "Quicksand-Medium.ttf"]

_FR_PRIVATE = 0x10


def register_fonts() -> None:
    if os.name != "nt":
        return
    for filename in _FONT_FILES:
        path = os.path.join(_FONT_DIR, filename)
        if os.path.exists(path):
            ctypes.windll.gdi32.AddFontResourceExW(ctypes.c_wchar_p(path), _FR_PRIVATE, 0)


def unregister_fonts() -> None:
    if os.name != "nt":
        return
    for filename in _FONT_FILES:
        path = os.path.join(_FONT_DIR, filename)
        if os.path.exists(path):
            ctypes.windll.gdi32.RemoveFontResourceExW(ctypes.c_wchar_p(path), _FR_PRIVATE, 0)

# ---- App icon ----

_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")
_ICON_ICO = os.path.join(_ICON_DIR, "app.ico")
_ICON_PNG = os.path.join(_ICON_DIR, "app.png")

# Kept alive for as long as the app runs. Tkinter's PhotoImage has no
# Python-side reference of its own once handed to iconphoto() -- without
# holding one ourselves, the garbage collector can reclaim it later and
# the window icon silently reverts to Tk's default feather. One shared
# instance is enough; every window that calls apply_app_icon() below reuses it.
_icon_photo_image = None


def set_dpi_awareness() -> None:
    """Declares this process DPI-aware to Windows. Call this once, as the
    very first thing main.py does -- before register_fonts(), before
    ctk.set_appearance_mode(), and before the first window (RSVPApp()) is
    created. Windows reads a process's DPI awareness once, early; setting
    it any later, or per-window, has no effect.

    Without this, on any display scaled above 100% (125%/150%/etc. -- the
    default on most modern laptops), Windows runs the whole app in a
    virtualized 96-DPI mode and then bitmap-stretches everything it draws
    to match the real scale -- window chrome, and the icons Windows shows
    for that window in the taskbar and title bar. That stretch is what a
    "blurry icon despite a proper high-resolution .ico" report almost
    always turns out to be; declaring DPI awareness up front means Windows
    asks for and draws icons at their real physical size instead.

    Tries the modern per-monitor-aware API first (Windows 8.1+), falls
    back to the older, coarser one (Vista+) if that's unavailable, and
    otherwise does nothing -- same defensive pattern as the rest of this
    file: Windows-only, and a DPI call that doesn't work just leaves the
    app rendering as it did before, never a reason it fails to launch."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # older fallback, system-DPI-aware only
        except (AttributeError, OSError):
            pass


def _set_native_windows_icon(window) -> None:
    """EXPERIMENTAL, not yet confirmed to fix anything -- see the note in
    apply_app_icon() below before touching this.

    iconbitmap() (in apply_app_icon()) is what gets the taskbar *button*
    icon looking right. But the window's own title-bar icon, its entry in
    the Alt-Tab list, and the small icon badge shown on the taskbar's
    hover-preview thumbnail are filled by a different Windows mechanism:
    each top-level window has two icon "slots" -- ICON_SMALL (title bar /
    Alt-Tab list / hover-preview badge) and ICON_BIG (Alt-Tab's large
    view) -- set via the WM_SETICON message. The working theory is that
    Tk's own internal handling of that message, on the Windows build in
    use here, extracts a fixed-size frame from the .ico (rather than
    asking Windows for whatever size that slot actually needs on this
    display) and lets Windows stretch it to fit -- which would produce
    exactly the "taskbar button improved, title bar/hover-preview still
    blurry" split that was reported after the BMP-format .ico fix.

    This bypasses Tk's icon handling for those two slots entirely: it asks
    Windows itself what physical pixel size each slot wants right now
    (GetSystemMetrics -- only meaningful because set_dpi_awareness() has
    already run before any window was created), has Windows extract an
    icon at exactly that size straight out of the .ico file (LoadImageW),
    and pushes the result into both slots directly (SendMessageW +
    WM_SETICON), instead of going through iconbitmap()'s own path.

    This is a real, standard technique for this exact class of problem,
    not a guess pulled from nowhere -- but unlike the previous two fixes
    in this file, neither the diagnosis nor this fix could be verified
    against a real Windows title bar before landing here. Treat it as an
    experiment to test, the same as the DPI-awareness and BMP-format
    fixes were, not as a confirmed solution.

    Best-effort and Windows-only, same defensive pattern as the rest of
    this file: any failure here just leaves the icon exactly as
    iconbitmap() left it -- never a reason the app fails to launch."""
    if os.name != "nt":
        return
    if not os.path.exists(_ICON_ICO):
        return
    try:
        user32 = ctypes.windll.user32

        get_parent = user32.GetParent
        get_parent.restype = ctypes.c_void_p
        get_parent.argtypes = [ctypes.c_void_p]

        get_system_metrics = user32.GetSystemMetrics
        get_system_metrics.restype = ctypes.c_int
        get_system_metrics.argtypes = [ctypes.c_int]

        load_image_w = user32.LoadImageW
        load_image_w.restype = ctypes.c_void_p
        load_image_w.argtypes = [
            ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint,
        ]

        send_message_w = user32.SendMessageW
        send_message_w.restype = ctypes.c_void_p
        send_message_w.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
        ]

        SM_CXSMICON = 49
        SM_CXICON = 11
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        # winfo_id() gives Tk's drawing-surface handle, not the real
        # top-level window -- GetParent walks up to the actual HWND that
        # owns the title bar, the one WM_SETICON needs to target.
        hwnd = get_parent(window.winfo_id())
        if not hwnd:
            return

        small_size = get_system_metrics(SM_CXSMICON)
        big_size = get_system_metrics(SM_CXICON)

        h_small = load_image_w(None, _ICON_ICO, IMAGE_ICON, small_size, small_size, LR_LOADFROMFILE)
        h_big = load_image_w(None, _ICON_ICO, IMAGE_ICON, big_size, big_size, LR_LOADFROMFILE)

        if h_small:
            send_message_w(hwnd, WM_SETICON, ICON_SMALL, h_small)
        if h_big:
            send_message_w(hwnd, WM_SETICON, ICON_BIG, h_big)
    except (AttributeError, OSError):
        pass


def apply_app_icon(window) -> None:
    """Sets the title-bar/taskbar icon for any CTk window -- the main
    RSVPApp window, or a CTkToplevel such as SettingsWindow or
    DetachedTranscriptWindow. Call this once per window, right after that
    window's own __init__ sets its title.

    On Windows this uses the bundled .ico via iconbitmap() -- a real
    multi-resolution icon (16/32/48/256px), and the same file a future
    PyInstaller build will use for the packaged .exe's own icon.
    iconbitmap()'s .ico support isn't reliable outside Windows, so other
    platforms fall back to iconphoto() with a plain PNG instead, same as
    most cross-platform Tk apps do.

    Immediately after that, on Windows, _set_native_windows_icon() runs
    as a second pass that overwrites the title-bar/Alt-Tab/hover-preview
    icon slots directly via Win32 calls -- see that function's docstring
    for why, and for the caveat that this second pass is still an
    unverified experiment, not a confirmed fix.

    Same defensive pattern as register_fonts() above: platform-guarded,
    and does nothing at all if the expected asset file isn't present --
    a missing icon should never be a reason the app fails to launch."""
    global _icon_photo_image

    if os.name == "nt":
        if os.path.exists(_ICON_ICO):
            window.iconbitmap(_ICON_ICO)
            _set_native_windows_icon(window)
    else:
        if os.path.exists(_ICON_PNG):
            if _icon_photo_image is None:
                _icon_photo_image = tk.PhotoImage(file=_ICON_PNG)
            window.iconphoto(True, _icon_photo_image)