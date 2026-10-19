# Usage

This guide covers everything in RSVP Desktop Reader: how the reading itself
works, organizing transcripts into Spaces, getting text in and editing it,
the reader and its controls, the detached window, the keyboard shortcuts, every
setting, and saved reading profiles.

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
title (case-insensitive), it does not search the body text. A small **X** inside
the right end of the box clears what you have typed. Next to it, a sort button
offers Title A to Z, Title Z to A, Date added newest or oldest first, Most read,
and Most time spent reading.

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

## Reading words in groups (chunking)

By default the reader shows one word at a time. Chunking instead flashes a
small group of words together in the same fixed spot, so your eyes take in a
few words per stop rather than one. The first word of the group anchors its
focus letter to the usual point, and the rest of the group trails to the right
of it.

A group never runs past the end of a sentence, so a single flash never
straddles two sentences. Timing is unchanged: a group stays on screen for
exactly as long as its words would have taken one at a time, so grouping does
not by itself change your reading speed, only how the words are parceled out.

There are two ways a group's size is decided:

- **Fixed** flashes a set number of words per group (2 to 5).
- **Adaptive** fills each group up to a character width instead (15 to 60
  characters, counting the letters and the single spaces between the words), so
  short words pack together and long ones do not crowd the line. In adaptive
  mode a group also never holds more than six words.

Chunking is set per transcript, so different transcripts can read differently,
and there are defaults that new transcripts start from. A large group at a big
Word size can be wider than the reading area, which the reader handles for you,
see [Wide flashes](#wide-flashes-auto-fit-and-the-scrollbar) below.

### The quick control

The control band at the bottom of the main window has a **Group** switch and a
small size stepper for the transcript you are reading. The switch turns grouping
on and off, and the stepper raises or lowers the fixed word count. Changing
either re-groups the words in place, without losing your spot or restarting the
session. The stepper always edits the fixed word count; the sizing mode and the
adaptive width live in the Configure chunking window below.

### The Configure chunking window

For the full set of options, open **Settings**, under Defaults, and click
**Configure chunking...**. At the top is an **Apply to** selector that chooses
whether your changes land on the transcript open right now or on the defaults
for new transcripts (only the defaults are offered when no transcript is open).
Below it are:

- **Group words together**, the on/off switch.
- **Group size**: **Fixed** or **Adaptive**.
- **Words per group**, the fixed word count, used in Fixed mode.
- **Group width**, the adaptive character width, used in Adaptive mode.

Applying to the current transcript re-groups the live reader in place and keeps
your spot; applying to the defaults only affects transcripts you create later.
The bottom control band and this window stay in step, since both drive the same
per-transcript settings.

## Wide flashes: auto-fit and the scrollbar

Sometimes a flash is wider than the reading area, most often when chunking is
on at a large Word size, when [letter spacing](#letter-spacing-and-the-opendyslexic-font)
is turned up, or when a transcript contains one very long word. The reader deals
with this on its own, in two stages, and most of the time you will not notice
either one.

**Auto-fit** shrinks the words just enough that the widest flash in the whole
transcript fits the reading area, with a small margin on each side. It measures
the entire transcript up front rather than the flash on screen, so the size
stays steady while you read instead of changing from flash to flash. Only what
is drawn changes: your Word size setting, the +/- buttons, and the saved size
are never touched, and the words return to full size as soon as everything fits
again (a smaller group, a smaller Word size, or a wider window). The guide marks
and the surrounding-words line follow the shrunken size. Auto-fit is always on,
there is no setting for it.

**The 60% floor.** Auto-fit never shrinks the words below 60% of your Word size.
If the widest flash is still too wide at that size, the scrollbar takes over.

**The scrollbar** appears along the bottom of the reading area only while
something still overflows, and goes away again when nothing does. Drag it to
slide the words left or right and bring the hidden part into view. Its travel
covers only what is actually hidden, so there is no empty space to scroll into,
and it is sized for the widest flash, so one position works for the whole
session. While you are panned, the guide marks are hidden (they mark the fixed
centre point, which is no longer where the focus letter sits), and the
surrounding-words line slides along with the words.

**The centre button** is a small square at the bottom left of the reading area,
just above the scrollbar. Click it to snap the words back to the centre, or
press **C**. The position is not saved: it starts centred every time a
transcript is opened, and again whenever the scrollbar goes away.

All of this works the same in the main window, the detached window, and the
window that plays a selection.

Panning moves the words, it cannot make a flash wider than the window fit in a
single glance. If you keep seeing the scrollbar, the lasting fix is a smaller
group, a lower adaptive width, a lower letter spacing level, or a smaller Word
size.

## Letter spacing and the OpenDyslexic font

Two optional settings change how the words look. Both are on the **Appearance**
tab in Settings (see [Appearance](#appearance)), both are off by default, and
they are independent: letter spacing works with any font, and the font switch
does not touch the spacing.

**Letter spacing** adds a little room between the letters of the flashing word.
It has four levels, Off, Small, Medium and Large, which add roughly 0.1, 0.18
and 0.3 of the Word size between neighbouring letters.

- The highlighted letter stays on its usual point. The room is added around it,
  not inside it.
- In chunk mode the gaps between the words of a group are widened where needed,
  so the words do not run together once the letters are spaced out.
- The surrounding-words line is left as it is.
- It applies as soon as you press **Apply**, in the main window and in the
  detached window. A window that plays a selection keeps the level it was
  opened with.
- The level is saved in [reading profiles](#profiles).
- Wider words need more room, so with spacing turned up the words may be drawn a
  little smaller, or the scrollbar may appear sooner (see
  [Wide flashes](#wide-flashes-auto-fit-and-the-scrollbar)).

Tk, the toolkit the app is built on, has no letter spacing setting, so the app
puts thin space characters between the letters. How wide those come out depends
on the font and on the computer, so the app measures them and picks the mix that
lands closest to each level. The levels look alike from one font or computer to
the next, but they are not identical.

**The OpenDyslexic font** switch changes every font in the app, not only the
reader, to OpenDyslexic, a typeface released under the SIL Open Font License.

- It takes effect the next time you launch the app, like the colour theme,
  because the fonts are chosen once at startup. The switch is saved when you
  press **Apply**.
- It is not saved in reading profiles, since a profile applies on the spot and a
  font cannot change that way.
- On Windows the app loads the font files from `assets/fonts/` itself. On macOS
  and Linux it cannot, so install OpenDyslexic on your system first (the files
  are in that folder), or the text is drawn in a stand-in font.
- If the OpenDyslexic files cannot be found in the fonts folder, the app keeps
  the standard fonts, and the Appearance tab says so.

Neither setting is a treatment for dyslexia, and the app does not claim that
either one helps. The research is mixed, and the studies used running text, not
words flashed one at a time. The FAQ has the details, under
[Do the OpenDyslexic font and letter spacing actually help?](faq.md#do-the-opendyslexic-font-and-letter-spacing-actually-help).

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
| C | Snap the words back to the centre after panning with the horizontal scrollbar (see [Wide flashes](#wide-flashes-auto-fit-and-the-scrollbar)) |
| Esc | Stop: ends the session and returns to the edit view. Works in both the main and detached windows |
| F | Toggle focus mode (main window only) |

## Settings

Open **Settings** from the top-right. Changes on most tabs are staged until you
click **Apply** (with **Close** to dismiss), and a few act immediately, noted
below. The Profiles tab has no Apply button of its own, see
[Profiles](#profiles). There are six tabs, plus a small round **i** button in
the top-right corner that opens the [About dialog](#the-about-dialog).

A **Search settings...** box sits at the top of this tab and filters the
controls below as you type. It matches a setting's name and some extra keywords
(so "colour" finds the colour pickers and "crosshair" finds the guide-mark
controls), in any order, and clears with the **X** inside its right end. The button next
to the box also searches each setting's longer description when you turn it on.
While a search is active the grey notes and the **Reset to Original Defaults**
button are hidden, with a short line in their place; if nothing matches, the tab
says so.

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

A **Configure chunking...** button opens the chunking window described under
[Reading words in groups](#reading-words-in-groups-chunking) above, where you
set grouping for the current transcript or for new transcripts.

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

This tab scrolls when the Settings window is too small to show all of it.

- **Colour theme**: Light, Dark, or System (default Light). This one takes
  effect the next time you launch the app, not live.
- **Use the OpenDyslexic font**: changes every font in the app to OpenDyslexic
  (default off). This one also takes effect the next time you launch the app,
  and it is saved when you press **Apply**. Notes under the switch say what
  applies on your system.
- **Letter spacing**: Off, Small, Medium or Large (default Off). It applies as
  soon as you press **Apply**.

Both are described under
[Letter spacing and the OpenDyslexic font](#letter-spacing-and-the-opendyslexic-font).

Note that a new transcript's reading colors come from the Defaults tab, not
from the theme, so they will not automatically match Light or Dark. Adjust them
under Defaults, or per transcript from the control band at the bottom of the
window.

### Profiles

A profile is a saved set of reader settings, so you can switch between ways of
reading in one go, say a quick, light skim and a slower, careful read, instead
of changing a handful of controls by hand each time.

**What a profile holds.** These settings, all from the Defaults tab except the
last:

- the guide marks: **Highlight vertical offset**, **Guide-mark thickness**,
  **Mark length**, **Mark colour**, and **Show horizontal guide lines**
- pacing: **Slow down for long words** and **Ease in at the start of reading**
- **Rewind a few words when resuming**, and how many words to rewind
- **Show surrounding words**
- **Skip amount** and **Pause playback when skipping**
- **Word-size step** for the +/- buttons
- **Pause after using the scrubber** and **Split long paragraphs when
  normalizing**
- **Speed** and **Word size**, the two sliders at the top of the Defaults tab
- **Letter spacing**, from the Appearance tab

**What it never changes.** Applying a profile never touches a transcript: not
its text, its position, or its own speed and size. It does not change your
Defaults colours (font, highlight and background), the chunking settings, the
layout, the data folder, the Light / Dark theme, or the OpenDyslexic font switch
(a font only changes when the app starts). Speed and Word size are the
Defaults sliders, so they only decide where the next *new* transcript starts.
The transcript you have open keeps the speed and size it already has. To keep
different texts apart, use [Spaces](#spaces).

The guide mark colour is remembered with one extra detail: if it was still
following the Light / Dark theme when you saved the profile, the profile keeps
following it, and applying it later gives you the current theme's colour. A
colour you picked by hand is applied exactly as picked.

**The tab.** At the top is a short explanation, then a **Save current settings
as...** button, then the list of your profiles. Click a profile to select it,
and click it again to unselect it. Four buttons under the list work on the
selected profile and stay greyed out while nothing is selected:

- **Apply** puts the profile's settings to use. It takes effect straight away,
  with no restart, in the reader you have open and in the detached window. The
  Settings window then closes, so that when you open it again every tab shows
  the new values.
- **Update** replaces what the profile holds with the settings you are using
  now, after a confirmation. The old settings cannot be brought back.
- **Rename** changes the profile's name.
- **Delete** removes the profile, after a confirmation.

A name can be up to 30 characters, and two profiles cannot share a name,
ignoring capitals. Extra spaces are tidied up. There is no limit on how many
profiles you can keep, and the list scrolls when it gets long.

**Saving, updating and applying start by applying your changes.** If you
changed something on another tab and have not pressed **Apply** yet, saving,
updating or applying a profile first applies those changes, and a value that
cannot be used (a number that is not a whole number, say) stops the action and
is reported under the tabs. That is why the window's own **Apply** button is
hidden on this tab: you do not need it here.

A profile is a snapshot, not a live link. Changing a setting later does not
change the saved profile, and applying a profile copies its values in. To bring
a profile up to date, set things the way you want and press **Update**.

**Older profiles.** A profile only changes the settings it holds. Profiles saved
before the Speed, Word size, +/- step, scrubber and paragraph settings joined do
not hold those five, and profiles saved before version 3.5.1 do not hold the
letter spacing, so applying them leaves those settings as they are. Select the
profile and press **Update** once to bring them in.

**Export and Import.** Profiles are saved in `settings.json`, so **Export Data**
carries them to another machine. **Replace** brings them in with the rest of
the settings, and **Expand** leaves your settings, profiles included, as they are.

### Stats

A read-only summary, one card per transcript across all Spaces, showing how
many times you have read it, how many words, and the total time spent. The
totals update when a reading session ends (clicking Stop, switching
transcripts, detaching, or closing the app), not while you are simply paused,
so if you want the latest numbers, stop or switch away first, then reopen
Settings.

### The About dialog

The small round **i** button in the top-right corner of the Settings window
opens an About dialog. It shows the app's icon, its name and version, the
license it is released under, and a link to the project on GitHub; clicking
the link opens the project page in your browser. That link is the only thing
in the app that reaches outside it, and only when you click it. **Close**, or
the window's own close button, takes you back to Settings.

The version shown there is the one to quote when you report a problem, or to
compare against the latest release on the project's Releases page.

### When changes take effect

- **Immediately:** the Skip amount and Pause-when-skipping controls, and the
  Export and Import buttons (Import then closes the app).
- **On Apply:** everything else on Defaults, Layout, and Storage, and the letter
  spacing on Appearance.
- **When you use a button on the Profiles tab:** saving, updating, renaming and
  deleting a profile are saved at once, and applying one takes effect at once
  and closes Settings. Saving, updating and applying first apply any pending
  changes from the other tabs.
- **Next launch:** the Appearance theme and the OpenDyslexic font switch. Both
  are saved when you press **Apply**.