"""Putting text and its bold on the Windows clipboard, in one go.

core/rich_copy.py builds the HTML that Word reads. This module hands it to
Windows, together with the plain text, so that one copy serves both: Word shows
the bold, Notepad and everything else that only reads plain text gets the same
words without it.

Tk cannot do this. Its clipboard takes one kind of data, plain text, so the
Windows clipboard functions are called directly through ctypes. That part can only
be tried on Windows, so it is kept as small as it can be: _Win32Api is a thin
wrapper with one method per Windows function, and everything that decides what is
done and in which order (copy_rich) works on any object with those methods, which
is how it is tested elsewhere.

copy_rich never raises and says whether it worked. When it did not (the clipboard
was held by another program, or not on Windows at all) the caller falls back to
an ordinary plain copy, so a copy is never lost."""

import sys
import time

# The clipboard format number of plain Unicode text, fixed by Windows.
CF_UNICODETEXT = 13

# HTML has no fixed number: it is looked up by this name, and Word looks for the
# same name.
HTML_FORMAT_NAME = "HTML Format"

# GlobalAlloc's flag for memory that the clipboard is allowed to move around.
_GMEM_MOVEABLE = 0x0002

# Another program can have the clipboard open for a moment (a clipboard manager,
# a remote desktop). A few quick retries get past that, and a copy that still
# cannot open it gives up.
_OPEN_TRIES = 5
_OPEN_WAIT = 0.02


def copy_rich(owner: int, plain: str, html: bytes, api=None) -> bool:
    """Put `plain` and `html` (the bytes from core.rich_copy.cf_html) on the
    clipboard. `owner` is the handle of one of the app's own windows: Windows
    refuses to store anything if the clipboard is opened without one. True when
    both formats are on the clipboard. False when not, and then nothing is
    promised about what the clipboard holds, so the caller should copy the plain
    text the ordinary way. Never raises."""
    try:
        if api is None:
            if sys.platform != "win32":
                return False
            api = _windows_api()
        # Everything that can fail on its own is done before the clipboard is
        # touched, so a failure here leaves what was on it alone.
        text = _windows_text(plain).encode("utf-16-le") + b"\0\0"
        page = html + b"\0"
        html_format = api.register_format(HTML_FORMAT_NAME)
        if not html_format:
            return False
        if not _open(api, owner):
            return False
        try:
            if not api.empty():
                return False
            return _put(api, CF_UNICODETEXT, text) and _put(api, html_format, page)
        finally:
            api.close()
    except Exception:
        # Whatever went wrong, the contract is to say so and not to bring the
        # app down over a copy.
        return False


def _windows_text(text: str) -> str:
    """text with Windows line endings, which is what the plain text format uses.
    Tk does the same for its own copies. A line break that already is one is not
    doubled."""
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def _open(api, owner: int) -> bool:
    for attempt in range(_OPEN_TRIES):
        if attempt:
            time.sleep(_OPEN_WAIT)
        if api.open(owner):
            return True
    return False


def _put(api, clipboard_format: int, data: bytes) -> bool:
    """Copy `data` into fresh global memory and give that to the clipboard under
    `clipboard_format`. The clipboard owns the memory once it has taken it, so it
    is freed here only when it was not taken."""
    handle = api.alloc(len(data))
    if not handle:
        return False
    taken = False
    try:
        address = api.lock(handle)
        if not address:
            return False
        try:
            api.copy(address, data)
        finally:
            api.unlock(handle)
        taken = bool(api.set_data(clipboard_format, handle))
        return taken
    finally:
        if not taken:
            api.free(handle)


class _Win32Api:
    """The Windows functions copy_rich needs, one method each. The argument and
    result types are set on every function, and that matters: ctypes takes
    everything to be a 32-bit int unless told otherwise, and a memory address cut
    to 32 bits corrupts memory (or crashes) on 64-bit Windows."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard.argtypes = []
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.CloseClipboard.argtypes = []
        user32.CloseClipboard.restype = wintypes.BOOL
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE
        user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
        user32.RegisterClipboardFormatW.restype = wintypes.UINT

        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = wintypes.LPVOID
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalFree.restype = wintypes.HGLOBAL

        self._user32 = user32
        self._kernel32 = kernel32

    def register_format(self, name):
        return self._user32.RegisterClipboardFormatW(name)

    def open(self, owner):
        return self._user32.OpenClipboard(owner)

    def empty(self):
        return self._user32.EmptyClipboard()

    def close(self):
        self._user32.CloseClipboard()

    def alloc(self, size):
        return self._kernel32.GlobalAlloc(_GMEM_MOVEABLE, size)

    def lock(self, handle):
        return self._kernel32.GlobalLock(handle)

    def unlock(self, handle):
        self._kernel32.GlobalUnlock(handle)

    def free(self, handle):
        self._kernel32.GlobalFree(handle)

    def copy(self, address, data):
        self._ctypes.memmove(address, data, len(data))

    def set_data(self, clipboard_format, handle):
        return self._user32.SetClipboardData(clipboard_format, handle)


_api = None


def _windows_api():
    """The real Windows bindings, made the first time they are needed."""
    global _api
    if _api is None:
        _api = _Win32Api()
    return _api