# Dyslexia-friendly font and letter spacing - design and status

Status (19.10.2026): SHIPPED as **v3.6.0** (tag `v3.6.0` on `d8c279c`, released
19.10.2026 as "v3.6.0 - Dyslexia-friendly font and letter spacing"). Code, tests,
docs, licences, README and the settings bug fix are all done. Nothing is left
open for this feature except the small loose ends at the bottom.

## Version history (read this before quoting a version)

The work was planned as 3.5.1 (the user's first call: a patch number, because the
release did not seem to deserve a minor bump). The bump commit `9403e35` "Bump
the version to 3.5.1" went in, and then the user changed their mind before
tagging: a feature release is a minor bump, as RELEASING.md says. `d8c279c`
moved it to 3.6.0 and was tagged. **There was never a v3.5.1 tag or release.**
`9403e35` stays in the history. The only two places in the docs that name the
version are the "profiles saved before version 3.6.0 do not hold the letter
spacing" sentences in docs/faq.md and docs/usage.md.

## Summary

Two separate things, both in the Appearance tab:

1. A font switch, labelled "Use the OpenDyslexic font". When on, every font in
   the app becomes OpenDyslexic. Takes effect on the next launch, the same way
   the theme does.
2. A "Letter spacing" level (Off, Small, Medium, Large) for the flashing word in
   the reader. Applies when you press Apply, no restart. In chunk mode the gaps
   between words grow along with it where the font's own space is too narrow.

The two are independent: spacing works with any font, and the font switch does
not touch spacing.

## Decisions (17.10.2026)

- Font: OpenDyslexic (SIL Open Font License 1.1). Chosen by the user from
  OpenDyslexic, Andika, Atkinson Hyperlegible and Lexend. Lexend's licence and
  static files were never verified, so it was not a safe default.
- Scope: whole app, next launch. Not reader-only. This reuses the mechanism that
  already resolves the theme at import time.
- Spacing: letter levels plus wider word gaps in chunks. The user accepted
  discrete levels, not a continuous slider.
- Profiles: the spacing level is part of profiles (an app-wide setting with no
  theme trap, applied live). The font switch stays out, because it needs a
  restart and a profile is meant to apply live. A profile saved before this
  lacks the key, so applying it leaves spacing alone.
- Licences and README Acknowledgments were handled at the docs stage (step 7).

## How it works (as built)

- core/letter_spacing.py: levels, target gaps in em, calibrated choice of gap
  characters, word gap rule, space_text and space_chunk. Pure, plain ASCII (the
  invisible characters are built with chr()).
- core/font_choice.py: takes the switch and returns the heading family, the
  body family and the font files to register. The switch is read with a strict
  check (is True), so a damaged settings file can't turn it on by accident.
- gui/theme.py reads the setting once at import (so a change applies on the next
  launch), uses the choice for FONT_HEADING, FONT_BODY and the registered file
  list, and overrides ThemeManager.theme["CTkFont"]["family"] so widgets with no
  explicit font (the transcript edit box) follow too.
- OpenDyslexic family names: the Regular file is "OpenDyslexic 3" (with a space)
  and the Bold file is "OpenDyslexic3" (no space). They do not group into one
  family, so the body font is the first and the heading font is the second,
  which mirrors Quicksand Medium for body and Fredoka SemiBold for headings.
- Settings: AppSettings.dyslexia_font_enabled (bool, default False) and
  AppSettings.letter_spacing_level (int 0 to 3, default 0). Both travel in
  exports and bundles. Old files load with the defaults.
- Reader: the GUI measures the gap characters once per font, builds the plan,
  and applies space_chunk() both when drawing and when measuring for auto-fit,
  so the fit measures exactly what is drawn. The peripheral line stays
  unspaced. The gap is part of the drawn text, not a layout offset, so the
  placement code is unchanged and the focus letter is never touched.
- Letter spacing levels (target gap in em): Off 0, Small 0.10, Medium 0.18,
  Large 0.30. Starting points tuned by eye, not proven settings. Word gap rule:
  the plain space plus whatever is needed to reach twice the letter gap.

## The OpenDyslexic files (checked 17.10.2026)

OpenDyslexic3-Regular.ttf (237,868 bytes) and OpenDyslexic3-Bold.ttf
(239,556 bytes), both dated 5 Nov 2014. Licence in the name table: SIL Open Font
License 1.1, "(c)2012 by Abelardo Gonzalez". The licence texts for all three
fonts now sit in assets/fonts (OFL-Fredoka.txt, OFL-Quicksand.txt,
OFL-OpenDyslexic.txt), verbatim from upstream.

- 867 code points; every letter, digit, accent and typographic quote in a test
  set is present.
- The plain space is 0.85 em wide (Fredoka's is 0.24 em), so words in a chunk
  are already far apart in OpenDyslexic.
- Vertical metrics at 48px as Tk reports them: ascent 60, descent 24, linespace
  84 (Fredoka 48 / 12 / 60, Quicksand 57 / 15 / 72). Labels are about 40
  percent taller than Fredoka's. The baseline sits at the same offset from the
  label centre, so the focus letter stays at the same height. The guide marks
  measure from the label edge, so they sit about 12px farther out at 48px.
  Judge by eye in the real app.

## The Windows probe (17.10.2026, user's machine)

None of the three fonts has a glyph for the thin-space characters (hair U+200A,
six-per-em U+2006, thin U+2009, punctuation U+2008), so Windows draws them from
a fallback font and the width depends on the font and the machine. Widths in
em per gap at 48px (good to about 0.01 em):

| font | hair | six-per-em | thin | punctuation | plain space |
| --- | --- | --- | --- | --- | --- |
| Fredoka SemiBold | 0.083 | 0.188 | 0.146 | 0.333 | 0.250 |
| Quicksand Medium | 0.104 | 0.167 | 0.208 | 0.250 | 0.271 |
| OpenDyslexic 3 (Regular) | 0.062 | 0.167 | 0.125 | 0.312 | 0.854 |
| OpenDyslexic3 (Bold) | 0.083 | 0.188 | 0.146 | 0.333 | 0.854 |

Gaps are additive and predictable on Windows. The same character is up to a
third wider or narrower depending on the font, hence the per-font calibration
at runtime. Every level lands within about 0.02 em of its target.

## Not Windows

register_fonts() only works on Windows, so on Linux and macOS none of the
bundled fonts (Fredoka, Quicksand, OpenDyslexic) are loaded and Tk falls back
to another family unless the font is installed on the system. This is how the
app already behaved. The docs and release notes say so where it matters.

## What the research says (for README and docs wording)

Do not claim the feature helps. The docs describe these as comfort settings.

- Typefaces made for dyslexia have weak evidence. Wery & Diliberto (Annals of
  Dyslexia, 2017; 11 children) found no benefit from OpenDyslexic. Rello &
  Baeza-Yates (2013) found no significant gain. Broadbent (2023) found people
  with a preference mostly chose OpenDyslexic for its looks, with no difference
  in scores.
- Spacing has better support. Marinus et al. (Dyslexia, 2016): the benefit of
  the Dyslexie font came from its spacing, not its letter shapes. Zorzi et al.
  (PNAS, 2012): wider letter gaps helped children with dyslexia on running text.
  The Zorzi figures came from a news summary, so check them against the paper
  before quoting numbers.
- Both spacing studies used running text, not one-word RSVP flashes. Whether it
  helps in this reader is untested.

## Implementation history

1. DONE. OpenDyslexic files added, Windows probe run.
2. DONE. core/letter_spacing.py and tests/test_letter_spacing.py (78 tests).
3. DONE. Settings: dyslexia_font_enabled and letter_spacing_level, with
   tests/test_settings_store_dyslexia.py (24 tests).
4. DONE. core/font_choice.py and tests; theme.py uses it.
5. DONE. Reader: gap measuring, plan, space_chunk in drawing and measuring,
   canvas.set_letter_spacing(), detached and preview windows.
6. DONE. Appearance tab controls, app.py wiring, the letter_spacing_level
   profile key, GUI smoke tests.
7. DONE. Docs (commits fcc4323 and cc5bbc9), licences and README (278db22).
8. DONE. Bug fix (cd75c47): see below.
9. DONE. Version bump and release: 9403e35 (3.5.1, superseded), then d8c279c
   (3.6.0), tagged and released 19.10.2026. Suite: 1294 passed on the user's
   machine.

## Bug found and fixed on the way (cd75c47)

SettingsStore._load did AppSettings(**data), and storage.parse_data did
Transcript(**t). Any key the dataclass did not know raised TypeError, which was
caught and treated as "use the defaults" or "no valid save". The next save then
overwrote the real file, so opening a file written by a newer version (or with
a stray key) wiped settings or transcripts. docs/data.md already said unknown
fields are ignored.

Fix: unknown keys are filtered out, following the existing _BOOKMARK_FIELDS
pattern (_TRANSCRIPT_FIELDS in core/storage.py, _known_settings() in
core/settings_store.py, also used by replace_from_bundle so a bundle import is
not left half done). A settings.json that is valid JSON but not an object no
longer crashes startup. 14 new tests, 12 of which fail on the old code.

Trade-off: unknown keys are dropped, not preserved. A downgrade followed by an
upgrade loses the settings only the newer version knew, but nothing else.

## Loose ends (the user's call)

- A damaged (not just unknown-key) data.json is still treated as "no save" and
  the next save overwrites it. A safer version would back the file up first.
- A few comments still say "Dyslexia-friendly font" where the UI label is "Use
  the OpenDyslexic font": core/profiles.py:21, core/font_choice.py:4,
  gui/theme.py:146, gui/app.py:827, tests/test_font_choice.py:3.

## Out of scope

Line spacing, a continuous spacing slider, a font picker with several fonts,
live font switching without a restart, spacing in the edit box, applying the
font switch from a profile, and any claim that the feature helps people with
dyslexia.
