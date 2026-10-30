# Architecture

RSVP Desktop Reader is built in two layers with a strict one-way dependency: a
pure-logic core under `core/`, and a CustomTkinter interface under `gui/`.
Nothing in `core/` imports anything from `gui/`. The GUI imports freely from the
core; the core never reaches back. That single rule is the backbone of the
whole project. It is why the reading engine can be tested without ever opening a
window, and why the interface can be rebuilt or replaced without touching the
logic underneath it.

`main.py` is the entry point. It constructs the main application window and
starts the event loop; everything else hangs off that.

## The core layer

Everything in `core/` is plain Python with no knowledge of widgets, windows, or
timers. It can be imported and exercised in isolation, which is exactly how the
test suite treats it.

### The reading pipeline

Turning a block of raw text into a sequence of flashable words happens in a
short, fixed pipeline, assembled once when a reading session is created.

- `parser.py` cleans the text and strips timestamps. For reading it flattens the
  text into a continuous stream; a separate line-preserving pass is used at
  import time so the edit box can keep its structure.
- `tokenizer.py` splits the cleaned text into individual word tokens. It is
  deliberately tiny, a whitespace split, because all the interesting work
  happens per word afterward.
- `punctuation.py` separates each token into leading punctuation, a core word,
  and trailing punctuation, and classifies the pause that should follow it
  (sentence, clause, or none).
- `orp.py` finds the Optimal Recognition Point letter for a word and splits it
  into the part before the focus letter, the focus letter itself, and the part
  after. A token that is only punctuation degrades gracefully rather than
  crashing.
- `timing.py` converts words per minute into a base per-word delay and holds the
  pause multipliers: the sentence and clause pauses, the optional long-word
  pacing, and the start-of-session warm-up ramp.

`reader.py` ties these together in `ReaderSession`, the heart of the engine.
When a session is built from a transcript's text, it runs that whole pipeline
in one pass, producing three parallel, fixed-length lists: the ORP-split word
frames, their pause classes, and their length bands. From those it pre-sums the
pacing multipliers from each position to the end, so asking how much reading
time remains is an O(1) lookup rather than a walk over the rest of the
transcript. After construction, the only thing that moves is the current index.

`ReaderSession` is pure and synchronous. It exposes the current word's frame,
the delay that word should stay on screen, the estimated time remaining, the
surrounding words for the peripheral ribbon, and position controls to advance,
seek by a delta, seek to an absolute word, or reset to the top. It owns no timer
of its own. The passage of time is the GUI's job.

### State and persistence

- `models.py` defines the `Transcript` data model: its text and in-progress
  draft, its reading position, its own speed, colors, and font size, its
  bookmarks, its reading stats, and which Space it belongs to.
- `storage.py` is the low-level JSON read and write, and the home of the default
  data location (`~/.rsvp_reader`). It also keeps a copy of a save file that
  cannot be read, under a new name next to it, before anything can save over
  it (`keep_damaged_copy()`), and both stores report such a file so the app can
  say so at launch.
- `transcript_store.py` holds all transcripts and Spaces in memory and persists
  them through `storage`. Live edits such as a position change save on a
  throttle so rapid updates do not hammer the disk, and an explicit flush forces
  a write when a session ends.
- `settings_store.py` does the same for application settings: the new-transcript
  defaults, layout sizes, data location, theme, the font switch, the letter
  spacing level, the bold word starts choice, the saved reading profiles, and
  what the app remembers between launches (the last open transcript, the
  window's size and place, and the sidebar's sort order).
- `data_bundle.py` builds and applies the single-file export used to move
  transcripts, Spaces, and settings between machines, deliberately leaving the
  machine-specific data path out of the bundle.

### Picking up where you left off

Three small modules hold the rules for what the app remembers between launches,
so they are tested without a window. `reopen.py` decides which transcript to
open at launch, if any. `window_placement.py` turns the saved size, position and
maximized state back into a window geometry, and decides whether a saved
position is still on a screen (the GUI says which points are, since only it can
ask the system). `transcript_sort.py` holds the sidebar's six sort orders, each
under a short id that is what gets saved, so a menu label can change without
anyone's saved choice being lost.

### Reading profiles

A reading profile is a named snapshot of the app-wide settings, and the two
pieces of logic behind it are both pure.

`profiles.py` holds the rules. It lists which settings a profile may hold (the
guide marks, pacing, rewind, surrounding words, skipping, the +/- step, the
scrubber and paragraph switches, the letter spacing level, and the Speed and
Word size defaults), checks that a value is the right kind for its setting, and
decides what makes a good name: trimmed, at most 30 characters, unique without
regard to capitals. It also loads saved profiles forgivingly. A damaged entry is
dropped, an unknown or invalid key inside a profile is ignored, and a key that
is missing from a profile means "leave that setting alone". That last rule is
what keeps a profile saved by an older version working after a newer version
adds a setting. What a profile does not hold is as deliberate as what it does:
no transcript values, no Defaults colours, no chunking, no layout, data location
or theme, and no font switch. The font is only read once at startup, so a
profile could not switch it on the spot the way it does everything else.

`profile_apply.py` works out what applying a profile does, without doing it.
Given the profile's values and the current settings, it hands back the complete
set of values the app should end up with: numbers are clamped to the same ranges
the Settings window enforces, anything the profile does not hold is filled in
from the current settings, and the guide mark colour is resolved against the
theme. A profile stores nothing for a guide mark colour that was still following
the Light / Dark theme when it was saved (it stores a null for it), so applying
it gives the current theme's colour and keeps it following, while a colour
picked by hand is applied as picked. `SettingsStore` keeps a flag for that
distinction and a setter, `restore_guide_mark_color`, that can turn it back on.

The saved profiles themselves are a list in `settings.json`, managed through
`SettingsStore`'s add, update, rename and delete methods, so the export bundle
carries them without any extra code.

### Display geometry

`scroll.py` is the arithmetic behind the reader's horizontal scrollbar. When a
flash is still wider than the reading row after the font has been fitted, the
display pans by a pixel offset added to its centre anchor. `scroll.py` holds the
pure pieces of that: how far the offset can travel, clamping it to that range,
and converting between the pixel offset and the pair of fractions a scrollbar
uses to size and place its thumb. It has no widgets in it, so it is tested
without a display like the rest of the core.

`text_fit.py` shortens a line of text with an ellipsis to fit a width, which the
header uses for a long transcript title. It never measures anything itself: the
caller hands it a function that does.

`wpm_step.py` is the step behind the Up and Down keys: 10 words per minute,
landing on the same values as the speed slider, within the range Settings
allows.

The core also owns how a flash's text is assembled. `reader.py` exposes the
split of each chunk into its before, focus, and after parts, in one place, so
that drawing a flash and measuring how wide the widest one is both use the same
text.

### Letter spacing and font choice

Two more small, pure modules sit behind the letter spacing selector and the font
switch on the Appearance tab.

`letter_spacing.py` works out the spacing. Tk has no letter spacing setting, so
the room between letters is made of thin space characters in the text that gets
drawn. How wide each of those characters is depends on the font and the machine,
because most fonts have no glyph for them and the system borrows one from
another font. So the GUI measures each character once, in em (a fraction of the
font size), and hands the widths to `build_plan()`. That picks the combination of
characters whose total lands closest to the gap the chosen level asks for (Off,
Small, Medium or Large), and it also decides the gap between the words of a
chunk, which is widened where needed so the words do not run together.
`space_chunk()` then puts those gaps into a flash's before, focus and after text
and leaves the focus letter itself untouched. The module never measures anything
and never touches a widget, so it is tested without a window. A level that is not
a valid one is pulled to the nearest valid one, and a value that is not a whole
number means Off.

`font_choice.py` names the two font sets, Fredoka with Quicksand as the standard
set and OpenDyslexic as the other, along with the font files each one needs.
`choose_fonts()` picks a set from the saved switch and the names of the files
found in the fonts folder. Only a real `true` turns OpenDyslexic on, so a damaged
settings file cannot do it by accident, and if the switch is on but the
OpenDyslexic files are missing it falls back to the standard set and says so.
The same module words the grey notes Settings shows under the switch, which
keeps that wording testable too.

### Bold word starts and copying with bold

Four small pieces sit behind the bold button and the copy, and all of them are
pure.

`bold_starts.py` decides which letters are bold. `bold_ranges()` takes a piece of
text and returns sorted, non-overlapping (start, end) pairs counted in Python
characters, and `fixation_length()` is the one place the length curve lives. A
word never runs across a line break, so a whole text and its lines one by one
give the same answer, which is what lets the edit box re-bold only the lines
someone typed in. The rules for what counts as a word are in there too, with the
reasoning: Latin, Cyrillic and Greek letters, apostrophes inside a word, and
digits stuck to a word or an address meaning it is left alone.

`bold_spans.py` turns those pairs into places a Tk text widget understands,
"line.column". Two facts shape it. Tk 8.6, the version that comes with Python
3.13 on Windows, counts a character outside the Basic Multilingual Plane (an
emoji, say) as two columns, and Tk 9 counts it as one, so the widget asks Tk
which and passes the answer in. And the time Tk needs to tag a line grows with
the square of the number of tags in it, about 0.1 seconds for a line of 1,000
words, 0.8 for 3,000 and 8 for 12,000. Lines over 4,000 characters
(`MAX_BOLD_LINE`) are therefore left plain, rather than freezing the window.

`rich_copy.py` builds what goes on the clipboard when the bold is copied.
`cf_html()` writes the Windows "HTML Format": a header of byte offsets (counted
in UTF-8 bytes, in fixed-width numbers), then one paragraph per line with `<b>`
around the bold runs. Spaces that HTML would squeeze are written as non-breaking
ones, so the text pastes back the way it was. `segments_text()` joins the same
pieces into the plain text that travels beside it.

`font_choice.py`, which already picks the font set, also has `bold_family()`.
Nearly every family is its own bold, but OpenDyslexic registers its Bold file as
a different family from its Regular one, and asking for bold in the regular
family would get a faked bold instead of the face the font ships with.

## The GUI layer

### App identity

`app_info.py` holds the app's name, version, license, and project link as plain
constants, so the About dialog in Settings has one place to read them from and
there is one place to change them. The version is bumped by hand just before a
release is tagged, and a test fails if the repository already has a newer
release tag than the one written there, which is the reminder to do it.

### The GUI layer

`gui/` is the CustomTkinter interface. It composes the windows, draws the
reading canvas, and drives the clock that the core engine leaves to it.

`gui/app.py` holds `RSVPApp`, the main window. It owns the two stores and lays
out the main regions: the sidebar with its transcript list, search, sort, and
Space switcher; the header; the reading canvas in the center; and the bottom
control band for speed and colors. It also binds the keyboard shortcuts and
opens the dialogs. It marks the open transcript in the sidebar list, notes the
window's size and place as it changes and saves them on close, and, when a save
file could not be read, queues a message for once the window is on screen
rather than showing it while the window is still being built.

The reading canvas is the busiest piece. It switches between two states for the
same transcript: the paste-and-edit box when a transcript has no text yet or has
been stopped, and the reader itself otherwise. The reader is a dedicated display
widget that places a word's before, focus, and after parts around a single fixed
anchor point, keeps the highlighted letter pinned to that point for every word,
draws the guide marks while words are flashing, and optionally shows the
peripheral ribbon. This display widget is where the timing loop actually lives:
it asks the session for the current word and its delay, shows the word, and
schedules the next step with the toolkit's timer. The core computes how long;
the GUI waits that long.

The display also fits what it draws to the room it has. It measures the widest
flash in the transcript in real pixels (again only when the grouping changes) and
renders the font no larger than that flash allows, never below 60% of the chosen
Word size. That is render-only: the saved size is never written back. If
something still overflows at the floor, it shows a horizontal scrollbar, driven by
the geometry in `core/scroll.py`, and a small button (and the C key) that returns
the flash to the centre. Measuring pixels is the GUI's job, which is why the fit
calculation lives here and only the pure arithmetic lives in the core.

Letter spacing is handled in the same place. The display measures the gap
characters in the font on screen, asks `build_plan()` for the gaps, and applies
`space_chunk()` both when it draws a flash and when it measures the widest one,
so the fit sees exactly what is drawn. Changing the level redraws the current
flash and measures again without touching the session, so the position, the
pause state and the timing all stay as they are. The surrounding-words line is
left unspaced.

Around the reader sit the controls: the floating stop button, the toolbar with
its play, restart, bookmarks, detach, and focus-mode actions and its time and
percent read-outs, the progress scrubber with its bookmark ticks, and the
bookmarks popover.

The detached window is a second, independent reader in its own top-level window,
with its own session and its own copies of the relevant settings, kept in sync
with the main window. It can do almost everything the main reader can, including
its own skipping buttons, and deliberately cannot enter focus mode, since it has
no chrome to hide.

The main window can read a different transcript while one is detached, so
`Canvas` decides where each of its controls goes by asking one question: is the
transcript open here the one in the detached window (`_detached_shows_current()`)?
Only then do the main window's keys, footer and toolbar reach the detached
reader. Settings that belong to the whole app, like the guide marks, reach both
windows either way.

The edit box, `gui/components/transcript_input.py`, draws the bold word starts
as a Tk tag on the inner text widget, with a bold copy of the font the box really
uses (CustomTkinter refuses a font in its own tag setting). Typing, pasting and
deleting re-bold only the lines that were touched. To learn which lines those
are, edits pass through a small Tcl procedure and not a Python callback. Tk runs
the text command inside a Tcl `catch`, so a Python function that raised there
would escape through the main loop, which is what used to break pasting.

Copying reads the bold back off the screen: it asks Tk to dump the selection with
its tag boundaries, rebuilds the pieces, and goes on only if the pieces spell
exactly the selected text. It then hands them to `gui/rich_clipboard.py`. Tk's own
clipboard takes plain text only, so that module calls the Windows clipboard
functions through `ctypes` and puts the plain text and the HTML on in one go.
`_Win32Api` is a thin wrapper with one method per Windows function, and
`copy_rich()` holds the order of the steps and works on any object with those
methods, which is how it is tested away from Windows. It never raises and says
whether it worked. When it did not, the box copies the plain text the ordinary
way, so a copy is never lost.

A click on the button updates the main edit box and the detached window through
`Canvas`, which then tells `RSVPApp`, and that saves the choice with
`SettingsStore.set_bold_starts_enabled`. A window that plays a selection is given
the look at the moment it opens and keeps it, so it is never touched by a click
elsewhere.

Reading profiles reach the screen through the Profiles tab of the Settings
window, `gui/components/profiles_tab.py`, with a name popup and a confirm popup
beside it. The tab only deals with what is on screen: it knows nothing about the
stores, and everything real goes through callbacks that `gui/app.py` hands it.
Applying a profile in `RSVPApp` asks `profile_apply.py` for the plan, then writes
it out through the same store setters and live canvas calls that Settings' Apply
uses, so it takes effect without a restart. Because the Settings window copies
every value into its controls when it opens, and its Apply writes them back, the
window closes after a profile is applied, and saving or updating a profile runs
the window's own Apply first. Otherwise a later Apply would put the old values
back over the profile.

Two small modules support the rest: `theme.py` holds the central design tokens
(colors, fonts, and how the active theme is resolved), and `icons.py` draws the
app's icons by hand rather than relying on font glyphs, which render
inconsistently across platforms. The many dialogs (the add-transcript chooser,
the create and move and delete dialogs, the Space dialogs, Settings, the About
dialog, and the import dialogs) each live in their own component file under
`gui/components/`. They share `dialog_keys.py` for Enter and Esc, and for putting
the cursor in a name box only once CustomTkinter has finished showing the
window, since it hides and re-shows a new window on Windows and would otherwise
take the cursor back.

The fonts follow the same pattern as the theme. `theme.py` reads the font switch
once, when it is first imported, and asks `font_choice.py` which set to use,
which is why changing the switch takes effect on the next launch. It registers
only the font files that set needs, and only on Windows (on other systems the
fonts have to be installed on the machine). When OpenDyslexic is in use it also
points CustomTkinter's default font at the same family, so widgets that set no
font of their own, such as the transcript edit box, follow along.

## How a word reaches the screen

Putting the layers together, a single reading session runs roughly like this:

1. The user selects a transcript, and the main window asks the transcript store
   for it.
2. The canvas builds a `ReaderSession` from that transcript's text, its saved
   speed, its last position, and the current pacing settings.
3. The reader display asks the session for the current word's frame and its
   delay, draws the word with its focus letter on the fixed anchor, and schedules
   the next step for that many milliseconds later.
4. When the timer fires it advances the session by one word and repeats, until
   the session reports it is finished.
5. As the position moves, it is written back to the transcript and saved on the
   throttle; stopping or leaving the transcript flushes the final position and
   updates the reading stats.

Pausing, skipping, scrubbing, and bookmarking all work by moving the session's
index or its play state and letting the same loop pick up from the new spot. The
engine never knows what a button is; it only knows which word is current.

## Why the boundary matters

Keeping `core/` free of the GUI is not decoration. It means the parser,
tokenizer, ORP logic, timing, stores, and the whole `ReaderSession` can be
tested directly, quickly, and without a display, which is most of what the test
suite does. The interface then gets a thin smoke-test layer on top to confirm
the wiring holds. If the one-way dependency ever broke, that separation, and the
testability that comes with it, would go with it. It is the rule most worth
protecting in the codebase.

## Tests and automation

The suite runs in two places. On a development machine, `python -m pytest`
runs all of it, the GUI smoke tests included. On GitHub, the Tests workflow
runs the same suite on Linux for every push to `main` and every pull request,
with a virtual display so the GUI tests have a screen to draw on.

The release workflow runs that same workflow first and builds nothing unless
it passes, so a tag can't turn a failing commit into a release. The steps for
making a release are written down in
[RELEASING.md](https://github.com/QuiteNew/rsvp-desktop-reader/blob/main/RELEASING.md)
in the repository.