# Bold word starts in the edit box (the "bionic" look) - design and status

Status (21.10.2026): **ALL STEPS DONE AND RELEASED as v3.7.0 (published by the user on 21.10.2026, 1796 tests).** Steps 1 to 8 are done. Steps 1 to 5 are committed
in the user's repo (5a is bb738a4, 5b the commit after it). Step 6 (the user's own
checks on Windows) found one real bug, the paste crash (below), fixed. **Step 8
(copy with the bold into Word) is built in three parts, 8a, 8b and 8c, and the user
confirmed on Windows that it works in Word.** **Step 7 (docs and release) is done, see "Step 7 as done" below.**
Version: **v3.7.0** (confirmed by the user on 19.10.2026). The details of step 4,
with the findings behind it, are also in `claude/bold-starts-step4-notes.md`.

## Summary

A small button in the edit box's button row, right next to Normalize, same size
(36x28) and same colour. Clicking it makes the start of every word in the
transcript text bold, so the draft looks "bionic". Click again to turn it off.

It is purely cosmetic and lives only in the draft box:

- Not in the reader, not in the peripheral line, not in profiles.
- The text itself never changes. Bold is a Tk text tag laid over it. So saving,
  Start reading, the transcript's stored text and the Normalize revert check
  (`can_revert` compares text) are all untouched.
- Independent from Normalize: neither button knows about the other.
- Works with the OpenDyslexic font too (user's requirement, 19.10.2026). The
  bold face for it exists (OpenDyslexic3-Bold is registered), and the bold copy
  of the edit box's font is built from whatever font the box really uses, so it
  follows the font switch. Both font modes are tested on the user's machine in
  step 6.
- **Lines over 4,000 characters are left plain** (about 650 words), with a short
  "Long lines stay plain" notice. See "Step 4 as built" for why this limit exists.
- **The bold is on screen, and travels to Word.** With the look on, Ctrl+C and a
  right-click "Copy with bold" put the selection on the Windows clipboard as HTML
  next to the plain text (step 8). Notepad and other plain-text targets get the
  words without the bold, which is the best they can ever do.

## Decisions (19.10.2026 and later)

- **Where:** all three edit views, because they share one widget
  (`TranscriptInput`): the main window, the detached window and the selection
  preview window. No extra flag.
- **Remembered across launches.** One new key in settings.json. It is a cosmetic
  global setting, not a profile key (profiles.py keeps an explicit key list, so
  it stays out unless added). It travels in exports and bundles like the font
  and spacing settings do.
- **Who follows whom (20.10.2026, user chose "Snapshot, own toggle"):** the main
  edit box and the detached window are one setting: a click in either changes
  both and is saved. **Selection preview windows are snapshots with their own
  button:** they open with the look the app has at that moment, their button
  changes only that window, is never saved, and later changes in the app never
  reach them (the same way their letter spacing and other styling already work).
  This replaced my first idea that every open edit view follows.
- **Hyphenated words:** bold each part. well-known becomes **we**ll-**kno**wn.
- **On state:** swap the icon (two glyphs, like Normalize and Revert), so the
  button colour stays identical to Normalize in both states.
- **Version:** v3.7.0.
- **Process:** one step is one commit, unless a step is large, then it is split.
  The things marked unverified below are tested as the steps go, not up front.
  The research is done at the docs stage (step 7), not before. Ponytail style
  (smallest complete change) is wanted, but the house rules win where they
  differ: whole files, reasoning explained first, humanised comments and commit
  text, tests checked by breaking the code on purpose.
- **Names:** because of the trademark check (see below) the internal names are
  neutral: `core/bold_starts.py`, `tests/test_bold_starts.py`, and the settings
  key `bold_starts_enabled`. The user never answered the naming question, but
  accepted step 1 under those names and asked to continue (20.10), so I treat it
  as settled. Step 2 put the key into settings.json, so a rename now means a
  migration.
- **"Nothing to change" moves** (20.10, user agreed): it now sits at the right-hand
  end of the button row, because beside two buttons it would run into Start
  reading in the 500 px detached window.
- **Very long lines stay plain** (20.10, my decision, flagged to the user, not yet
  confirmed by them): a Tk limit, see step 4c.

## What I read in the code first (19.10.2026)

- The button row is `button_row` in `gui/components/transcript_input.py`:
  three grid columns, Normalize in column 0, Start reading in column 1, the
  "Nothing to change" feedback label that used to share column 0 with
  `padx=(44, 0)`.
- Normalize is a plain `CTkButton`, 36x28, 24px icon drawn white
  (`PAGE_ICON_COLOR`) at 4x and scaled down (see `_PAGE_ICON_SOURCE_SCALE` in
  `gui/icons.py`), with the Tk image label's border stripped through the private
  `_image_label`. The new button copies all of that.
- The edit box is a `CTkTextbox` with no font of its own. It follows CustomTkinter's
  theme family (Roboto, which CustomTkinter bundles with only a Regular and a
  Medium file, no Bold) and, with the OpenDyslexic switch on, `gui/theme.py`
  overrides the theme family. Quicksand and Fredoka are not used by the edit box,
  so their bold files are not needed.
- **CustomTkinter 6.0.0 refuses `font` in `CTkTextbox.tag_config`** (line 447 of
  `ctk_textbox.py`, "incompatible with scaling"). The bold tag is set on the
  inner `tk.Text` (`self.textbox._textbox`), with a bold copy of that widget's
  real font. It stays right after a display-scale change (tested, 4b).
- `set_text()` deletes and reinserts, which drops tags, so the tag is re-applied
  after it when on.
- Whether real Roboto bold looks right on Windows is a guess: with no Roboto Bold
  file registered, Windows probably thickens the Regular glyphs. Step 6.

## The algorithm as built (step 1, core/bold_starts.py)

`bold_ranges(text)` returns sorted, non-overlapping `(start, end)` pairs counted
in Python characters. `fixation_length(letter_count)` is the one place the
length curve lives. A word never crosses a line break, so a whole text and its
lines one by one give the same answer, and the bold of one line depends on that
line only (which step 4c relies on).

Rules, as they ended up (they differ from the first sketch in three places,
marked NEW):

- A **word** is a run of letters of Latin, Cyrillic or Greek. Letters of other
  scripts (Chinese, Japanese, Arabic, Hebrew, Thai) are left alone.
- Straight, curly and modifier apostrophes between letters stay inside the word.
  One at either end is punctuation.
- **Boundaries:** every kind of hyphen and dash, slash, underscore, digit, any
  other punctuation, space. Each part is its own word.
- Soft hyphen, ZWNJ, ZWJ and word joiner stay inside a word and are not counted.
  **NEW: a zero-width space ends the word** (it is a break opportunity), where
  the first sketch had it as glue.
- Combining marks stay with their letter and a cut never lands between them.
- **NEW: a word with a digit right against it (3rd, H2O, mp3, x86, 1990's, m2)
  is left alone.** The first sketch bolded each letter run of such tokens.
  COVID-19 and 3-D still work because the hyphen separates them.
- URLs (http://, https://, www.) and email addresses are left alone. **NEW:**
  that was in the first sketch only as an idea. A bare domain (example.com) is
  not recognised, on purpose, and the code comment says so.
- ALL CAPS and CamelCase are one word. A one-letter word is bold in full.
- The surrogate-pair rule from the first sketch is gone: Python strings have no
  split halves. What Tk does with characters outside the BMP is handled in
  step 4a (below).

Length curve (letters in the word : bold letters): 1:1 2:1 3:2 4:2 5:3 6:3
7-10:4 11-14:5 15 or more:6. In words of 7 letters or more the cut moves up to 2
letters to the nearest place between a vowel and a consonant (the shorter cut
wins a tie, a cut is never made right before a Cyrillic soft or hard sign, y
counts as a vowel, Cyrillic short i is a consonant). A word with no such place
keeps the plain length. Sample output the user can judge:

a is the that about people because reading journey audience beautiful
information understanding international internationalization state-of-the-art
well-known mother-in-law don't O'Brien become, in bold:
**a** **i**s **th**e **th**at **abo**ut **peo**ple **bec**ause **read**ing
**jou**rney **aud**ience **beau**tiful **info**rmation **unde**rstanding
**inte**rnational **intern**ationalization **sta**te-**o**f-**th**e-**ar**t
**we**ll-**kno**wn **mot**her-**i**n-**la**w **do**n't **O'Br**ien. The user has
not said anything about the curve, so it is still tunable in
`fixation_length()`.

How it was checked (in a scratch copy, Python 3.13.16, pytest 9.1.1):

- tests/test_bold_starts.py, 106 tests, all passing.
- Mutation checks: 26 deliberate breaks of the module, all caught by a test. The
  first pass left 8 alive, which exposed real test gaps (nudge distance, upper
  case, the position-1 look-through, the guard that keeps the cut inside the
  word) and 2 pieces of code that did nothing visible (a letter-follows check,
  and ftp://), which were deleted.
- A crash fuzz over 30,000 random strings from Latin, Cyrillic, Greek, marks,
  digits, punctuation, invisible characters, other scripts and emoji: no crash,
  and the answer kept its shape every time.
- Speed: about 950,000 characters (98,000 bold stretches) in 0.32 s, so a full
  pass on a book-sized text is fine.
- The user then ran the whole suite on their machine: 1400 tests, green.

## The setting as built (step 2)

Smallest change that does the job: **one file of production code changes,
`core/settings_store.py`, by three additions and nothing removed** (14 added
lines). Export bundles, bundle import and the unknown-key filter pick the new
field up on their own because they work from the dataclass fields, so none of
them changed. `core/profiles.py` is untouched on purpose.

- `AppSettings.bold_starts_enabled: bool = False`, placed after
  `letter_spacing_level`.
- `SettingsStore.bold_starts_enabled`, a read-only property that returns
  `... is True`. That is stricter than its siblings: a settings.json with
  `"false"` as text, a 1, null and so on reads as off, so a damaged or
  hand-edited file cannot switch the look on by accident (same care as
  core/font_choice.py takes with the font switch). The raw value is still what
  gets exported.
- `SettingsStore.set_bold_starts_enabled(enabled)`, saves straight away like the
  other switches.
- Not a profile key, and a profile cannot hold it even if asked to
  (`sanitize_values` drops it).
- tests/test_settings_store_bold_starts.py: 25 tests. Defaults, switching on and
  off, no effect on other settings and none from them, persisting and reloading
  in both directions, the file on disk, an older file without the key, eight
  damaged values, the export (on and off), a replace import, a bundle from
  before the key, and the profile rules.
- Twelve deliberate breaks of the setting code, all caught (the first pass left
  one alive, a key added to the profile value rules but not the key list, so
  one assertion was added). Committed by the user.

## The icons as built (step 3, gui/icons.py)

Only `gui/icons.py` and `tests/test_icons.py` change. In `gui/icons.py` it is
**54 added lines and nothing removed**: two constants, the glyph drawing
`_draw_bold_starts_glyph(size, color, bold_starts)` and the helper
`bold_starts_icon(is_on, size=24)`, placed after `revert_icon`. One function with
an `is_on` flag, not two near-identical ones.

The look (chosen by the user from rendered previews, 20.10.2026):

- Three rows of two "words" drawn as plain rounded bars, ragged at the end like
  a paragraph. No page outline, so it cannot be taken for Normalize (page with a
  check) or Revert (plain page).
- **Off:** every word is the same soft tone, alpha 130 of 255.
- **On:** the same glyph with the front half of every word at full strength. So
  on is exactly off plus brightened word starts, and switching it on only ever
  adds ink.
- The soft tone is a lower alpha, not a second colour, so it still works on the
  hover colour (same reason the Normalize cut-out is transparent). It is
  worked out from the colour's own alpha too.
- White (`PAGE_ICON_COLOR`), drawn at 4x and only scaled down, like the other
  page icons.
- The user chose 130 over 160 and 190. My lean was 160: at 130 the off glyph is
  fairly dim next to the other white icons and could read as "disabled". Not
  seen on a real screen yet, to be judged in step 6. The one number to change
  is `_BOLD_STARTS_SOFT_ALPHA`.
- Rejected on the way: a thicker front (looked like bolts, L-shapes and arrows
  at 24px), and a dim off state with a bright on state where on had less ink.

How it was checked:

- tests/test_icons.py: 40 tests, up from 10 (30 new, all about the new glyph and
  icon, none of the old ones changed). They read pixels, with no window.
- 21 deliberate breaks of the glyph and icon code, all caught. The first pass
  left three alive (a bad target in my own script, a colour test that could not
  tell white from grey, a missing test for a size other than 24); all closed.
- Three tests first failed on tolerances, not on the glyph: the resize overshoots
  next to the sharp step between soft tone and bright front (a 130 pixel reads
  121, a 200 red reads 215). Checked at the pixel positions before the
  tolerances were loosened.
- Diff against the pasted files: icons.py 54 added, 0 removed.

## Step 4 as built (TranscriptInput), split in three commits (all committed)

Details and the measurements are in `claude/bold-starts-step4-notes.md`.

**4a (7880b44), pure helpers with no window.**
`core/bold_spans.py` turns bold stretches into Tk "line.column" places
(`tk_spans`), and `bold_family()` in `core/font_choice.py` maps the OpenDyslexic
Regular family ("OpenDyslexic 3") to the family of its Bold file ("OpenDyslexic3"),
because the two files register as two families. Tk 8.6 (what Python 3.13 on
Windows ships) counts an emoji as two columns and Tk 9 as one, so the widget
asks Tk once and passes `astral_width`. Only `"\n"` ends a line for Tk.

**4b (b93d645), the button and the look.** In `gui/components/transcript_input.py`:
the bold button (36x28, same colour as Normalize, 8 px to its right, icon swapped
for on/off), the tag on the inner Text (`BOLD_TAG`), `set_bold_starts()`,
`on_bold_starts_toggled`, the constructor arguments `bold_starts` and
`on_bold_starts_toggled`, a full re-apply after `set_text()`, and the "Nothing to
change" label moved to column 2, sticky east. The tag font is a plain tuple
`(bold_family(family), int(size), "bold")` read from the Text's font, because
building it through `tkinter.font.Font` rounds 13 px to 9 pt. A scale change does
not raise `<Configure>` on the inner Text, so the edit box is a small
`CTkTextbox` subclass (`_EditBox`) that overrides `_set_scaling` and
`_update_font` and tells the owner. 35 GUI tests, 21 deliberate breaks all caught.

**4c (0f2e8b2), the bold follows the typing.**
What was tried and why it failed matters:

- First plan: on `<<Modified>>`, compare the lines with a saved copy
  (`changed_lines`) and re-bold only the lines that differ. A fuzz test found it
  wrong. Tk keeps a tag with the characters it was put on, so when new text pushes
  old text down a line, that line reads the same as before while its tag has moved
  away and the new line is bare. A realistic case: select all and paste the same
  text back with one typo fixed, and every line but one loses its bold. It also
  cost a whole-text read per keystroke (11 ms at 30 pages, 62 ms at a novel).
- What it was first (replaced on 21.10.2026, see "The paste crash"): `_EditBox`
  puts a thin forwarder in front of the Text widget's own Tcl command (rename it,
  register a Python command under its name, as IDLE does). The forwarder is now a
  Tcl procedure; the rest of this paragraph still describes what it does. Tk's own typing, paste and cut bindings call that command directly, so
  this is the only place to see them. Every call passes through unchanged (results
  and `TclError`s too); after an insert, delete or replace, `on_edited(first, last)`
  gives the first and last line touched. The widget bolds just those lines again.
  Several-range deletes report `(None, None)` and the whole text is bolded again.
  Undo and redo need no case: Tk runs them as ordinary inserts and deletes through
  the same command. The forwarder is removed in `destroy()`.
- `changed_lines` was deleted as dead code, with its tests.
- A bold keystroke now costs 0.4 to 0.5 ms from 12,000 to 240,000 words (about
  2.8 ms in 120-word paragraphs). Turning it on takes 74 ms at 30 pages and 1.4 s
  at a 240,000-word novel.
- **Tk is quadratic in tags per line.** Adding tags to one line costs time that
  grows with the square of the count, however they are added: 1,000 words 0.1 s,
  3,000 words 0.8 s, 12,000 words 8 s, same with a colour tag, reverse order, one
  call, or building the tagged text in one pass (worse). A pasted transcript that
  is one long paragraph would freeze the window, so `core/bold_spans.MAX_BOLD_LINE`
  = 4000 characters (about 650 words, about 30 ms): longer lines are left plain and
  the feedback label says "Long lines stay plain". Open for the user: a lazy
  approach that bolds only what is on screen would remove the limit, at the cost
  of scroll hooks and a lot more code.
- Reading the whole text after every edit (the Normalize icon check) is slow with
  bold on (Tk assembles the text from many pieces: about 125 to 157 ms at 240,000
  words, against 0.8 ms untagged). `_refresh_normalize_button` now reads it only
  when something has been normalized (`can_revert` already short-circuits on that).
- Test hygiene: a destroyed CustomTkinter root leaves its recurring timers
  pending, which print errors during the next test module's event loop. The new
  test roots cancel all pending timers (`after info`) before destroying.
- Checks: 167 tests across the three bold test files on Tk 8.6 and Tk 9, 33
  deliberate breaks all caught (two survivors of the first pass were equivalent
  mutants, one was a broken mutant, and one real gap, a missing test for the
  whole-text fallback, was closed).

## Step 5 as built (the wiring), two commits (both committed)

**5a (bb738a4): canvas, detached window, preview window.** Files:
`gui/components/canvas.py`, `detached_window.py`, `selection_preview_window.py`,
`tests/conftest.py`, new `tests/test_bold_starts_wiring.py` (21 tests).

- `Canvas` takes `bold_starts_enabled` and `on_bold_starts_toggled`. It hands
  its `_handle_bold_starts_toggled` to the main `TranscriptInput` and to the
  detached window. A click calls `set_bold_starts_enabled` (updates the main box
  and the detached window, never a preview) and then tells the owner.
  `set_bold_starts_enabled` itself never tells the owner, which is only for a click.
- `DetachedTranscriptWindow` takes `bold_starts_enabled`, `on_bold_starts_toggled`
  and has `set_bold_starts_enabled`.
- `SelectionPreviewWindow` takes only `bold_starts_enabled` (no callback), so its
  button is its own.
- `tests/conftest.py` gained the opt-in module fixture `fresh_widget_image_caches`.
  Reason: `CanvasToolbar` caches `_BOOKMARK_IMAGE` and `gui/theme` caches
  `_icon_photo_image`, both made for the first Tk root, so a second root in one
  process fails with "image pyimageN doesn't exist". `test_gui_smoke.py` shares one
  root for the whole module for that reason. New modules that build a toolbar (a
  Canvas or the app) ask for the fixture. It hands back the reset function, for
  modules with several roots in turn.

**5b (the commit after bb738a4): the app.** `gui/app.py` got three additions:
the handler `_handle_bold_starts_toggled` (calls
`settings_store.set_bold_starts_enabled`, which saves at once), the callback passed
to `Canvas`, and the saved look passed to `Canvas`. Settings, Apply, profiles and
import are not involved (import restarts the app). New
`tests/test_bold_starts_app.py` (7 tests, each run twice, once with the look saved
as on and once as off).

Checks: 17 of 17 deliberate breaks of 5a and 7 of 7 of 5b all caught (5b's first
pass left three alive: canvas not given the saved look, always told on, also saves
another setting; closed by running the module with saved on and off and by checking
changes both ways). Wiring, app and smoke tests together: 158 passed on Tk 8.6.
Full suite on Tk 8.6 in the sandbox: 1670 passed, 3 failures that need `LICENSE`,
`README` and `docs/` (not copied). The user ran the whole suite on their machine
after each commit: green.

Known harmless quirk: in a full run, error text ("bgerror ... application has been
destroyed") can show at the start of `test_transcript_input_bold_live.py`. It comes
from timers left by the smoke module's destroyed app, was there before, and a fix
would be a timer cancel in the smoke fixture's teardown (a whole-file paste of a
2,400-line file). Not done. Offered to the user; no answer needed.

## The paste crash (found in step 6, 21.10.2026)

The user pasted into the draft on Windows and the whole app closed, with the look
on or off. Traceback: `_tkinter.TclError: text doesn't contain any characters
tagged with "sel"` out of `_forward_to_tk` in `_EditBox`. The fix changed only the
edit box and its new test file.

**Cause (reproduced, not guessed):**

- Tk's own bindings call the Text command inside a Tcl `catch`, and expect it to
  fail sometimes: `tk_textPaste` runs `catch {$w delete sel.first sel.last}` when
  `tk windowingsystem` is not x11 (so on Windows), and `tk_textCopy` and
  `tk_textCut` run `catch {$w get sel.first sel.last}`. With nothing selected the
  call fails on purpose.
- The 4c forwarder was a Python command (`createcommand`). When such a command
  raises, `_tkinter` keeps the exception in its `errorInCmd` flag and raises it
  again out of `mainloop()`, even though Tcl caught the error. So Ctrl+V with no
  selection closed the app. Ctrl+C and Ctrl+X with nothing selected had the same
  crash.
- It is not tied to the bold button: the forwarder is always installed.
- **Why the tests missed it:** they drove Tk with `update()`, which does not check
  that flag, and never ran `mainloop()`. The paste tests also ran on Linux, where
  Tk skips the failing delete. Lesson: any GUI test that involves a Tcl `catch`
  around a Python command must run `mainloop()`, and a test that depends on the
  platform needs `windowingsystem` faked.

**Fix:** the forwarder is a Tcl procedure (`_FORWARDER_BODY` in
`gui/components/transcript_input.py`). Insert, delete and replace first ask a
Python hook (`_before_edit`) which lines they touch, run the real command, and only
if it succeeded tell a second hook (`_after_edit`). Every other call goes through
`tailcall`. Results and errors reach the caller untouched, as on a plain Text
widget. The hooks are registered with `Misc.register`, which wraps them so they
cannot raise into Tcl. Two Tcl details that bit during the fix: `catch` reports
level 0, so `dict incr options -level` is needed before `return -options`, or the
edit runs twice; and `tkapp.call("list", x)` returns a tuple, so command names go
through the `_tcl_word()` check (letters, digits, `.`, `!`, `_` only).
Rejected: swallowing errors in a Python forwarder (what IDLE does). Parts of the
app rely on the `TclError` the widget gives.

**Checks:** new `tests/test_transcript_input_edit_forwarder.py`, 21 tests that run
a real `mainloop()` through the real Copy, Cut and Paste bindings and compare with
a plain Text widget (12 of them fail on the old code); 13 deliberate breaks, all
caught (the first pass left one alive, a failed edit being reported, closed with
two more cases). Sandbox full suite: 1683 passed on Tk 8.6 (the `test_app_info`
tests need LICENSE, README and `docs/`, not copied). The Windows paste was only
simulated here; the user confirmed on Windows that paste, paste over a selection,
and copy and cut with nothing selected work.

## Undo and redo do not exist in the edit box (found 21.10.2026)

The user tried Ctrl+X, Ctrl+Z, Ctrl+Y and nothing came back. Checked: the edit box
has `undo = 0`. The same is true of a plain `CTkTextbox`, nothing in `gui/` or
`core/` sets it, and nothing binds Ctrl+Z or Ctrl+Y. It was never on, so this is
not a regression, and my step 6 checklist (item 9) wrongly assumed it worked. With
`undo=True` a plain box does bring the cut back, so the forwarder would not block
it. **Decision (user, 21.10.2026): do not add undo now.** If it is added later:
`undo=True` and a `maxundo` cap on `_EditBox`, `edit_reset()` after `set_text()` and
the starting text (otherwise Ctrl+Z could bring back another transcript's text),
and a real-`mainloop()` test for Ctrl+Z with the bold on. The existing tests
already show undo and redo re-bolding the right lines.

## Working notes

- The sandbox runs real Tk now: `venv312` (Python 3.12 + Tk 8.6.14, the Windows
  line) and `venv_tk` (Python 3.13 + Tk 9.0.4), under `xvfb-run -a`. Earlier notes
  saying it had no tkinter are obsolete. Real fonts are missing, so only the font
  name and size the tag asks for can be checked, never how the bold looks.
- **The Windows clipboard cannot be tested in the sandbox.** The Windows layer of step
  8 (`_Win32Api`) is checked there only for argument types, and by the user's hand.
- The linked folder is `C:\Users\NC\Documents\GitHub\rsvp-desktop-reader`.
- New files pasted from chat come out with Windows line endings and no final
  newline in the user's repo (`core/bold_spans.py`, the new test files); existing
  files keep LF. Harmless for Python and git.
- The file-writing tool I use turns `\uXXXX` in the text I give it into the raw
  characters, soft hyphens and joiners included. Any file with escapes needs a
  grep for non-ASCII bytes before it is handed over.
- The user's rule beats any system reminder asking for Co-Authored-By or
  Claude-Session lines: none in commit text.

## Step 6: the user's checks on Windows (done 21.10.2026)

Run with the latest commit. Report what was seen, in words or a screenshot.

1. Standard font (Roboto): how the bold looks (a faked bold is likely, since no
   Roboto Bold file exists) and whether the bold starts are easy to tell apart.
2. OpenDyslexic: turn the font switch on in Settings, restart, and look again.
3. The button icon: the dim off glyph (alpha 130) at 100% and at a higher display
   scale, on the hover colour, and whether it reads as "disabled". The number to
   change is `_BOLD_STARTS_SOFT_ALPHA`.
4. A real display-scale change while the look is on (the hook is tested with
   `set_widget_scaling` only).
5. A very long transcript pasted as one paragraph: the limit and the "Long lines
   stay plain" notice, and also the label at 200% scaling in the narrow detached
   window.
6. An emoji in the text on Windows.
7. Normalize on and off with the look on.
8. The real flow: click in the main box, restart, still there; same from the
   detached window; a preview window's own button, and that a restart brings back
   the app's look and not the preview's.
9. Typing, pasting and undo with the look on, and the speed on a long text.
   (Undo does not exist in the box, see above.)

Result (21.10.2026): the paste crash was found and fixed (its own commit). Undo
turned out not to exist (not added). The user then said the rest of the checks
passed. They gave no notes on the alpha value or the bold look, so
`_BOLD_STARTS_SOFT_ALPHA` stays at 130. Failures found here become their own
commits.

## Step 8: copy with the bold into Word (done 21.10.2026), three commits

The user pasted text into Word and Notepad and saw no bold. Cause: Tk copies plain
text only, and tags are not part of that. Notepad can only hold plain text, so it
can never show bold. Word shows bold if the clipboard also carries a rich format.

**Decisions (user, 21.10.2026):** the trigger is **both**: Ctrl+C while the bold look
is on, and a "Copy with bold" row in the right-click menu. With the look off, Ctrl+C
is untouched. Cut stays plain (the text is gone from the box afterwards). Format:
HTML ("HTML Format", CF_HTML), my choice, because Word, Outlook and Google Docs read
it, where RTF is mostly Word and WordPad.

**8a, `core/rich_copy.py` and `tests/test_rich_copy.py` (pure, no window).**
`cf_html(segments)` takes (text, is_bold) pieces and returns the UTF-8 bytes of the
clipboard format; `segments_text(segments)` is the plain text next to it.

- The header's four offsets are UTF-8 BYTE counts (Cyrillic 2 bytes a letter, emoji
  4), measured from the encoded text. The header is fixed-width (ten digits), so it
  is measured first and filled in after.
- Each line (only "\n" ends a line, like Tk) is one paragraph, `<p style="margin:0">`,
  the way plain text pastes into Word. `<b>` around bold stretches, neighbouring
  pieces with the same boldness joined. `& < >` escaped.
- HTML squeezes spaces and Word follows, so a space at a line edge or next to
  another space or a tab becomes `&nbsp;`, a tab is four of them, an empty line
  keeps one `&nbsp;`. Control characters (a Windows CR included) are left out of the
  HTML only, never out of the plain text.
- No font is set and the paragraph margin is 0. Both were guesses about Word; the
  user saw the result in Word and said it works.
- Checks: 40 tests, header read back and every offset checked against the bytes with
  Cyrillic and emoji; the HTML parsed back into (character, bold) per line and
  compared with the input, including 400 random texts; 1M characters convert in
  about 1.1 s. 31 deliberate breaks, 30 caught, 1 equivalent (the text before the
  fragment is pure ASCII, so characters and bytes agree there).

**8b, `gui/rich_clipboard.py` and `tests/test_rich_clipboard.py`.**
`copy_rich(owner, plain, html, api=None)` puts CF_UNICODETEXT (13) and "HTML Format"
on the clipboard. Never raises; False means "copy the plain text the ordinary way".

- Windows refuses SetClipboardData after EmptyClipboard when the clipboard was opened
  with a NULL owner, so `owner` is a real window handle (`inner.winfo_id()`).
- Retries OpenClipboard 5 times, 20 ms apart (a clipboard manager can hold it).
- Plain text gets CRLF (no doubling), UTF-16LE and a closing zero; HTML a closing
  zero. Everything that can fail alone is done before the clipboard is touched.
  Memory goes to the clipboard on success and is freed only when refused.
- The decisions work on any object with the Windows calls, so they are tested against
  a fake clipboard (busy, out of memory, lock or copy fails, data refused). The thin
  `_Win32Api` sets argtypes and restype on every call, pointer sized (a 32 bit
  address corrupts memory on 64 bit Windows); a test checks that against a fake
  `ctypes.WinDLL`.
- Checks: 26 tests; 37 deliberate breaks, all caught after closing two gaps (the
  constant 13 not pinned, a copy test whose data ended in zero bytes).
- Hand check on Windows with a throwaway script: Word showed the bold, the emoji,
  the empty row and the leading spaces. A read-back script listed formats 13, "HTML
  Format", 16, 1 and 7 (Windows makes 1, 7 and 16 itself) and Tk read the plain text
  back correctly. The user first reported nothing pasting into Notepad after that
  script; it was never reproduced (the clipboard held correct plain text), and with
  the real Ctrl+C the user only noted there is no bold in Notepad, which is expected.

**8c, `gui/components/transcript_input.py` and
`tests/test_transcript_input_rich_copy.py`.**

- `_selection_pieces()` reads the selection off the screen with Tk's `dump -tag
  -text` (the raw Tcl call: tkinter's `dump()` groups the answer in Python and takes
  twice as long). The start state is asked with `tag_names(sel.first)`, since dump
  does not report a tag that began before the range. Only BOLD_TAG counts, so what
  is copied is exactly what is seen (long lines left plain stay plain) and no
  Tk column has to be turned into a Python position (the emoji trap).
- `_copy_with_bold()` refuses (False) unless the pieces add up to exactly
  `get(sel.first, sel.last)`, then calls `copy_rich`.
- Ctrl+C: `<<Copy>>` bound on the inner Text; with the look on and a successful rich
  copy it returns "break", otherwise Tk's own plain copy carries on.
- Right-click: a "Copy with bold" row while the look is on (the menu now opens for
  that alone, so the selection preview window gets it too). Success shows "Copied
  with bold"; if the rich copy fails it copies the plain text itself and shows
  "Copied without bold" (it re-reads the selection, falling back to the text the
  menu was opened with).
- Speed: a normal selection is instant; about 1 s per 500,000 characters, a
  select-all of a whole novel takes a few seconds.
- Checks: 35 tests (real `mainloop()`, `copy_rich` faked), full suite 1784 passed on
  Tk 8.6, the new file also on Tk 9; 36 deliberate breaks, all caught after closing
  three gaps (a different tag ending inside a bold stretch, an uncaught Tk error in
  the handler, one redundant guard that was simplified). User checked on Windows:
  works in Word.
- Two of my own test mistakes worth remembering: the popup must be mapped
  (`root.update()`) before `event_generate("<Button-1>")` reaches a row, and "hello"
  is shown **hel**lo (five letters, three bold).

## Plan, one commit per step

1. DONE, committed: `core/bold_starts.py` and `tests/test_bold_starts.py`.
2. DONE, committed: the `bold_starts_enabled` setting.
3. DONE, committed: the two glyphs and `bold_starts_icon()` in `gui/icons.py`.
4. DONE, committed: `TranscriptInput` (4a, 4b, 4c).
5. DONE, committed: wiring (5a, 5b).
6. DONE (21.10.2026): the user's checks on Windows. The paste crash became its own
   fix.
7. DONE (21.10.2026, see "Step 7 as done"): docs and release: usage, FAQ, data.md (the new key), README feature line,
   then release notes and the version bump last (v3.7.0). The research is done at
   this stage, together with the docs, not before. Mention in the usage doc and the
   FAQ: the long-line limit (4,000 characters), that Ctrl+C and the right-click
   "Copy with bold" carry the bold to Word while the look is on, that Notepad and
   other plain-text targets get the words without bold, that Cut stays plain, and
   that Word draws the bold in its own font. Also the name check and wording rules
   below.
8. DONE (21.10.2026): copy with the bold into Word (8a core, 8b clipboard writer, 8c
   wiring). The user confirmed it in Word.

## Step 7 as done (21.10.2026)

Two docs commits and then the release, all by the user from whole files given in chat.

- **Docs commit** (the commit after aa8bf02, "Documented bold word starts and copying
  with bold in the FAQ and usage pages"): `docs/faq.md` (new entries: what the bold
  button does, how to copy with bold into Word, whether it helps, whether it is the
  same as Bionic Reading), `docs/usage.md` (new section "Bold word starts and copying
  with bold" before "The detached window", plus small mentions under Normalize,
  selection reading, shortcuts, Profiles "never changes" and "When changes take
  effect"), `docs/data.md` (the `bold_starts_enabled` row, profile exclusion, export
  note), `docs/architecture.md` (new core section, edit box and clipboard paragraphs).
- **README and version commit:** feature bullet, project tree (3 core modules,
  `gui/rich_clipboard.py`, 12 test files), roadmap line "Bionic Reading" replaced by
  the struck-through plain wording, trademark paragraph in the License section,
  `APP_VERSION = "3.7.0"` in `core/app_info.py`.
- **Wording decisions:** the feature is never called by the trademarked name (UI,
  docs headings, settings key, release title). The user decided (21.10.2026) that the
  docs should name the owner, so the FAQ entry "Is this the same as Bionic Reading?",
  the README License section and the release notes say it is a trademark of BRCG
  Casutt GmbH, that the project is not affiliated with it, and that the app does not
  use its software. I advised against using the name as the feature's name or in the
  draft release (implies affiliation and a benefit claim); not legal advice.
- **Research recorded in the FAQ (read on 21.10.2026):** Beelders 2025, J. Eye Movement
  Research, doi 10.3390/jemr18050049 (53 adults, 131.1 vs 130.8 wpm, p = 0.9, fixation
  232.9 vs 228.4 ms); Mozina, Kovacevic and Blaznik 2025, Sage Open, doi
  10.1177/21582440251376158 (114 adults, bold slightly slower on screen, 37.58 vs
  36.57 s, no overall comprehension difference); Parker, Lee, Wang and Joseph 2026,
  Royal Society Open Science, registered report with 90 skilled adults (read only
  through a ScienceBlog write-up, so cited without a link; first fixation moved toward
  the start of 8-letter words, no change in reading time or comprehension, readability
  rating 7.48 plain vs 6.76 start-bold). Not cited: the Readwise 2022 company test
  (2,074 completed, 325.3 vs 327.9 wpm, p = 0.055, comprehension 88% both) and the
  Springer paper "To boldly go where no text has gone before" (could not be read,
  rate limited). The phys.org article also failed to load.
- **Release:** title `v3.7.0 - Bold word starts`, tag `v3.7.0`. The notes are
  archived in `claude/release-notes-archive.md`. The paste crash was left out of the
  notes because it was only ever in unreleased code.
- Not verified by me: the trademark owner details come from a US trademark listing
  (BIONIC READING, serial 79212988, owner BRCG Casutt GmbH) and the owner's website;
  the docs say "a trademark", not "registered".

## Open ideas after the release (none requested)

- Undo and redo in the edit box (never enabled; the user said no need for now):
  `undo=True`, `maxundo`, `edit_reset()` after `set_text` and the initial text, and a
  real-`mainloop` test.
- A tunable `fixation_length()`; lazy bolding of only the visible part, which would
  remove the 4,000-character limit; the dim-icon alpha `_BOLD_STARTS_SOFT_ALPHA`
  (130, no complaint so far); a timer cancel in the smoke fixture teardown.
- Docs gap: the architecture page's paragraph on what a profile does not hold still
  lists only "no font switch" and does not name the bold look (data.md and usage.md
  do).

## Name check (19.10.2026)

Checked on the owner's own pages only. I could not reach the national registers
themselves (the search engine returned nothing from them), so the registration
numbers below are the owner's claim, not independently verified.

- bionic-reading.com writes the name as **Bionic Reading®**, says "The
  intellectual property of the Bionic Reading® method is protected by patent
  rights, copyrights, and trademark rights", and lists WIPO, USPTO, EUIPO, INPI
  and IGE-IPI logos under "Our global registrations".
- Its page https://bionic-reading.com/patent-trademark/ lists trademark
  registrations: US 5557651, Canada 2211148, Japan 1684673, EU 015969488, UK
  UK00915969488, Australia 1684673, New Zealand 1219946, Switzerland 707270,
  Liechtenstein 1357135. Classes are not stated.
- Rights holder: BRCG Casutt GmbH (Chur, Switzerland), "the exclusive rights
  holder"; Bionic Reading AG is its authorized partner for development and
  sales. The Apple listing shows "©2024, Renato Casutt, Bionic Reading AG".
- Patent: the page names only a French publication, **FR1755215**, with no
  grant or status and no claims shown. Whether any patent is in force, and what
  it claims, is UNKNOWN to me.
- They sell fonts, a plugin and **IP and API licences**, so they treat the brand
  and method as licensable.
- The EULA restricts use of their Software, and says trademarks are to be used
  "in accordance with accepted trademark practices". It says nothing about
  others implementing a similar bolding idea.

Consequences for this project (I am not a lawyer, this is not legal advice):

- Do not use "Bionic Reading" as the name of the feature, button, tooltip,
  setting or release title. The name is a claimed registered mark, including in
  the EU, the UK and Switzerland.
- Describe the feature in plain words, for example "bold word starts". A
  one-line factual mention in the docs that it is a similar idea to what is
  sometimes called bionic reading is a different, lower-risk thing than using
  the name for ours. Say it once, with the registered-trademark owner named, or
  leave it out. The user decides.
- The method itself (bold first letters of words) is the open question, because
  of the FR1755215 publication. The user should know that before releasing
  publicly. If it matters to them, a patent register lookup (Espacenet, INPI) or
  a lawyer settles it. I could not.
- Step 8 does not change any of this, but a copied-out bold text travels beyond
  the app, so the wording in the docs matters a little more.

## Wording and evidence (docs stage)

- Do not claim it helps. It is a comfort setting.
- Check the research when the docs are written (step 7), the way it was done
  for the font and spacing (the FAQ entry "Do the OpenDyslexic font and letter
  spacing actually help?" is the model). Not done yet, so no figures here.

## Out of scope

Bionic in the reader, the peripheral line or profiles, an adjustable bold
strength, and any claim that it helps reading speed or comprehension. Bold in
Notepad or any other plain-text target is impossible, not just out of scope.
