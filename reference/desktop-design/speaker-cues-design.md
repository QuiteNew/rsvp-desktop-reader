# Speaker cues - design

Status (12.11.2026, end of the feature): BUILT, merged into `main`, release v4.1.0 in progress. Pull request #3 ("Speaker cues") was merged with a merge commit, `2e3e0a1`, branch kept. PR #1 and #2 had merged earlier parts (PR #2 on 11.11 as `ba5e9de`). The release notes are in `claude/release-notes-archive-v4.1.0.md`. The next piece of work is the CI/CD pipeline; see `claude/12.11.2026 context.md`.

Commits in PR #3 (the last stretch): `3d5775b` 7e (whole-book clipboard test), `f863611` 8a (popups centred on scaled displays), `e02e4d1` 8b-1 (the position setting), `28b1bc5` 8b-2 commit 1 (the reader draws the tag in the top right corner), `29aa6c0` 8b-2 commit 2 (the position choice in the window and the wiring), `d04cfd0` docs pages, `dafbbac` "Release 4.1.0 with speaker cues" (README, RELEASING.md, `APP_VERSION = "4.1.0"`).

Commits in PR #2, all in `main`: `4b6b5d3` 4b, `0108e77` 5, `5831a21` 6a, `c329296` 6b, `0e72106` and `4f65341` 6c, `759b257` 7a, `b2a8e69` 7b, `d8fd94c` 7c, `4fee047` (unused import caught by pyflakes on GitHub). PR #1 held `f87fd37`, `58f65d9`, `2c5c90a`, `fce7107`, `913963b`, `e15885d`.

Guiding rule, the same as chunking: with Speaker cues off, reading must not change in any way.

Read first for how the chat began: `claude/speaker-cues-start.md`.

## 8a: popups placed too far right and down on scaled displays (DONE, `f863611`)

- Seen by the user on Windows: Settings and the windows opened from it (Chunking) spawn lower and further right than they should, partly below the screen.
- Cause, confirmed by reading CustomTkinter's code and by the screenshots' numbers: `center_over_parent()` in `gui/theme.py` centred popups with their unscaled size, while CustomTkinter's `CTkToplevel.geometry()` scales the width and height but not the x and y, and the parent's `winfo_rootx/width` are already screen pixels. So a popup landed (scale - 1) x size / 2 too far right and down. The user's laptop is at 200%.
- Fix: `center_over_parent()` multiplies the size by `ScalingTracker.get_window_scaling(window)` (new helper `_window_scaling()`, 1 when CustomTkinter doesn't track the window) before centring; the geometry string still gets the unscaled size. No bottom/right clamp, on purpose: `winfo_screenwidth/height` only describe the main monitor, and a clamp would pull windows off a second monitor.
- Tests: `tests/test_center_over_parent.py` (6), scaling 1, 1.25, 1.5 and 2, checked against the real on-screen size. One test needed a second go: Windows enforces a minimum width on a titled window (232 against the 200 asked for), so the plain-window test uses 500 x 300. Don't shrink it.

## 8b: the name tag's position (DONE, D16)

- Two positions: above the word (as before) or the top right of the reader, a fixed spot in the reader's top-right corner that never moves while reading (`SPEAKER_TAG_CORNER_MARGIN_PX = 12`, scaled by the widget scaling; placed with `_place_physical(..., anchor="ne")`). Not "following the word's end", which would jump sideways with every word.
- Setting: `speaker_cue_tag_position`, "above" / "top_right", default "above", an unknown value reads as "above", app-wide, not in profiles, travels in export bundles.
- Window: the tick box is now "The speaker's name" with "Above the word | Top right" segmented buttons under it, greyed while the name is off (the choice is kept). The window is 470 x 740 with a list, 470 x 580 without.
- Reader: the horizontal pan only slides the tag when the position is "above". The flash still colours the tag in either position.
- Wiring: `set_speaker_cue_options(name_tag, flash, sound, style, tag_position)`. The argument has a default only in `ReaderDisplay`; it is required in `Canvas`, `DetachedWindow` and the app's `_apply_speaker_cue_settings` (a mutation check showed a default there was never used). Constructors keep `speaker_cue_tag_position="above"`.
- Commits: `e02e4d1` (setting), `28b1bc5` (reader), `29aa6c0` (window and wiring). Mutation checks: setting 10 breaks, reader 12, window 10, wiring 15; all caught after one test fix each in the setting and the wiring.
- Lesson: the two machines were out of sync once. The PC (desktop-h3i8shg) was three commits behind the laptop and the full run failed on collection (`ImportError: cannot import name 'SPEAKER_CUE_TAG_POSITIONS'`). It was a sync problem, not a code bug. Commits made on one machine need a `git pull` on the other.

## 9: docs and release (DONE except the tag)

- Docs commit `d04cfd0`: `docs/usage.md` (a new "Speaker cues" section with subsections), `docs/faq.md` (five answers), `docs/data.md` (the `speaker_custom` field and a settings table), `docs/architecture.md` (a "Speaker cues" part in the core layer and a GUI paragraph). Checked with `mkdocs build --strict` in the sandbox; the real check is the Docs workflow on `main`.
- Last commit `dafbbac`: README (feature bullet, file trees, 13 new test files, roadmap "Speaker cues" crossed out, the three workflow badges on their own row with a `<br>`), RELEASING.md (docs commits, merging with a merge commit, tag the tip of `main`, the Linux glibc line in Downloads), `core/app_info.py` bumped to 4.1.0.
- Name (D7): kept "Speaker cues" everywhere. The release title is "v4.1.0 - Multisensory speaker cues".

## Git and GitHub workflow (decided 10.11.2026)

- All work on `speaker-cues`. Merge into `main` at milestones through a pull request, always with "Create a merge commit" (never squash or rebase), leave the merge title as GitHub fills it, keep the branch, then update local `main` in GitHub Desktop (switch to main, Fetch origin, Pull origin, switch back).
- The user cares about the GitHub contribution graph. Only commits on the default branch count; GitHub's docs say the author date decides the day, so waiting to merge costs nothing.
- The Tests workflow runs only on pushes to `main` and on pull requests: pytest under xvfb, then pyflakes (`python -m pyflakes core gui tests main.py`). A push to the branch while a PR is open re-runs the PR's checks. The Docs workflow runs only on pushes to `main`.
- The user's timer script pushes `main:main` explicitly, so on the branch they push by hand.
- Two machines: desktop-h3i8shg (`C:\Users\NC\Documents\GitHub\rsvp-desktop-reader`, the PC) and desktop-usu3n6f (`C:\!!Git\rsvp-desktop-reader`, a laptop at 200% display scaling; slow under load and on battery).
- GitHub's check results and API are blocked for me; the user sends logs and screenshots. `git ls-remote origin` works read-only from the device shell. The device bridge sometimes drops; retry once, then tell the user.
- On every step: the hash command per file, `git add`, `git status --short` and `git diff --cached --numstat` with expected numbers, title and description separately (one line per paragraph, no em dashes, no Co-Authored-By or session lines). Multi-file commits go as attachments.
- Tk's "invalid command name" and "bgerror" lines in full Windows runs are the known leftover-timer noise since commit 45; they don't affect results.

## Fixes that went into the release notes

- Test suite: `e15885d` (`test_expand_while_a_transcript_is_being_read_still_saves_the_reading` read too short a time for GitHub's faster runner; `READ_LONG_ENOUGH_MS`), `3d5775b` (`test_a_whole_book_is_quick` timed the busy machine; now `process_time` and 15 s).
- App: `f863611`, popups open centred over their window on scaled displays.

## Decided

- D1 Scope: transcripts with speaker labels at the start of a line only. Books are left for a later, separate release.
- D2 The label word stays in the flash; word indices, positions and bookmarks never change.
- D3 Visual cue: a name tag (dimmed: font blended 0.55 toward the background) and a brief flash (330 ms: the tag in the highlight colour and the background warmed 0.18 toward the highlight). Both on by default, each with its own switch. The tag stays visible while paused. Position: see D16.
- D4 Sound: Windows only at first (winsound, async from WAV files in a temp folder; silent on Linux/macOS). No new dependency.
- D5 The on/off switch lives inside the Configure speaker cues window. No "turn it on first" error.
- D6 Speaker pause: SPEAKER_PAUSE_MULTIPLIER = 3.5 on the last word of a turn, the longer of that and the word's own pause, no switch of its own.
- D7 Name: "Speaker cues".
- D8 Reviewable speaker list: Auto (labels seen at least twice) and Custom (untick, merge, rename).
- D9 No bracket form "[Name]"; ">>" is an unnamed change.
- D10 A label can't start with a small letter.
- D11 Commits may be split when large; multi-file commits as attachments.
- D12 Sound styles bell (default), soft, glass, wood; per-speaker patterns (shape plus pitch): C5; C5-G5; G5-C5; C6; C5-E5-G5; a sixth wraps. Change chime A4. The preview in the window plays with `wait=True`.
- D13 A selection read on its own (right-click Play or Detach) uses the whole transcript's speaker list (`transcript_speakers()`). Words before the selection's first label have no name.
- D14 Speaker cue settings belong to the whole app: changes reach the main reader and the detached window at once; selection previews snapshot them at open time. One `ChimePlayer` for the whole app, made in `gui/app.py`, closed in `_handle_close()`.
- D15 The Configure speaker cues window: button under "Configure chunking" on the Defaults tab; Close and Apply (Apply keeps it open, "Applied."); top part for the whole app (switch, name and flash tick boxes, name position, Sound Off / One chime / Per speaker, Style Bell/Soft/Glass/Wood with "▶ Listen", greyed without sound); bottom part for the open transcript (rows with tick box, editable name, "seen N times", Automatic/Custom, "Back to automatic"; equal-to-Auto saves as Automatic).
- D16 The name tag's position: above the word or top right (see 8b).
- Two lines in a row from the same speaker are one turn: no cue in between.

## What exists (summary; details in the commits)

- `core/speakers.py` (labels, Auto, turns, `clean_custom_speakers`, `transcript_speakers`, `SpeakerRow`, `speaker_rows`, `speakers_to_save`), `core/settings_store.py` (six speaker cue settings: `speaker_cues_enabled`, `speaker_cue_sound`, `speaker_cue_style`, `speaker_cue_name_tag_enabled`, `speaker_cue_tag_position`, `speaker_cue_flash_enabled`), `core/models.py` (`Transcript.speaker_custom`), `core/reader.py` (turns, speaker pause, chunks break at turn ends), `core/timing.py` (`SPEAKER_PAUSE_MULTIPLIER`), `core/chime.py` (styles, patterns, `ChimeGap`), `gui/chime_player.py`, `gui/components/reader_display.py` (tag, flash, chime), wiring in canvas, detached window, selection preview and app, `gui/components/speaker_cues_window.py`, the Settings button, and the popup centring fix in `gui/theme.py`.
- Tests (13 new files): `test_speakers.py`, `test_settings_store_speaker_cues.py`, `test_transcript_speaker_list.py`, `test_reader_speaker_cues.py`, `test_chime.py`, `test_chime_player.py`, `test_reader_display_speaker_cues.py`, `test_whole_transcript_speakers.py`, `test_speaker_cues_wiring.py`, `test_speaker_rows.py`, `test_speaker_cues_window.py`, `test_speaker_cues_settings_in_app.py`, `test_center_over_parent.py`; `test_separator_line.py` expects 15 lines on Defaults. Windows full run before the last commit: 3178 passed, 8 skipped, plus one sidebar rename test (`test_an_empty_or_unchanged_title_is_not_saved[empty]`) that failed once in a 17-minute run and passed on its own; likely cause (inferred, not confirmed): Tk dropped a generated key press when the window lost screen focus. Expected after 8b-2 commit 2: 3179 passed, 8 skipped.

## Working notes (sandbox)

- Before sending ANY file, run `python -m pyflakes core gui tests main.py`.
- `/home/claude/repo` is a clone of the branch with sandbox-only commits; `/home/claude/venv313` has Python 3.13 with the user's requirements plus pyflakes; `/home/claude/venv_docs` has mkdocs-material. GUI tests run under `xvfb-run`. Known sandbox-only failures (fonts and metrics): 3 in `test_reader_letter_spacing.py`, 1 in `test_gui_smoke.py`, 2 in `test_header.py` (scaled display), 1 in `test_settings_pickers_and_resets.py`. A full sandbox run takes about 16 minutes in three parts. If the sandbox was reset, clone the branch again from GitHub.
- The file-writing tool turns `\uXXXX` into raw characters; check delivered files with a non-ASCII grep.
- Mutation runs: `PYTHONDONTWRITEBYTECODE=1`, `python -B`, `__pycache__` removed; foreground, explicit timeout. Don't edit the file under test while a run is going.
- Pin tuning values as plain numbers in at least one test. Window sizes in tests: compare with `round(size * ScalingTracker.get_window_scaling(window))`; the user's laptop is at 200%. Don't test tiny plain windows on Windows: it widens titled windows to a minimum width that grows with scaling.
- Before sending whole files, check the user's folder matches the branch head (read-only, `git --no-optional-locks`).

## Open

1. Whether a transcript can turn cues off for itself (proposed: no). Not built.
2. Whether the edit box shows anything about speakers (proposed: no). Not built.
3. Watch item: `_update_peripheral_context` uses an unscaled `_guide_mark_length()` while the guide marks use `length * scale`. Not raised by the user and not checked in 8b.

## Out of scope for this release

Books and quotation-mark dialogue, sound on Linux and macOS, hiding the label word, per-speaker colours of the words or background, the bracket label form, and speaker cues in profiles.
