"""Small helpers for the tests that open real CustomTkinter windows.

Each of these used to be copied into every test file that needed it, and the
copies had started to drift apart: the same settle function waited 250, 300 or
800 ms depending on which file it was in. This is the one copy now, and a test
file imports what it needs from here:

    from tk_helpers import all_widgets, cancel_pending_afters, click, settle

This works because pytest adds the tests folder to the import path when it
loads a test file from it. The tests folder has no __init__.py and pytest runs
in its default import mode (see pyproject.toml), so this module is found by its
plain name. Its name doesn't start with test_, so pytest never collects it as a
test file.

click and click_button send a real mouse click to a widget.

settings_window, at the end, builds the Settings window the way most of the
Settings tests need it, so they don't each keep their own list of its settings.

Why these tests need settle() at all: a CTkToplevel on Windows doesn't come up
in one go. Its __init__ hides the window, recolours the title bar and calls
update(), then leaves the rest to a string of timers: 5 ms to put the window
back on screen, 10 ms to give focus back, another 10 ms from resizable() to run
the whole title bar routine a second time, 200 ms to set the icon and 1000 ms to
settle its minimum and maximum size. The app's own dialogs add an 80 ms reveal
on top. In the app that always finishes, because the event loop runs all the
time between a person's clicks. In a test nothing runs the loop unless the
test asks, so a window built and destroyed back to back gets destroyed halfway
through its own startup, and the leftovers land on whichever window happens to
call update() next. settle() is that asking, and it's also why these tests
briefly flash real windows on screen while they run.
"""
import time


def settle(widget, milliseconds=250):
    """Run Tk's event loop for a while, so everything already queued, timers
    included, gets a chance to finish.

    The default is long enough to cover a CTkToplevel's startup (see the note
    at the top of this file), so a window that has been settled is one Tk has
    finished putting up and is safe to look at or destroy. Pass a number when a
    test needs a shorter or longer wait, for example to get past a timer of the
    app's own."""
    end = time.monotonic() + milliseconds / 1000
    while time.monotonic() < end:
        widget.update()
        time.sleep(0.005)


def all_widgets(root):
    """root and every widget below it, depth first."""
    found = [root]
    for child in root.winfo_children():
        found.extend(all_widgets(child))
    return found


def cancel_pending_afters(window):
    """Cancel whatever Tk timers `window`, or anything inside it, still has
    queued. Call it on a settled window that is about to be destroyed. What's
    left by then is the long tail, mainly CTkToplevel's 1000 ms minimum and
    maximum size timer, which would otherwise fire on a widget that's gone.

    Each timer is cancelled through the widget that scheduled it, found by
    matching the timer's Tcl command name against that widget's own
    _tclCommands list. That detail matters. after_cancel deletes the timer's
    Tcl command and takes it off the list of the widget it was called on. So
    cancelling through any other widget deletes the command but leaves it on
    its owner's list, and the owner then fails with "can't delete Tcl command"
    when it's destroyed. Timers that belong to anything outside this window,
    like the main window's own widgets or CustomTkinter's DPI watcher, are left
    alone for the same reason."""
    owner_of = {}
    for widget in all_widgets(window):
        for command_name in (getattr(widget, "_tclCommands", None) or ()):
            owner_of[command_name] = widget

    try:
        pending = window.tk.splitlist(window.tk.call("after", "info"))
    except Exception:
        return
    for after_id in pending:
        try:
            command_name = window.tk.splitlist(window.tk.call("after", "info", after_id))[0]
        except Exception:
            continue
        owner = owner_of.get(command_name)
        if owner is not None:
            try:
                owner.after_cancel(after_id)
            except Exception:
                pass


def click(widget, times=1):
    """Press and let go of the left mouse button over a widget. Twice in a row
    is a double click, which Tk recognises by itself because the two come so
    close together.

    The click has to go to the Tk widget the binding was made on. For a
    CustomTkinter widget that's the one inside it: a CTkLabel's text is
    label._label, and a CTkFrame or CTkButton is drawn on its _canvas. Binding
    to a CustomTkinter widget binds those, so a click sent to the outer widget
    reaches nothing."""
    for _ in range(times):
        widget.event_generate("<Button-1>", x=5, y=5)
        widget.event_generate("<ButtonRelease-1>", x=5, y=5)


def click_button(button):
    """Click a CustomTkinter button. It only counts a click when the pointer has
    come over it first, as a real one always has, and it learns that from its own
    Enter handler. That handler is called here rather than sending an Enter event,
    because on Linux Tk dropped the generated Enter for the second button clicked
    in a window, and that click then did nothing. The press and release are still
    sent as events."""
    button._on_enter()
    click(button._canvas)


def settings_window(owner, **given):
    """A Settings window built straight from the default settings, with
    callbacks that do nothing in place of the app. Pass anything a test needs
    to be different, for example on_apply to see what Apply sends, transcripts
    for the Stats tab, or one of the settings themselves.

    Every SettingsWindow parameter that is also a setting gets its default
    from AppSettings, so a setting added to the window later needs nothing
    here. A name the window doesn't take fails the test straight away."""
    import inspect
    from dataclasses import asdict

    from core.settings_store import AppSettings
    from gui.components.settings_window import SettingsWindow

    defaults = asdict(AppSettings())
    nothing = lambda *args: None
    values = {name: defaults[name] for name in inspect.signature(SettingsWindow).parameters if name in defaults}
    values.update(
        transcripts=[],
        on_apply=nothing,
        on_export_requested=nothing,
        on_import_requested=nothing,
        profile_names=lambda: [],
        on_profile_save=nothing,
        on_profile_update=nothing,
        on_profile_apply=nothing,
        on_profile_rename=nothing,
        on_profile_delete=nothing,
    )
    values.update(given)
    return SettingsWindow(owner, **values)