# Speaker cues: starting note for the new chat (written 09.11.2026)

READ THIS FIRST in the new chat, then `claude/09.11.2026 context.md` (state, tools, house rules).

## How the new chat should begin

The user will explain how they imagine the feature, in their own words, at the start. Do not propose a design, a name, a detection method or any code before that. Listen, ask the few questions that change what is built, then decide together. Slow and steady: a design note first (see "Precedents"), code only after the design is agreed, each step confirmed before the next. Nothing below is decided except what is marked DECIDED.

## What the user has said so far

- The idea, in the user's words on 09.11.2026: the next feature gives the reader a cue that a different character is talking; it could be a visual or an audible sign.
- DECIDED: the feature is called **Speaker cues** ("Ok speaker cues it is"). "Speaker" was preferred over "character" because transcripts have speakers (for example "Interviewer:" or "Speaker 2:") and books have characters; "cues" covers a visual and an audible kind under one name.
- Suggested and not objected to, but not decided: one Speaker cues switch in Settings with two sub-options, Visual (a colour shift or a marker) and Sound (a soft chime), so someone can turn either off. "Audiovisual speaker cues" was floated by the user as a description; the advice was to keep it as the description, not the name.
- In the last message of the previous chat the user wrote "multivisual cues". It is not clear whether that is a typo for audiovisual or a different idea. Ask.
- The README roadmap already lists "Speaker cues" as the next item.

## Open questions to raise (not a plan, not answers)

- What counts as "a different speaker talking", and how does the app know? Possibilities to discuss: a label at the start of a line ("Name:"), a change of quotation marks in a book, a blank line, a marker the user types or inserts in the edit box, or something else. This is the hard part; it decides how much of it can be pure logic in `core/`.
- Which texts is it for: transcripts with named speakers, books with dialogue, both? What does the app do when it cannot tell?
- The visual cue: what changes (the word colour, a marker next to the word, the guide marks, the ribbon of surrounding words, the background), for how long, and how it looks in Light and Dark and with the OpenDyslexic font and letter spacing.
- The audible cue: the app is fully offline and gets bundled by PyInstaller for Windows and Linux (macOS not finished). How is a sound played on each system without a heavy new dependency, and where does the sound file live? (Not researched; do not assume.)
- How it fits the reading engine: chunking (a chunk that crosses a change of speaker), timing and pauses at a change, rewind on resume, skipping and the scrubber, the detached window and the selection preview window (they have their own wiring), the edit box (the bold starts precedent shows a look that exists only in the edit box).
- Where the setting lives: Settings tab, whether it belongs in a reading profile (profiles hold a list of reader settings; see `core/profiles.py`), per transcript or global, defaults, how it is saved in `settings.json`, export and import.
- Accessibility and comfort: not startling (a sound while reading fast), a way to turn it off at once, a note in the docs like the ones for bold starts and the dyslexia font ("a comfort option, not a treatment").
- How it is tested, following Test Suite 2.0: pure logic in `core/` with its own tests, GUI behaviour through the real app windows with real clicks and keys, mutation checks on the new tests.

## Precedents to read before designing

Existing design notes show how earlier features were designed and recorded: `claude/bionic-reading-design.md` and `claude/bold-starts-step4-notes.md` (bold word starts), `claude/dyslexia-font-design.md`, `claude/reading-profiles-design.md`, `claude/chunking-v1-design.md`, `claude/chunking-v2-adaptive-design.md`, `claude/reader-fit-and-scroll-design.md`. The release text of earlier features is in `claude/release-notes-archive.md` and `claude/release-notes-archive-v4.0.1.md`. The reading engine is `core/reader.py` (`ReaderSession`) with `core/timing.py`; the reader widget is `gui/components/reader_display.py`; settings are `core/settings_store.py` and `gui/components/settings_window.py`. Re-read the real files through the device bridge before relying on any of this; file state does not carry over between chats.

## Working rules (short; full list in the 09.11.2026 note)

- Whole files only, never diffs, with the filename and destination in plain text. The project folder is read-only for Claude unless the user asks in that moment for a file to be written; ask first if unsure.
- Explain before changing; do not present a guess as a fix; confirm one step before the next.
- Strict `core/` (pure logic) and `gui/` (CustomTkinter) separation; fully offline; Python 3.13 on Windows.
- Humanize code comments and commit titles and descriptions. Title and description separate, description one line per paragraph, no em dashes, no Co-Authored-By or Claude-Session lines.
- With every commit: hash commands, `git add`, `git status --short`, `git diff --cached --numstat` with expected numbers. The user commits and pushes; I cannot push.
- Bugs found along the way go in the release notes under "Bug fixes". Docs are done at the end, with the release (see RELEASING.md). The release number for a new feature is a minor bump (the next one would be v4.1.0).
- New code needs tests in the Test Suite 2.0 style (real app windows, shared fixtures in `tests/conftest.py`, `tests/tk_helpers.py`, `tests/edit_box_helpers.py`; never assert where a running reading "is" without pausing first; never run a second Tk job while the full suite runs).
