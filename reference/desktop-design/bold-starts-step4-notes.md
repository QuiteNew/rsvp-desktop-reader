# Bold word starts, step 4 (TranscriptInput): findings and results (20.10.2026)

Companion to `claude/bionic-reading-design.md`. Steps 1 to 3 are committed in the
user's repo (algorithm, setting, icons), and so are step 4a and 4b. Step 4c is
written and tested and is to be committed. This file holds what was found while
planning and building step 4, how step 4 was split, and what was checked in each
part.

## The sandbox can run real Tk now

Earlier notes said the sandbox has no tkinter. That is fixed for the Python I
use for GUI tests:

- `apt-get update` first, then `apt-get install python3.12 python3-tk tk8.6`.
  That gives Python 3.12 with **Tk 8.6.14**, the same Tk line as Python 3.13 on
  Windows (8.6.15). A venv with customtkinter 6.0.0, pillow, pytest: `venv312`.
- `uv python install 3.13` gives a 3.13 build with **Tk 9.0.4** (`venv_tk`), a
  second opinion for how Tk 9 behaves.
- GUI tests run with `xvfb-run -a`. Real fonts (Roboto, OpenDyslexic) are not
  there, so only the font name and size the tag asks for can be checked, not how
  the bold face looks. That stays a step 6 check on the user's machine.
- For a full-suite run the whole project has to be staged (core, gui, tests,
  assets) and `python-docx`, `pypdf`, `lxml` installed in both venvs. Without
  `LICENSE`, `README` and `docs/` three `test_app_info.py` tests fail; that is
  the staging, not the code.
- The staged copy of the repo lives in the scratchpad (`repo/`), refreshed with
  `device_stage_files`. The linked folder is `C:\Users\NC\Documents\GitHub\rsvp-desktop-reader`
  (the first path, `C:\!!Git\...`, was refused and is not the one in use).

## Findings that shape the design (4a and 4b)

- **Emoji columns differ between Tk versions.** In "a<emoji>b" Tk 8.6 reports the
  end of the line as column 4 (an emoji counts as 2), Tk 9 as column 3. So the
  columns cannot be assumed. The widget probes once (insert an emoji into a
  throwaway Text, read the column of `end`) and passes `astral_width` (1 or 2)
  to `core/bold_spans.tk_spans`. Bold letters are never astral, so a span never
  cuts an emoji in half; only the columns after one shift.
- **The edit box's font** is `'Roboto -13 {normal roman  }'` on the inner Text
  (a string, exact negative pixel size). Rebuilding it through `tkfont.Font`
  rounds 13 px to 9 pt, so the bold tag font is a plain tuple
  `(family, size, "bold")` built from `tk.splitlist` of that spec.
- **Scale changes do not raise `<Configure>`** on the inner Text, so the bold tag
  font would go stale after a display scale change. CustomTkinter only reaches
  the inner Text through `_set_scaling` and `_update_font`, so the edit box is a
  tiny `CTkTextbox` subclass (`_EditBox`) that overrides those two and tells the
  owner. Tested with `ctk.set_widget_scaling` (13 px becomes 20 px at 1.5, and
  the tag follows).
- **OpenDyslexic:** the Regular face is the family "OpenDyslexic 3" and the Bold
  face is the family "OpenDyslexic3" (see `core/font_choice.py`). Asking for bold
  in the regular family would fake the bold. `bold_family()` maps one to the
  other (step 4a).
- **`CTkTextbox.tag_add` takes only two indices**, and `tag_config` refuses
  `font`, so everything about the tag goes through the inner Text (`_textbox`).
- **Only `\n` ends a line for Tk**, not the other separators `str.splitlines()`
  knows. `tk_spans` splits on `"\n"` only.
- **Layout problem in the button row (decided, built in 4b).** The detached
  window is 500 px wide, so its button row is 460 px and "Start reading" starts
  near x=160. The feedback label "Nothing to change" sat at x=44 to about x=149.
  A second 36 px button pushes it to x=88 and the label would overlap "Start
  reading" by about 30 px. The user agreed to move the label to the right-hand
  end of the row (column 2, `sticky="e"`), with 100% scaling at 2K looking fine
  for them and 200% unchecked, which is why it moves for safety.

## How step 4 was split (one commit each)

- **4a** (committed, 7880b44) pure helpers, tested without a window:
  `core/bold_spans.py` (`tk_spans`), `bold_family()` in `core/font_choice.py`.
  Tests: `tests/test_bold_spans.py`, `tests/test_bold_family.py`.
- **4b** (committed) `gui/components/transcript_input.py`: the button next to
  Normalize (36x28, same colour, `bold_starts_icon(is_on)`), the tag, the bold
  font with the scale hook (`_EditBox`), full re-apply after `set_text()`,
  `set_bold_starts()`, the `on_bold_starts_toggled` callback, the constructor
  arguments `bold_starts` and `on_bold_starts_toggled`, the feedback label move.
  GUI tests in `tests/test_transcript_input_bold_starts.py` with its own
  module-scoped root (the pattern of `tests/test_reader_letter_spacing.py`).
- **4c** (written and tested, to be committed) the bold follows the typing.

Step 5 (wiring through canvas, detached window, preview window and `gui/app.py`
with the saved setting) comes after.

## 4c: what was tried, what failed, what it is now

**First plan, abandoned: compare the lines with a saved copy (`changed_lines`).**
On `<<Modified>>`, compare the line list with a snapshot and re-bold only the
lines that differ. A seeded fuzz test found it unsound (failed at seed 1, step
116):

- **A Tk tag stays attached to the original characters.** When new text is
  inserted at the start of a line, the old text (and its tags) moves down, and the
  new line is bare. The two lines can then read exactly like before, while the
  tags sit somewhere else. So a content diff cannot tell which lines lost their
  bold.
- A realistic case that breaks it: select all, paste the same text back with one
  typo fixed. Every line but one keeps its text but loses its bold.
- It also read the whole text on every keystroke (11 ms at 30 pages, 62 ms at a
  novel).

**What replaced it: a command forwarder in front of the Text widget.**
(The technique IDLE uses.) `_EditBox` renames the widget's Tcl command to
`name + "_original"` and registers a Python command under the old name. Tk's own
key bindings, `tk_textPaste` and `tk_textCut` call `$w insert` and `$w delete`
directly, so this is the only place that sees typing.

- Every call passes through unchanged, results and `TclError`s included.
- For `insert`, `delete` and `replace` the first and last line the edit touched
  are worked out before the call (new text counted by its newlines) and handed
  to `on_edited(first, last)` after it.
- A delete with several ranges reports `(None, None)`, and the whole text is
  bolded again.
- Undo and redo run ordinary inner inserts and deletes through the same command,
  so they need no special case (an earlier "edit undo/redo" branch was removed
  after seeing that).
- `destroy()` removes the forwarder (`rename name ""`, then the original back).
  Checked: no `_original` command is left behind, on Tk 8.6 and Tk 9.
- `set_text` and the constructor pause edit handling so those edits are not bolded
  line by line just before the whole text is bolded at once.
- `changed_lines` and its tests were deleted as dead code.

## 4c: Tk's tag cost is quadratic per line

Measured on Tk 8.6, one line, time to add the bold tags:

| words in the line | time |
|---|---|
| 1,000 | 70 to 100 ms |
| 3,000 | about 0.8 s |
| 12,000 | about 8 s |

- The cost grows with the square of the number of tag toggles in a line.
- It makes no difference whether the tag changes the font or only a colour,
  whether it is added in one call or batches, or in reverse order. Building the
  tagged text with `insert(text, tag, ...)` in one pass is worse.
- Text with many short lines is linear: 240,000 words take about 1.4 s for a full
  apply.
- So `core/bold_spans.MAX_BOLD_LINE = 4000` characters (about 650 words, about
  30 ms). Longer lines stay plain and the label says "Long lines stay plain".
  The label text is at most 24 characters so it fits beside Start reading.
- Open question for the user: a lazy approach that bolds only what is on screen
  (scroll hooks) would remove the limit, at the cost of a lot more code. Not
  done.

## 4c: the whole-text read

`get` of the whole text gets slow once there are many tags (125 to 157 ms at
240,000 bold words, against 0.8 ms untagged). The forwarder adds nothing to that.
`_refresh_normalize_button` read the whole text after every edit to check
`can_revert`, so it now reads it only when something has been normalized
(`self._pre_normalize_text` is set).

## 4c: timings (Tk 8.6, sandbox)

- A bold keystroke: about 0.4 to 0.5 ms from 12,000 to 240,000 words; about 2.8 ms
  in 120-word paragraphs.
- A wall of prose (a very long line) is skipped in about 2 ms.
- Turning bold on, full apply: 74 ms at 12,000 words, 315 ms at 60,000, 1,439 ms
  at 240,000.

## 4c: test hygiene

A destroyed CustomTkinter root leaves its recurring timers pending, and they fire
inside the next test module's event loop (the "bgerror ... application has been
destroyed" noise). The fix is in the module `root` fixture teardown of both GUI
test files: cancel every pending `after` timer (`after info`) before
`destroy()`. A drain loop did not work. The bisect that found this was broken
twice by my own harness (a relative python path, then `resolve()` losing the
venv), which hid the cause for a while.

## Checks done for 4a

- 66 tests (`test_bold_spans.py` 50, `test_bold_family.py` 16), all pass on
  Python 3.12 (Tk 8.6 build) and 3.13. (After 4c `test_bold_spans.py` has 45
  tests: the `changed_lines` ones are gone, the limit ones are new.)
- 20 deliberate breaks of the new code: 19 caught. The one survivor is an
  equivalent change: at width 1 the shift formula adds 0, so the `!= 1` test is
  only a speed shortcut.
- `font_choice.py`: 14 lines added, 0 removed. No non-ASCII bytes in the files.
- The user's committed `core/bold_spans.py` has CRLF line endings and no final
  newline; the tested copy had LF and a final newline. Harmless.

## Checks done for 4b

- 35 GUI tests, all pass on Tk 8.6 and Tk 9 (37 now, the narrow-window label test
  covers both scaling 1.0 and 2.0 and both messages).
- 21 deliberate breaks of `transcript_input.py`, all caught. A control run with
  no change passes, and one mutant was inspected to confirm it fails for the real
  reason (the overlap test measures real widget positions in a mapped 500 px
  window at scaling 1.0 and 2.0).
- Hidden windows never get a real size, so layout tests build a mapped
  `CTkToplevel` and assert the widths are above 1 first.

## Checks done for 4c

- 167 tests across `test_bold_spans.py` (45), `test_transcript_input_bold_starts.py`
  (37) and the new `test_transcript_input_bold_live.py` (about 86) pass on Tk 8.6
  and Tk 9, with no stray noise (run with `-s`, 0 bgerror lines).
- The live tests cover: typing, deleting, joining, splitting and pasting lines;
  the regression cases for the tag-moves-with-characters flaw; only the touched
  lines being recomputed (a spy on `tk_spans`); off, on and `set_text`; very long
  lines (including a fuzz with `MAX_BOLD_LINE` made small); the Normalize icon
  guard; emoji; typing, cut and paste through Tk's own bindings; the forwarder on
  its own (lines reported, errors, return values, undo, destroy); a seeded
  random-edit fuzz against a full recompute; and the whole-text fallback.
- 33 deliberate breaks of the forwarder, the handler, the limit and the icon
  guard, all caught in the end. Of the first pass's survivors, two were
  equivalent mutants, one was a broken mutant, and one was a real gap (no test
  for the whole-text fallback), which was closed with a test.
- One new test failed on unmutated code, which made its mutation meaningless; the
  expectation was corrected and the control and the mutant re-run.
- Whole suite on Tk 8.6: 1635 passed, 3 failed (the `test_app_info.py` tests that
  need `LICENSE`, `README` and `docs/`, not staged). On Tk 9, 7 failed: those 3
  plus 4 letter-spacing tests that fail the same way without my change.
- pyflakes clean, `transcript_input.py` ASCII-only.
- Still not checkable here (step 6, on the user's Windows machine): how the real
  bold face looks in the standard font and in OpenDyslexic, a real display-scale
  change, how the dim off icon (alpha 130) reads, and a very long transcript with
  the notice on screen.
