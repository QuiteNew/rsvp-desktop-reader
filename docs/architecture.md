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
  data location (`~/.rsvp_reader`).
- `transcript_store.py` holds all transcripts and Spaces in memory and persists
  them through `storage`. Live edits such as a position change save on a
  throttle so rapid updates do not hammer the disk, and an explicit flush forces
  a write when a session ends.
- `settings_store.py` does the same for application settings: the new-transcript
  defaults, layout sizes, data location, and theme.
- `data_bundle.py` builds and applies the single-file export used to move
  transcripts, Spaces, and settings between machines, deliberately leaving the
  machine-specific data path out of the bundle.

## The GUI layer

`gui/` is the CustomTkinter interface. It composes the windows, draws the
reading canvas, and drives the clock that the core engine leaves to it.

`gui/app.py` holds `RSVPApp`, the main window. It owns the two stores and lays
out the main regions: the sidebar with its transcript list, search, sort, and
Space switcher; the header; the reading canvas in the center; and the bottom
control band for speed and colors. It also binds the keyboard shortcuts and
opens the dialogs.

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

Around the reader sit the controls: the floating stop button, the toolbar with
its play, restart, bookmarks, detach, and focus-mode actions and its time and
percent read-outs, the progress scrubber with its bookmark ticks, and the
bookmarks popover.

The detached window is a second, independent reader in its own top-level window,
with its own session and its own copies of the relevant settings, kept in sync
with the main window. It can do almost everything the main reader can, including
its own skipping buttons, and deliberately cannot enter focus mode, since it has
no chrome to hide.

Two small modules support the rest: `theme.py` holds the central design tokens
(colors, fonts, and how the active theme is resolved), and `icons.py` draws the
app's icons by hand rather than relying on font glyphs, which render
inconsistently across platforms. The many dialogs (the add-transcript chooser,
the create and move and delete dialogs, the Space dialogs, Settings, and the
import dialogs) each live in their own component file under `gui/components/`.

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