"""Tests for gui/rich_clipboard.py, the part that puts text and its bold on the
Windows clipboard.

The real Windows calls cannot run here, so the decisions in copy_rich are tested
against a fake that behaves like the clipboard, failures included: busy, out of
memory, a lock that fails, data that is refused. The things that go wrong and
cost something are checked in particular: memory that is never freed, a
clipboard that is never closed, an exception that reaches the caller. The thin
layer of real calls is checked as far as it can be without Windows, which is the
argument and result types, since a pointer cut to 32 bits is the classic mistake
there. What Word then shows is looked at by hand."""

import ctypes
import sys
from types import SimpleNamespace

import pytest

from gui import rich_clipboard
from gui.rich_clipboard import CF_UNICODETEXT, HTML_FORMAT_NAME, copy_rich

HTML_FORMAT = 49999          # what the fake hands out for "HTML Format"
OWNER = 123456


class FakeClipboard:
    """Stands in for the Windows functions, one method each, and keeps count."""

    def __init__(self, busy_for=0, fail=None, register_result=HTML_FORMAT):
        self.busy_for = busy_for          # how many opens are refused before one works
        self.fail = fail                  # name of the step that fails, or None
        self.register_result = register_result
        self.calls = []
        self.opened_by = None
        self.is_open = False
        self.contents = {}                # what the clipboard holds: format -> bytes
        self.memory = {}                  # handle -> bytes, for memory that is allocated
        self.locked = set()
        self.next_handle = 1000
        self.registered = None

    def _step(self, name):
        self.calls.append(name)
        return self.fail != name

    def register_format(self, name):
        self.registered = name
        self.calls.append("register_format")
        return self.register_result

    def open(self, owner):
        self.calls.append("open")
        if self.busy_for:
            self.busy_for -= 1
            return False
        self.opened_by = owner
        self.is_open = True
        return True

    def empty(self):
        assert self.is_open
        self.contents.clear()
        return self._step("empty")

    def close(self):
        self.calls.append("close")
        self.is_open = False

    def alloc(self, size):
        if not self._step("alloc"):
            return 0
        self.next_handle += 1
        self.memory[self.next_handle] = bytearray(size)
        return self.next_handle

    def lock(self, handle):
        assert handle in self.memory, "locking memory that is not allocated"
        if not self._step("lock"):
            return 0
        self.locked.add(handle)
        return handle * 10                # an "address" that maps back to the handle

    def unlock(self, handle):
        self.calls.append("unlock")
        self.locked.discard(handle)

    def free(self, handle):
        self.calls.append("free")
        assert handle in self.memory, "freeing memory that is not allocated, or twice"
        assert handle not in self.locked, "freeing memory that is still locked"
        del self.memory[handle]

    def copy(self, address, data):
        if not self._step("copy"):
            raise OSError("copy failed")
        buffer = self.memory[address // 10]
        assert len(data) == len(buffer), "copied a different amount than was allocated"
        buffer[:] = data

    def set_data(self, clipboard_format, handle):
        assert self.is_open, "storing on a clipboard that is not open"
        assert handle not in self.locked, "handing over memory that is still locked"
        if not self._step("set_data"):
            return 0
        # The clipboard owns the memory from here on.
        self.contents[clipboard_format] = bytes(self.memory.pop(handle))
        return handle

    def leaked(self):
        """Memory that was allocated and neither given to the clipboard nor freed."""
        return list(self.memory)


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    waits = []
    monkeypatch.setattr(rich_clipboard.time, "sleep", waits.append)
    return waits


def run(fake, plain="hello", html=b"<p>hello</p>"):
    return copy_rich(OWNER, plain, html, api=fake)


# ---- a copy that works ----

def test_both_formats_end_up_on_the_clipboard():
    fake = FakeClipboard()
    assert run(fake, "one\ntwo", b"<html>") is True
    assert set(fake.contents) == {CF_UNICODETEXT, HTML_FORMAT}
    assert fake.contents[CF_UNICODETEXT] == "one\r\ntwo".encode("utf-16-le") + b"\0\0"
    assert fake.contents[HTML_FORMAT] == b"<html>\0"
    assert fake.leaked() == []

def test_the_plain_text_format_is_the_number_windows_gives_it():
    # Fixed by Windows (CF_UNICODETEXT), not something this code may choose.
    assert CF_UNICODETEXT == 13

def test_the_html_format_is_asked_for_by_its_name():
    fake = FakeClipboard()
    run(fake)
    assert fake.registered == HTML_FORMAT_NAME == "HTML Format"

def test_the_clipboard_is_opened_with_the_owner_given_and_closed_afterwards():
    fake = FakeClipboard()
    run(fake)
    assert fake.opened_by == OWNER
    assert fake.is_open is False
    assert fake.calls.count("open") == 1 and fake.calls.count("close") == 1

def test_the_order_is_open_then_empty_then_text_then_html_then_close():
    fake = FakeClipboard()
    run(fake)
    calls = fake.calls
    assert calls[:3] == ["register_format", "open", "empty"]
    assert calls[-1] == "close"
    stored = [call for call in calls if call == "set_data"]
    assert len(stored) == 2
    assert list(fake.contents) == [CF_UNICODETEXT, HTML_FORMAT]     # text went first

def test_every_piece_of_memory_is_unlocked_before_it_is_handed_over():
    fake = FakeClipboard()
    run(fake)
    assert fake.calls.count("lock") == 2 and fake.calls.count("unlock") == 2
    assert fake.locked == set()

def test_the_plain_text_gets_windows_line_endings_without_doubling_them():
    for plain, wanted in [("a\nb", "a\r\nb"), ("a\r\nb", "a\r\nb"), ("a\n\nb\n", "a\r\n\r\nb\r\n"), ("", "")]:
        fake = FakeClipboard()
        run(fake, plain)
        assert fake.contents[CF_UNICODETEXT] == wanted.encode("utf-16-le") + b"\0\0"

def test_cyrillic_and_emoji_are_stored_as_utf16_and_end_in_a_zero():
    fake = FakeClipboard()
    text = "Привет \U0001F600"
    run(fake, text)
    stored = fake.contents[CF_UNICODETEXT]
    assert stored.endswith(b"\0\0")
    assert stored[:-2].decode("utf-16-le") == text
    assert len(stored) % 2 == 0


# ---- a busy clipboard ----

def test_a_clipboard_that_is_busy_for_a_moment_is_tried_again(no_waiting):
    fake = FakeClipboard(busy_for=2)
    assert run(fake) is True
    assert fake.calls.count("open") == 3
    assert len(no_waiting) == 2

def test_a_clipboard_that_stays_busy_is_given_up_on_without_touching_it(no_waiting):
    fake = FakeClipboard(busy_for=100)
    assert run(fake) is False
    assert fake.calls.count("open") == rich_clipboard._OPEN_TRIES
    assert len(no_waiting) == rich_clipboard._OPEN_TRIES - 1
    assert "empty" not in fake.calls and "close" not in fake.calls     # it was never opened
    assert fake.contents == {} and fake.leaked() == []


# ---- things that fail ----

@pytest.mark.parametrize("step", ["empty", "alloc", "lock", "copy", "set_data"])
def test_a_failing_step_gives_false_closes_the_clipboard_and_leaks_nothing(step):
    fake = FakeClipboard(fail=step)
    assert run(fake) is False
    assert fake.is_open is False and fake.calls.count("close") == 1
    assert fake.leaked() == []
    assert fake.locked == set()

def test_a_failing_copy_does_not_raise():
    fake = FakeClipboard(fail="copy")
    run(fake)                                       # an OSError inside must not get out

def test_when_only_the_html_is_refused_it_still_says_false_and_leaks_nothing():
    class RefusesHtml(FakeClipboard):
        def set_data(self, clipboard_format, handle):
            if clipboard_format == HTML_FORMAT:
                self.calls.append("set_data")
                return 0
            return super().set_data(clipboard_format, handle)

    fake = RefusesHtml()
    assert run(fake) is False
    assert CF_UNICODETEXT in fake.contents and HTML_FORMAT not in fake.contents
    assert fake.leaked() == [] and fake.is_open is False

def test_when_the_html_format_cannot_be_registered_the_clipboard_is_left_alone():
    fake = FakeClipboard(register_result=0)
    assert run(fake) is False
    assert "open" not in fake.calls

def test_text_that_cannot_be_encoded_is_refused_before_the_clipboard_is_touched():
    fake = FakeClipboard()
    assert run(fake, "broken \ud800 text") is False
    assert "open" not in fake.calls and "empty" not in fake.calls

def test_a_clipboard_that_raises_while_open_is_still_closed():
    class Explodes(FakeClipboard):
        def empty(self):
            raise RuntimeError("boom")

    fake = Explodes()
    assert run(fake) is False
    assert fake.is_open is False


# ---- not on Windows ----

def test_without_windows_nothing_is_attempted(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(rich_clipboard, "_windows_api", lambda: pytest.fail("looked for Windows"))
    assert copy_rich(OWNER, "text", b"<html>") is False


# ---- the real Windows layer, as far as it can be checked here ----

class _FakeFunction:
    """Stands in for a function of a DLL: accepts argtypes and restype, records calls."""

    def __init__(self, name, log, result=1):
        self.name, self.log, self.result = name, log, result
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        self.log.append((self.name, args))
        return self.result


class _FakeDll:
    def __init__(self, log):
        self._log = log
        self._functions = {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._functions.setdefault(name, _FakeFunction(name, self._log))


@pytest.fixture
def real_layer(monkeypatch):
    log = []
    dlls = {}

    def win_dll(name, use_last_error=False):
        return dlls.setdefault(name, _FakeDll(log))

    monkeypatch.setattr(ctypes, "WinDLL", win_dll, raising=False)
    return rich_clipboard._Win32Api(), dlls, log

def test_the_real_layer_gives_every_function_pointer_sized_types(real_layer):
    api, dlls, log = real_layer
    user32, kernel32 = dlls["user32"], dlls["kernel32"]
    pointer = ctypes.c_void_p
    assert user32.OpenClipboard.argtypes == [pointer]
    assert user32.SetClipboardData.argtypes == [ctypes.c_uint, pointer]
    assert user32.SetClipboardData.restype is pointer
    assert user32.RegisterClipboardFormatW.argtypes == [ctypes.c_wchar_p]
    assert user32.RegisterClipboardFormatW.restype is ctypes.c_uint
    assert kernel32.GlobalAlloc.argtypes == [ctypes.c_uint, ctypes.c_size_t]
    assert kernel32.GlobalAlloc.restype is pointer
    assert kernel32.GlobalLock.argtypes == [pointer]
    assert kernel32.GlobalLock.restype is pointer
    assert kernel32.GlobalUnlock.argtypes == [pointer]
    assert kernel32.GlobalFree.argtypes == [pointer]
    assert kernel32.GlobalFree.restype is pointer

def test_every_function_the_real_layer_calls_has_types_set(real_layer):
    api, dlls, log = real_layer
    api.register_format("x"); api.open(1); api.empty(); api.close()
    api.alloc(8); api.lock(1); api.unlock(1); api.free(1); api.set_data(13, 1)
    called = {name for name, _ in log}
    assert called == {
        "RegisterClipboardFormatW", "OpenClipboard", "EmptyClipboard", "CloseClipboard",
        "GlobalAlloc", "GlobalLock", "GlobalUnlock", "GlobalFree", "SetClipboardData",
    }
    for dll in dlls.values():
        for function in dll._functions.values():
            assert function.argtypes is not None and function.restype is not None, function.name

def test_the_real_layer_passes_things_through_to_the_right_functions(real_layer):
    api, dlls, log = real_layer
    api.open(77)
    api.alloc(10)
    api.set_data(13, 555)
    api.register_format("HTML Format")
    assert log == [
        ("OpenClipboard", (77,)),
        ("GlobalAlloc", (0x0002, 10)),
        ("SetClipboardData", (13, 555)),
        ("RegisterClipboardFormatW", ("HTML Format",)),
    ]

def test_the_real_layer_copies_bytes_to_the_address_it_is_given(real_layer):
    api, dlls, log = real_layer
    buffer = ctypes.create_string_buffer(6)
    api.copy(ctypes.addressof(buffer), b"abcdef")
    assert buffer.raw == b"abcdef"

def test_the_real_layer_is_made_once(monkeypatch):
    made = []
    monkeypatch.setattr(rich_clipboard, "_Win32Api", lambda: made.append(1) or SimpleNamespace())
    monkeypatch.setattr(rich_clipboard, "_api", None)
    first = rich_clipboard._windows_api()
    assert rich_clipboard._windows_api() is first
    assert made == [1]