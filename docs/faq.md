# FAQ

Common questions about installing, using, and troubleshooting RSVP Desktop
Reader. For full details, the [Installation](installation.md),
[Usage](usage.md), and [Data and export format](data.md) pages go deeper.

## Installing and running

### The app won't start and I see "No module named 'tkinter'"

Tkinter is the GUI toolkit the app is built on. It ships with Python on Windows,
but on macOS and Linux it is usually a separate package.

- macOS (Homebrew Python): `brew install python-tk@3.13`
- Debian or Ubuntu: `sudo apt install python3-tk`
- Fedora: `sudo dnf install python3-tkinter`
- Arch: `sudo pacman -S tk`

Install it before creating your virtual environment, then rebuild the venv. The
full per-platform steps are on the [Installation](installation.md) page.

### "No module named customtkinter" (or a version error)

The dependencies did not install into the interpreter you are running the app
with. This almost always means `pip` and `python` point at different places.
Activate your virtual environment, then install with the module form so they
stay in sync:

```bash
python -m pip install -r requirements.txt
```

You can confirm the environment is healthy with:

```bash
python -c "import tkinter; print('Tk:', tkinter.TkVersion)"
python -c "import customtkinter; print('CustomTkinter:', customtkinter.__version__)"
```

Both should print a version with no error.

### Which Python version do I need?

Python 3.10 or newer. The app is developed and built on 3.13, which is the
safest choice if you are installing fresh.

### Is there a prebuilt download, or do I have to run from source?

Both. Tagged releases include prebuilt bundles built automatically: a Windows
`.zip` and a Linux `.tar.gz`, downloadable from the project's Releases. A macOS
build is not finished yet, so on macOS run from source for now (see
[Installation](installation.md)). Running from source works on all three
platforms.

### Does it need an internet connection?

No. The app is fully offline. Nothing it does requires a network, and the two
fonts it uses (Fredoka and Quicksand) are bundled in the repo and registered at
launch, so there is nothing extra to download.

## Getting text in

### What file types can I import?

Plain text (`.txt`), subtitles (`.srt`, `.vtt`), Markdown (`.md`, `.markdown`),
HTML (`.html`, `.htm`), Word (`.docx`), and PDF (`.pdf`). Click **+** in the
sidebar and choose **Add from file**.

### I imported a big file and got a warning, or it crashed

If a file comes in at more than about 30,000 words, the app shows a heads-up
that very large transcripts have been known to crash it. That is a warning, not
a hard limit, so you can continue, but if it does crash, split the file into
smaller parts and import those. Importing is also a single blocking step, so the
window will not respond while a large file is being read; give it a moment.

### What happened to the timestamps in my transcript?

They are stripped automatically on import. Subtitle timing lines, bracketed or
parenthesized times, and bare timestamps on their own line are all removed so
only the words are read. A time written inside a sentence, like "we met at
10:30", is left alone.

### Can I read only part of a transcript?

Yes. In the edit box, select the portion you want, right-click it, and choose
**Play** to read just that selection, or **Detach** to read it in its own
window. Selection reading never changes the transcript's saved text, position,
or stats.

### How do I edit a transcript after I've started reading it?

Click **Stop** (or press **Esc**). That ends the session and drops you back to
the edit box with the transcript's saved text, where you can change it and click
**Start reading** again. Note that stopping replaces whatever is in the box with
the saved text.

### What does the Normalize button do, and can I undo it?

It tidies the layout of the text in the edit box: removing list markers and page
numbers, stripping any leftover timestamps, rejoining lines broken mid-sentence,
and repairing common PDF extraction damage. It is a toggle, so clicking it again
reverts, as long as you have not edited the box in between. It only changes how
the text is laid out, never which words get read. Optionally (a setting, off by
default) it also splits very long walls of text into paragraphs.

## Reading and controls

### How do I skip forward or back? I don't see any buttons

In the main window, skipping is done with the **left and right arrow keys**,
there are no skip buttons on the main toolbar. The detached window does have
dedicated skip buttons. How far a skip moves is set by the skip amount in
Settings (ten words by default), and you can optionally have it pause on the
word it lands on.

### How do I add and jump to bookmarks?

Press **B** while a word is on screen to bookmark it (or remove a bookmark
already there), or use the toggle in the Bookmarks popover. Bookmarks appear as
small ticks under the progress bar and as rows in the popover. In the popover,
single-click a row to jump to that word, and double-click it to rename it.

### Why can't I turn on focus mode in the detached window?

On purpose. Focus mode hides the sidebar and app chrome, and the detached window
has none of that to hide, so the feature would do nothing there. It is available
in the main window only.

### What are the keyboard shortcuts?

Space to play or pause, left and right arrows to skip, R to restart, B to
bookmark the current word, Esc to stop, and F for focus mode (main window only).
Shortcuts are ignored while you are typing in a text field. The full table is on
the [Usage](usage.md) page.

## Settings and appearance

### I changed the theme but nothing happened

The Light / Dark / System theme takes effect the next time you launch the app,
not immediately. Close and reopen it to see the change.

### I switched to Dark theme but my reading colors didn't change

A transcript's reading colors (word, highlight, background) come from the
Defaults in Settings, not from the theme, so they do not automatically follow
Light or Dark. Adjust them under Settings, in the Defaults tab, for new
transcripts, or change them per transcript from the control band at the bottom
of the window.

### How do I change speed or colors for one transcript versus all new ones?

For the transcript you are reading, use the control band at the bottom of the
window; those changes apply to that transcript only. For every transcript you
create from now on, use the Defaults tab in Settings. Changing the defaults does
not touch transcripts you already have.

### The vertical guide marks don't show up

First, make sure you are on the latest version: a display-scaling bug that hid
the marks at 125% was fixed in v2.10.1. Also check that the guide-mark thickness
in Settings is not set to its minimum on a display where that renders too thin;
the allowed range is 2 to 6 pixels. The marks also only appear while words are
actively flashing, and disappear when you pause or stop.

## Data, backups, and moving machines

### Where is my data stored?

Your transcripts and Spaces live in `data.json`, inside your data directory,
which defaults to `~/.rsvp_reader`. Your settings live in `settings.json`, which
always stays in `~/.rsvp_reader` even if you move the data directory elsewhere.
Full details are on the [Data and export format](data.md) page.

### How do I back up my transcripts?

Copy `data.json` somewhere safe (and `settings.json` too if you want your
preferences). Or, from Settings under Storage, use **Export Data** to write a
single bundle file containing everything.

### How do I move everything to another computer?

Use **Export Data** on the old machine and **Import Data** on the new one,
rather than copying raw files, so machine-specific paths are handled correctly.
On import you choose **Replace** (wipe this machine and load the bundle) or
**Expand** (add the bundle's transcripts and Spaces to what is already here).
The app closes after an import, so reopen it to see the result.

### Can I change where my data is saved?

Yes. In Settings, under Storage, use **Choose folder**. The change takes effect
when you click Apply. Only `data.json` moves to the new folder; `settings.json`
stays in `~/.rsvp_reader`, since it is what records where the data folder is.

### Will updating the app lose my data?

No. The save format is designed to be forgiving across versions: fields added in
newer versions are filled in with defaults on older save files, and fields the
app does not recognize are ignored. Export bundles carry a format version and
refuse to import if it does not match, rather than misreading your data.

### I edited the JSON by hand and lost data

The files are plain JSON and you can edit them, but close the app first. It
overwrites these files as you use it and saves again on close, so edits made
while it is open are lost. A malformed file is treated as "no save yet" and
falls back to defaults rather than crashing, which is safe but means a bad edit
can wipe what was there. Always keep a copy before editing.

### Is any of my data sent anywhere?

No. Everything stays on your machine. The app is fully offline and has no
telemetry or accounts.

## Platform notes

### macOS

There is no finished macOS build yet, so run from source following the
[Installation](installation.md) page. The key extra step on macOS is installing
Tkinter separately with `brew install python-tk@3.13` and building the virtual
environment with the full interpreter path, so it uses the Python you installed
Tkinter for.

### Do I need to install the fonts?

No. Fredoka and Quicksand are bundled with the app in `assets/fonts/` and
registered automatically, just for the app, when it launches. They are not
installed system-wide and need nothing from you.