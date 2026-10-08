# Usage

This guide covers everything in RSVP Desktop Reader: how the reading itself
works, organizing transcripts into Spaces, getting text in and editing it,
the reader and its controls, the detached window, the keyboard shortcuts, and
every setting.

## How the reading works

RSVP (Rapid Serial Visual Presentation) shows text one word at a time in a
single fixed spot, so your eyes never move across a page. Within each word,
one letter is highlighted: the Optimal Recognition Point, the letter your eye
naturally lands on to recognize the word fastest.

A few mechanics are worth knowing, because several settings tune them:

- **The highlighted letter** sits a little left of center and moves one
  position to the right as words get longer: the first letter for a
  one-letter word, the second for words up to five letters, the third up to
  nine, the fourth up to thirteen, and the fifth beyond that. The center of
  that letter is pinned to the same point on screen for every word, so your
  eye rests in one place and never has to relocate.
- **Guide marks** are the two short vertical marks above and below the focus
  letter. They appear only while words are actively flashing and disappear
  when you pause, stop, or finish. Their length, thickness, and color are
  adjustable, and you can optionally add faint horizontal lines through them
  to form a crosshair.
- **Pacing** starts from your speed in words per minute: at 300 WPM each word
  gets about 200 ms. Punctuation then lengthens the pause after a word, a word
  that ends a sentence stays up about two and a half times as long, and one
  ending in a comma, colon, or semicolon about one and a half times. If "slow
  down for long words" is on, longer words also get up to roughly 1.2, 1.45,
  or 1.7 times their normal time in three length bands. Punctuation and length
  pauses do not stack, whichever is longer wins for that word.
- **Ease in** (off by default) starts a session at about half speed and ramps
  smoothly up to your full speed over the first twenty words, to settle your
  eyes in. Restarting a session restarts the ramp; skipping or scrubbing does
  not.

## Spaces

Spaces are named groups of transcripts, like browser-tab categories, so
related transcripts stay together. The sidebar list only ever shows the
transcripts in the current Space. There is always at least one Space, and on
first launch it is called **General**.

Spaces are managed from the switcher bar at the bottom of the sidebar, which
shows a **v** button on the left, the current Space name in the middle, and a
**+** button on the right.

- **Create a Space:** click **+** on the switcher bar, type a name in the
  **New Space** dialog, and click **Create**. Creating a Space switches you
  to it. A blank name does nothing, and a duplicate name is rejected.
- **Switch Spaces:** click **v** to open the **Select Space** picker. The
  current Space is shown highlighted and the others are clickable, click one
  to switch.
- **Rename a Space:** in that same picker, click the pencil icon on a row,
  edit the name, and press Enter (or click away) to commit, or Escape to
  cancel. Renaming reassigns all of that Space's transcripts to the new name.
- **Delete a Space:** click the X icon on a row in the picker. You cannot
  delete your only Space, and you cannot delete a Space that still contains
  transcripts, move or delete those first. Otherwise you confirm in a
  **Space deletion** dialog.

## Transcripts

### Creating a transcript

Click **+** at the top of the sidebar. The **Add Transcript** chooser asks
how you want to add one, with two choices:

- **Blank transcript** opens an empty transcript.
- **Add from file...** imports text from a file (covered below).

Either way you then get a dialog asking for a **Title** and which **Space**
the transcript belongs to (pre-set to your current Space), with a **Create**
button. A blank title does nothing, and duplicate titles are allowed.

A new blank transcript starts empty and opens into the paste and edit box
when you select it.

### Importing from a file

Choosing **Add from file...** opens a file picker titled **Add from File**.
Supported formats are:

- Plain text (`.txt`)
- Subtitles (`.srt`, `.vtt`)
- Markdown (`.md`, `.markdown`)
- HTML (`.html`, `.htm`)
- Word documents (`.docx`)
- PDF (`.pdf`)

While the file is read, a small **Importing** notice appears. Importing is a
single blocking step, so the app will not respond until it finishes, which can
take a moment for large files. When it is done, the create dialog opens with
the title pre-filled from the file name (selected, so typing replaces it).

Importing cleans the text up for reading automatically:

- **Timestamps are stripped**, including subtitle timing lines, bracketed or
  parenthesized times, full hour-minute-second times, and bare minute-second
  times sitting alone on their own line (the YouTube style). A time written
  inside a sentence, like "we met at 10:30", is kept.
- **Structure is preserved** for the edit view (line breaks kept, runs of
  blank lines collapsed, each line trimmed), and format-specific markup is
  removed: subtitle index and timing lines, Markdown formatting, HTML tags and
  scripts, and so on. PDF text is pulled page by page, and common extraction
  damage like broken ligatures is repaired.

If a file parses to more than about 30,000 words, the dialog shows a heads-up
that very large transcripts have been known to crash the app and suggests
splitting the file. It is a warning, not a block. If a file cannot be read (a
password-protected PDF, an empty or unsupported file), you get a **Couldn't
add that file** message explaining why.

Imported text lands in the edit box as a draft, it does not start reading on
its own.

### Editing the text, and Normalize

A transcript opens into its paste and edit box when it has no text yet or when
it has been stopped. Paste or type your text there and click **Start
reading**. A transcript that already has text and is not stopped opens
straight into the reader instead, to get back to its text, click **Stop** (or
press Esc), which returns you to the edit box with the last saved text.

Beneath the edit box is a **Normalize** button that tidies the layout of the
text: it removes list markers and page numbers, strips any timestamps that
slipped through, rejoins lines that were broken mid-sentence, and repairs
PDF-extraction damage. It is a toggle, clicking it again reverts if you have
not changed the box, and it does nothing if there is nothing to tidy.
Normalizing only changes how the text is laid out in the box, never which
words get read. Optionally (a setting, off by default) it also splits very
long walls of text into paragraphs at sentence ends.

### Reading just a selection

You do not have to read a whole transcript. Select a portion of text in the
edit box, right-click it, and choose **Play** to read just that selection, or
**Detach** to open it in its own window. Selection reading is independent, it
never changes the transcript's saved text, position, or stats.

### Renaming, moving, and deleting

- **Rename:** double-click the transcript's title in the sidebar. The title
  turns into an editable field, press Enter or click away to save, Escape to
  cancel.
- **Move to another Space:** right-click the transcript's row and choose
  **Move to Space...**, then pick the destination. If you only have one Space,
  it tells you to create another first.
- **Delete:** hover the row and click the **X** on its right. You confirm in a
  **Transcript deletion** dialog before it is permanently removed.

### Finding transcripts

A **Search...** box above the list filters the current Space's transcripts by
title (case-insensitive), it does not search the body text. Next to it, a sort
button offers Title A to Z, Title Z to A, Date added newest or oldest first,
Most read, and Most time spent reading.

## The reader

### Controls

The reading view has a floating **Stop** button in the top-left corner and a
toolbar on the right. In the main window the toolbar shows, left to right, two
read-out pills (estimated time remaining and progress percent), then
**Play/Pause**, **Restart**, **Bookmarks**, **Detach**, and **Focus mode**.

- **Play/Pause** starts and pauses the flashing.
- **Restart** jumps back to the first word, resumes playing, and restarts the
  ease-in ramp.
- **Stop** ends the session and drops you back to the edit box showing the
  transcript's saved text. (It is careful not to wipe anything, it only acts
  when the reader is genuinely what is on screen.)
- **Detach** pops the transcript out into its own window (see below).
- **Focus mode** hides the sidebar and app chrome so only the flashing words
  remain. It is a main-window feature.

If no transcript is open, the area shows "Select or create a transcript to
begin".

### Skipping

Skipping moves backward or forward by a configurable number of words (ten by
default, adjustable from 1 to 50 in Settings). In the **main window skipping
is done with the left and right arrow keys**, there are no skip buttons on the
main toolbar. The detached window does have dedicated skip buttons. You can
optionally have the reader pause on the word it lands on after a skip.

### The progress bar

Below the words is a progress bar you can drag to seek. Above it, a read-out
shows "word X of Y", and the toolbar pills show the estimated time remaining
and the percent complete. While you drag, playback holds so you can see where
you are landing. By default, releasing the bar leaves the reader paused on that
word, you can change that in Settings so it resumes playing instead.

### Bookmarks

Press **B** (or the toggle in the Bookmarks popover) to bookmark the word
currently on screen, or to remove a bookmark already there. Bookmarks show up
two ways: as small ticks under the progress bar at each bookmarked word, and as
rows in the **Bookmarks** popover (opened from the toolbar). In the popover,
single-click a row to jump to that word (which pauses there and closes the
popover), and double-click a row to rename it. Each row has an **X** to delete
it.

### The surrounding-words line

Optionally (off by default) a dim line appears beneath the flashing word
showing a couple of words before and after it, so your peripheral vision keeps
the thread of the sentence. The current word is centered and dimmed under the
same point as the focus letter.

## The detached window

The **Detach** button pops the current transcript out into its own standalone
window that reads completely independently of the main window, with its own
position, play state, and stats. While it is out, the main window shows a
"Transcript window detached" placeholder with a **Bring back** button.

The detached window has its own full set of reading controls: play/pause,
**skip backward and forward buttons** (unlike the main window, which uses the
arrow keys), restart, the progress bar with bookmark ticks, its own Bookmarks
popover, and Stop. It keeps all your settings in sync with the main window.

Two things it deliberately does not do: it has no **Focus mode** (there is no
sidebar or chrome to hide), and it cannot detach again. Only one detached
window exists at a time. To bring it back, click **Bring back** or just close
the window.

## Keyboard shortcuts

Shortcuts act on the reading controls. They are ignored while you are typing in
a text field (the search box, a rename field, or the edit box).

| Key | Action |
| --- | --- |
| Space | Play / Pause |
| Left / Right arrows | Skip backward / forward, by the skip word count set in Settings |
| R | Restart |
| B | Bookmark the current word (or remove the bookmark there) |
| Esc | Stop: ends the session and returns to the edit view. Works in both the main and detached windows |
| F | Toggle focus mode (main window only) |

## Settings

Open **Settings** from the top-right. Changes on most tabs are staged until you
click **Apply** (with **Close** to dismiss), and a few act immediately, noted
below. There are five tabs.

### Defaults

The color, speed, and word-size controls at the top are **defaults for newly
created transcripts** and do not change transcripts you already have. Most of
the controls below them apply **globally**, to every transcript, and the skip
controls at the bottom apply **live**.

New-transcript defaults:

- **Speed** (100 to 1000 WPM, default 300)
- **Font colour**, **Highlight colour**, **Background colour** for the reading
  canvas
- **Word size** (16 to 96 px, default 32)

Global controls:

- **Word-size step** for the +/- buttons (1 to 10 px, default 1)
- **Highlight vertical offset**, shift the focus letter up or down (-3 to 3 px,
  default 0)
- **Guide-mark thickness** (2 to 6 px, default 2)
- **Mark length** as a percent of word size (15 to 60%, default 35), so it
  scales with word size
- **Mark colour**
- **Show horizontal guide lines**, adds the crosshair lines (default off)
- **Slow down for long words**, the length pacing described above (default off)
- **Ease in at the start of reading** (default off)
- **Split long paragraphs when normalizing** (default off)
- **Rewind a few words when resuming** (default off), with a **words to
  rewind** amount (1 to 5, default 3)
- **Pause after using the scrubber** (default on)
- **Show surrounding words**, the peripheral line (default off)

Live controls (take effect immediately, on the current transcript and future
ones):

- **Skip amount** (1 to 50 words, default 10)
- **Pause playback when skipping** (default off)

A **Reset to Original Defaults** button restores this tab.

### Layout

- **Free-form resize**, lets you drag the sidebar and bottom-band borders
  directly in the main window (default off)
- **Window width** (500 to 2000, default 1000)
- **Window height** (400 to 1400, default 650)
- **Sidebar width** (120 to 500, default 220)
- **Bottom band height** (80 to 400, default 100)
- **Reset to Original Defaults**

### Storage

Shows the folder your transcripts are saved in (as a JSON file).

- **Choose folder...** picks a new data folder. The change is staged and takes
  effect when you click Apply.
- **Export Data...** saves a single file containing all your transcripts,
  Spaces, and settings (except the data-folder path, which is
  machine-specific). This happens immediately.
- **Import Data...** loads such a file. You then choose **Replace** (wipe
  everything here and replace it with the file), **Expand** (add the file's
  transcripts and Spaces to what you have, leaving your settings untouched), or
  **Cancel**. Either way the app closes afterward so the change can take
  effect, reopen it when you are ready.
- **Reset to Original Defaults** restores the default data folder.

### Appearance

- **Colour theme**: Light, Dark, or System (default Light). This one takes
  effect the next time you launch the app, not live.

Note that a new transcript's reading colors come from the Defaults tab, not
from the theme, so they will not automatically match Light or Dark. Adjust them
under Defaults, or per transcript from the control band at the bottom of the
window.

### Stats

A read-only summary, one card per transcript across all Spaces, showing how
many times you have read it, how many words, and the total time spent. The
totals update when a reading session ends (clicking Stop, switching
transcripts, detaching, or closing the app), not while you are simply paused,
so if you want the latest numbers, stop or switch away first, then reopen
Settings.

### When changes take effect

- **Immediately:** the Skip amount and Pause-when-skipping controls, and the
  Export and Import buttons (Import then closes the app).
- **On Apply:** everything else on Defaults, Layout, and Storage.
- **Next launch:** the Appearance theme.