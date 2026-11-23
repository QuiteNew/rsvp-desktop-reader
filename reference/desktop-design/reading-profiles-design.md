# Reading profiles - design

Status: SHIPPED as v3.5.0 (tagged and released 17.10.2026). Scope narrowed on
16.10.2026, then widened a little on 17.10.2026 (see "What changed"). The
dyslexia-friendly font and letter/word spacing work followed as v3.6.0 (see
claude/dyslexia-font-design.md) and added the letter spacing level to profiles.
The v3.5.0 release page was deleted by mistake on 19.10.2026 and restored; the
tag was never touched (see claude/release-notes-archive.md).

## Summary

Named reading profiles. A profile is a saved snapshot of the app-wide settings
that decide how the reader feels (guide marks, pacing, skip behaviour, resume
rewind, peripheral context, and a few switches and sliders from the Defaults
tab), so "Fast skim" and "Careful read" can be switched between in one go.
Applying a profile takes effect live, with no restart.

A profile only ever changes app settings. It never touches a transcript, the
colours, or the chunking defaults. Of the Defaults that new transcripts start
from it holds only Speed and Word size, and those only decide where the next
new transcript starts. Anything that should differ per piece of text is what
spaces are for, not profiles.

## What changed

### 16.10.2026

The first version of this design also had profiles change the open transcript
(speed, colours, font size, chunking) and the Defaults for new transcripts.
The user ruled that out: profiles are for settings only, no transcript changes,
no Defaults changes. That removed:

- the per-transcript keys (wpm, font_color, highlight_color, background_color,
  font_size, chunking_enabled, chunk_size, chunk_mode, chunk_char_target)
- the "open transcript" and "new-transcript defaults" layers
- the "no transcript open" case
- the colour trap for transcript colours (only the guide mark colour is left)

Found while checking the colour handling, kept here for the record: in Dark
mode new transcripts are seeded from the DARK_READING_* constants and ignore the
Defaults colours, and in Light mode "follows the theme" means "follows the
Defaults tab". Writing profile colours into Defaults would have made a
theme-following profile unable to restore the original colours.

### 17.10.2026

Found in real use: after switching profiles, the Speed and Word size sliders on
the Settings Defaults tab did not move, while the skip slider did. That was the
16.10 ruling doing what it said (both are default_* values), but it looked like
a bug from the Defaults tab. Decision, made with the user:

- Speed (default_wpm) and Word size (default_font_size) join profiles. They are
  the Defaults tab sliders only: the transcript that is open is not changed.
- font_size_step, split_long_paragraphs_enabled and scrub_pause_enabled join
  profiles too. They are plain app-wide settings with no theme trap.
- The colours stay out, for the reason recorded above. Chunking stays out: it
  is the default for new transcripts and has a window of its own.
- Profiles saved before this change simply lack the five new keys. A missing key
  means "leave that setting alone", so they keep working and do not move the
  new settings until they are updated.
- The explanation on the Profiles tab was reworded to say all of this.

Note for the same day: a hand-picked guide mark colour stored in a profile
(for example #3B2E27, the Light theme colour) is applied as picked even in Dark
mode. It is correct, but easy to create by saving a profile right after "Reset
to Original Defaults" while in Dark mode. Not changed.

## Decisions

- A: A profile holds the app-wide settings listed below, nothing else.
- B: Applying a profile changes the app-wide settings live, through the same
  setters and canvas methods the Settings Apply path already uses. No
  transcript is changed. Of the default_* values only default_wpm and
  default_font_size are written (the colours are passed through unchanged,
  because their setter takes all five together).
- C: Switching lives in a new Profiles tab in Settings, placed between
  Appearance and Stats. The tab carries a short paragraph explaining what a
  profile holds and does not change, and that spaces are the way to keep
  different transcripts apart. Settings' own Apply button is hidden on that
  tab, since saving, updating and applying a profile apply pending changes
  first. Clicking the selected profile again unselects it. A quick-switch
  dropdown in the main window is a possible later addition, not part of this
  release.
- D: No restart. Everything in a profile is already applied live. The
  appearance mode (Light/Dark/System) needs a restart and is not part of
  profiles.
- E: Profiles are user-made only, created with "Save current settings as
  profile". No starter profiles are shipped.
- F: A profile is a snapshot, not a live link. Applying copies its values in.
  Changing settings afterwards does not change the saved profile unless the
  user presses "Update".
- G: Names are unique (case-insensitive) and limited to 30 characters. Rename,
  update and delete are included. The list scrolls, no hard cap.

## What a profile holds

- highlight_offset_px
- guide_mark_horizontal_enabled, guide_mark_thickness_px,
  guide_mark_length_percent, guide_mark_color
- length_pacing_enabled, warm_up_enabled
- resume_rewind_enabled, resume_rewind_words
- peripheral_context_enabled
- skip_word_count, pause_on_skip
- default_wpm, default_font_size (the Defaults tab sliders, for new transcripts)
- font_size_step
- split_long_paragraphs_enabled, scrub_pause_enabled
- letter_spacing_level (added in v3.6.0; a profile saved before that lacks it,
  so applying one leaves spacing alone)

Not in a profile: window size, sidebar width, bottom band height, free-form
resize, data directory, appearance mode, the OpenDyslexic font switch (it needs
a restart), the three Defaults colours (default_font_color,
default_highlight_color, default_background_color), the chunking defaults
(default_chunking_enabled, default_chunk_size, default_chunk_mode,
default_chunk_char_target), and every per-transcript value.

## The guide mark colour and the theme

guide_mark_color has an "is still following the theme" flag
(guide_mark_color_is_default on AppSettings). If a profile stored a plain hex
value, applying it would mark the colour as picked by hand and it would stop
following Light/Dark. So a profile stores None for a guide mark colour that was
still following the theme when it was saved, and a hex value only for one
picked by hand. Applying None resolves to the current theme's guide mark colour
(LIGHT_/DARK_READING_GUIDE_MARK_COLOR in gui/theme.py) and keeps the flag on.
SettingsStore.restore_guide_mark_color(color, follows_theme) does the setting,
because set_guide_mark_color() only ever turns the flag off.

## Storage (done)

- AppSettings.profiles: list of {"name": str, "values": dict}, in
  settings.json, so Export/Import carries profiles automatically. An old
  settings.json without the field loads with no profiles. A bundle exported
  before profiles existed keeps this machine's profiles on a Replace import.
- Loading is forgiving: malformed entries are dropped, unknown or invalid keys
  inside a profile are ignored, and a key missing from a profile means "leave
  that setting alone" when applying. Values are clamped to the existing range
  constants (HIGHLIGHT_OFFSET_RANGE, GUIDE_MARK_*, RESUME_REWIND_WORDS_RANGE,
  SKIP_WORD_COUNT_RANGE, WPM_RANGE, FONT_SIZE_RANGE, FONT_SIZE_STEP_RANGE,
  and the letter spacing range) when applying.

## Where the snapshot comes from

All values come from the saved settings (SettingsStore). No transcript is
involved. "Update" uses the same source as "Save".

## Known risk to design around: stale Settings widgets

The Settings window copies every value into its widgets when it opens, and its
Apply writes the widget values back to the stores. If a profile is applied
while the window is open, the stores change underneath it, and a later Apply
would write the old widget values back over the profile.

Done: applying a profile closes the Settings window after applying, so the next
open reads the new values. "Save as profile" and "Update" capture what is on
screen, so they run the window's normal Apply first and then take the
snapshot.

## Implementation plan (core first, tests at each step, commit per step)

1. DONE. core/profiles.py (rules, names, loading) and the AppSettings.profiles
   field with the SettingsStore methods (add, update, rename, delete, list).
   Commits "Added the rules behind reading profiles" and "Store reading
   profiles in settings.json".
2. DONE. Store support for the guide mark colour flag
   (SettingsStore.guide_mark_color_is_default and restore_guide_mark_color).
3. DONE. Narrow core/profiles.py to the app-wide keys above and update its
   tests and the store tests.
4. DONE. A small pure module (core/profile_apply.py) that clamps a profile's
   values and resolves the guide mark colour against the current theme into a
   plan the app can carry out.
5. DONE. App wiring in gui/app.py: an apply-profile path that reuses the
   existing setters and live canvas methods.
6. DONE. The Profiles tab (between Appearance and Stats), as its own component
   so settings_window.py does not grow further, plus the name and confirm
   popups. Follow-up fix: click the selected profile again to unselect it, and
   hide Settings' own Apply button on that tab.
6b. DONE (17.10.2026). Speed, Word size, +/- step, split paragraphs and the
   scrubber switch join profiles (see "What changed").
7. DONE (17.10.2026). Docs (usage, FAQ, architecture, data, README features and
   roadmap), APP_VERSION 3.5.0 (commit 2c45c29), tagged v3.5.0 and released as
   "v3.5.0 - Reading profiles".

## Out of scope for this release

A quick-switch dropdown in the main window, starter profiles, profiles that
include the appearance mode, per-transcript settings in profiles, colours and
chunking in profiles, and profile-specific layout or window sizes.

## Side finding, not part of profiles

The Appearance tab note says a new transcript's reading colours "come from the
Defaults tab, not from this theme setting". That is out of date in Dark mode,
where new transcripts are seeded from the DARK_READING_* constants (see
_current_theme_reading_colors in gui/app.py). Worth fixing separately.
