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

No. The app is fully offline. Nothing it does requires a network, and the fonts
it uses (Fredoka and Quicksand, plus OpenDyslexic if you turn it on) are bundled
in the repo, so there is nothing extra to download.

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

### What does the bold button next to Normalize do?

It makes the start of every word in the edit box bold, so each word begins with
a stronger anchor. Click it again to turn it off. Short words get their first
letter or two in bold and longer ones up to six, so "hello world" shows as
**hel**lo **wor**ld. It only changes how the text looks: the words are never
touched, so saving, **Start reading** and Normalize's undo all work as before,
and the reader itself is not affected.

The choice is remembered between launches, and it works with the OpenDyslexic
font too. In the main window and in the window opened by a transcript's
**Detach** button it is one setting, so a click in either changes both. A window
that plays or detaches a selection opens with the look the app has at that
moment, and its own button changes only that window.

A few things are left plain on purpose: web and email addresses, words with a
digit stuck to them (3rd, H2O), and letters outside the Latin, Cyrillic and
Greek scripts. Hyphenated words get bold on each part, as in
**we**ll-**kno**wn. A line longer than about 4,000 characters (roughly 650
words) stays plain too, because bolding a line that long makes the box slow to
type in. That usually means text pasted as one huge paragraph. The box says "Long
lines stay plain" when it happens, and splitting the text into shorter lines
brings the bold back.

### How do I copy text with its bold into Word?

With the bold look on, select text in the edit box and press **Ctrl+C**, or
right-click and choose **Copy with bold**. Paste into Word and the bold comes
along. Word uses its own font and spacing, so only the bold carries over.
Copying a very large selection, a whole book say, can take a few seconds.

Programs that only take plain text, Notepad for one, get the same words without
the bold, because a plain-text field has no way to hold it. That is expected and
not a fault. **Ctrl+X** always cuts plain text, and with the look off a copy is
the ordinary plain copy. Copying with bold works on Windows; on macOS and Linux
a copy is plain. After the right-click choice, a short note at the end of the
button row says "Copied with bold" or, when the bold could not go along,
"Copied without bold" (the words are copied either way).

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

### The words look smaller than my Word size, or a scrollbar appeared

That is auto-fit. When the widest flash in a transcript, usually a multi-word
group at a large Word size, would run past the edges of the reading area, the
reader draws the words a little smaller so they fit. Letter spacing makes every
flash wider too, so turning it up can bring this on sooner. Your Word size
setting is not changed, and the words return to full size when everything fits
again, for example with a smaller group or a wider window. Auto-fit never goes
below 60% of your Word size. If a flash is still too wide at that point, a
horizontal scrollbar appears along the bottom so you can slide the words into
view. The small button above it, or the **C** key, snaps them back to the
centre. See [Wide flashes](usage.md#wide-flashes-auto-fit-and-the-scrollbar) for
the full picture.

### Why can't I turn on focus mode in the detached window?

On purpose. Focus mode hides the sidebar and app chrome, and the detached window
has none of that to hide, so the feature would do nothing there. It is available
in the main window only.

### What are the keyboard shortcuts?

Space to play or pause, left and right arrows to skip, up and down arrows to
make the transcript 10 WPM faster or slower, R to restart, B to bookmark the
current word, C to centre the words after panning with the horizontal
scrollbar, Esc to stop, and F for focus mode (main window only). Shortcuts are
ignored while you are typing in a text field. In the popups and in Settings, Esc
closes or cancels, and Enter confirms where there is one clear thing to do. The
full table is on the [Usage](usage.md#keyboard-shortcuts) page.

### I detached a transcript and opened another one. Which one do the keys control?

The one open in the main window. While a transcript is detached you can read a
different one in the main window, and the main window's keys, toolbar and bottom
band work on that one, leaving the detached window alone. The detached window's
own keys and buttons always work on its own transcript. Open the detached
transcript in the main window again (the "detached" placeholder shows) and the
main window's keys go back to controlling the detached window.

## Settings and appearance

### How do I find a setting?

The Defaults tab in Settings has a **Search settings...** box at the top. Type a
word from the setting's name (or a related word like "colour" or "crosshair")
and the list narrows as you type; the button beside the box also searches each
setting's description when you turn it on. Clear the box with the **X** at its
right to bring the full list, and the **Reset to Original Defaults** button,
back.

### Which version am I running?

Open **Settings** and click the small round **i** button at the top right. The
About dialog shows the version number, the license, and a link to the project
page on GitHub, where the Releases section lists the newest version.
*This is only for v3.3.0 onwards*

### What is a reading profile, and how do I use one?

A profile is a saved set of reader settings, so you can switch between ways of
reading in one click. Set things up the way you like in Settings, open the
**Profiles** tab, click **Save current settings as...** and give it a name. Later,
select it in the list and press **Apply**. It takes effect straight away and
Settings closes. A profile holds the guide marks, pacing, rewind on resume,
surrounding words, skipping, the +/- step, the scrubber and paragraph switches,
the letter spacing, and the Speed and Word size sliders. It does not hold the
OpenDyslexic font switch, because a font only changes when the app starts. The
full list is under [Profiles](usage.md#profiles) on the Usage page.

### I applied a profile, but my open transcript's speed and size did not change

On purpose. A profile's Speed and Word size are the two sliders at the top of
the Defaults tab, which only decide where *new* transcripts start. Applying a
profile never touches a transcript, so the one you have open keeps its own speed
and size. To change those for the transcript you are reading, use the control
band at the bottom of the window. Open Settings after applying and you will see
the sliders on the Defaults tab have moved.

### I applied a profile, but my colours did not change

Profiles leave colours alone, and chunking too, so applying one never repaints
your reader. The only colour a profile carries is the guide mark colour. If you
want different colours for different texts, set them per transcript from the
control band, or keep those texts in separate [Spaces](usage.md#spaces).

### An older profile does not move Speed, Word size, the step, the switches or the letter spacing

Profiles saved before those settings joined do not hold them, and a profile only
changes what it holds, so applying one leaves them as they are. That covers
Speed, Word size, the +/- step and the scrubber and paragraph switches for the
oldest profiles, and the letter spacing for any profile saved before version
3.6.0. Select the profile, set Settings the way you want, and press **Update**
once to bring them in.

### If I change a setting afterwards, does the saved profile change?

No. A profile is a snapshot. Changing a setting later leaves the saved profile
as it was, and applying a profile copies its values in. To bring a profile up to
date, set things the way you want and press **Update**.

### Do my profiles come along when I move to another computer?

Yes. Profiles are saved in `settings.json`, so **Export Data** carries them in
the bundle. On the other machine, **Replace** brings them in with the rest of the
settings, and **Expand** leaves your settings, profiles included, as they are.

### I changed the theme but nothing happened

The Light / Dark / System theme takes effect the next time you launch the app,
not immediately. Close and reopen it to see the change.

### What does the OpenDyslexic font switch do?

On the **Appearance** tab in Settings, **Use the OpenDyslexic font** changes
every font in the app, not only the reader, to OpenDyslexic, a typeface released
under the SIL Open Font License. It takes effect the next time you launch the
app, like the colour theme, and it is not saved in reading profiles, because a
profile applies on the spot and a font cannot change that way. On Windows the app
loads the font files from `assets/fonts/` itself. On macOS and Linux it cannot,
so install OpenDyslexic on your system first (the files are in that folder),
otherwise the text is drawn in a stand-in font. The switch is saved when you
press **Apply**.

### I turned on the OpenDyslexic font but nothing changed

Three things to check. The font only changes at startup, so close the app and
open it again. On macOS and Linux the font has to be installed on your system
first, since the app cannot load its own font files there. And if the Appearance
tab says the OpenDyslexic font files weren't found, the app has put the standard
fonts back for now: check that `OpenDyslexic3-Regular.ttf` and
`OpenDyslexic3-Bold.ttf` are in the app's `assets/fonts/` folder.

### What does letter spacing do?

It adds a little room between the letters of the flashing word, with four levels
on the Appearance tab: Off (the default), Small, Medium and Large. In chunk mode
the gaps between the words of a group are widened where needed, so the words do
not run together. The highlighted letter stays on its usual point, and the
surrounding-words line is left as it is. It applies as soon as you press
**Apply**, in the main window and in the detached window, and it is saved in
reading profiles. A window that plays a selection keeps the level it was opened
with. Wider words need more room, so with spacing turned up the words may be
drawn a little smaller, or the scrollbar may appear sooner. See
[Wide flashes](usage.md#wide-flashes-auto-fit-and-the-scrollbar).

### Do the OpenDyslexic font and letter spacing actually help?

The app does not claim they do, and neither is a treatment for dyslexia. They are
optional, for people who find them easier on the eyes, and the research so far is
mixed. A study of OpenDyslexic found no improvement in reading rate or accuracy
(Wery and Diliberto, *Annals of Dyslexia*, 2017, [full
text](https://pmc.ncbi.nlm.nih.gov/articles/PMC5629233)). Wider spacing has had
better results: children with dyslexia read sentences faster and with fewer
mistakes when the letters were spaced further apart (Zorzi and others, *PNAS*,
2012, [doi:10.1073/pnas.1205566109](https://doi.org/10.1073/pnas.1205566109)),
and another study found that the benefit of a font made for dyslexia came from
its wider spacing, not the shape of its letters (Marinus and others,
*Dyslexia*, 2016). Those studies used running text, not words flashed one at a
time, so how much any of this carries over to an RSVP reader is not known. Try
the levels by eye, and keep whatever feels comfortable.

### Does bold word starts actually help?

The app does not claim it does. It is an optional look, off by default, for
people who find it easier to follow. The studies so far do not show a gain in
speed or understanding, and they did not test RSVP, so they cannot say much
about this app. Three that used eye trackers:

- Beelders, *Journal of Eye Movement Research*, 2025
  ([doi:10.3390/jemr18050049](https://doi.org/10.3390/jemr18050049)): 53 adults
  read at 131.1 words per minute in plain text and 130.8 with bold word starts,
  and their eyes did not move toward the word starts.
- Možina and others, *Sage Open*, 2025
  ([doi:10.1177/21582440251376158](https://doi.org/10.1177/21582440251376158)):
  114 adults. On screen the bold text took slightly longer to read (37.6
  against 36.6 seconds per text), and comprehension did not differ overall.
- Parker and others, *Royal Society Open Science*, 2026, a registered report
  with 90 skilled readers reading single sentences: the bold pulled the first
  look toward the start of long words, but reading time and comprehension did
  not change, and readers rated plain text as more readable.

None of these tested readers with dyslexia or ADHD, so what bold word starts
does for them is not known. Try it by eye, and keep it only if it feels
comfortable.

### Is this the same as Bionic Reading?

It is a similar look, but this app is not made by, affiliated with or endorsed
by the people behind it. "Bionic Reading" is a trademark of BRCG Casutt GmbH,
and the company says the method is also protected by patents and copyright. The
app has its own rules for where the bold goes and does not use that company's
software or name, which is why the feature is called bold word starts. This is
not legal advice.

### I switched to Dark theme but my reading colors didn't change

They change the next time you start the app, like the rest of the theme. A
transcript's reading colors (word, highlight, background) each follow the theme
until you pick that color yourself from the control band at the bottom of the
window, so a color you changed by hand stays as you set it in both themes. In
Light the colors come from the Defaults tab, and in Dark from the app's own
dark reading colors.

### How do I change speed or colors for one transcript versus all new ones?

For the transcript you are reading, use the control band at the bottom of the
window, or the up and down arrow keys for the speed; those changes apply to that
transcript only. For every transcript you
create from now on, use the Defaults tab in Settings. Changing the defaults does
not touch transcripts you already have.

### The vertical guide marks don't show up

First, make sure you are on the latest version: a display-scaling bug that hid
the marks at 125% was fixed in v2.10.1. Also check that the guide-mark thickness
in Settings is not set to its minimum on a display where that renders too thin;
the allowed range is 2 to 6 pixels. The marks also only appear while words are
actively flashing, and disappear when you pause or stop.

### The app opened my last transcript when it started. Can I turn that off?

Yes. That is **Reopen the last transcript at launch**, in Settings under
Defaults, on by default. When it is on, the transcript comes back paused at the
same word, so nothing plays until you press Play. The app also remembers the
main window's size, place and whether it was maximized, and the order you picked
for the sidebar list.

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
while it is open are lost. A file the app cannot read is not thrown away: it is
copied to a new name next to it, such as `data.damaged-20261029-153012.json`,
before anything is saved over it, and the app tells you when it starts. Fix the
copy and put it back while the app is closed. Still, keep your own copy before
editing. The details are under
[If a file cannot be read](data.md#if-a-file-cannot-be-read).

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

On Windows, no. Fredoka and Quicksand (and OpenDyslexic, if you turn it on) are
bundled with the app in `assets/fonts/`, and the app registers the ones it needs
itself, just for the app, when it launches. They are not installed system-wide
and need nothing from you.

On macOS and Linux the app cannot load its own font files, so it uses the fonts
installed on your system. Without Fredoka and Quicksand installed the app still
works, and the text is drawn in a stand-in font, so it only looks different. For
the OpenDyslexic switch to do anything, install OpenDyslexic first. Install the
files from `assets/fonts/` the way you would install any font on your system.