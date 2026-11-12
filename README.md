# Rapid Serial Visualization Presentation Desktop Reader

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-6.0.0-2B2B2B?style=for-the-badge)
![Pillow](https://img.shields.io/badge/Pillow-11557C?style=for-the-badge)
![pypdf](https://img.shields.io/badge/pypdf-A50E0E?style=for-the-badge)
![cryptography](https://img.shields.io/badge/cryptography-5C3D8C?style=for-the-badge)
![lxml](https://img.shields.io/badge/lxml-2E6DB4?style=for-the-badge)
![python-docx](https://img.shields.io/badge/python--docx-2B579A?style=for-the-badge)
![darkdetect](https://img.shields.io/badge/darkdetect-222222?style=for-the-badge)
![Platforms](https://img.shields.io/badge/Windows%20%7C%20macOS%20%7C%20Linux-4C4C4C?style=for-the-badge)
![Offline](https://img.shields.io/badge/100%25%20offline-2E7D32?style=for-the-badge)
<br>
  [![Build & Release](https://github.com/QuiteNew/rsvp-desktop-reader/actions/workflows/build-release.yml/badge.svg)](https://github.com/QuiteNew/rsvp-desktop-reader/actions/workflows/build-release.yml)
  [![Docs](https://github.com/QuiteNew/rsvp-desktop-reader/actions/workflows/docs.yml/badge.svg)](https://github.com/QuiteNew/rsvp-desktop-reader/actions/workflows/docs.yml)
  [![Tests](https://github.com/QuiteNew/rsvp-desktop-reader/actions/workflows/tests.yml/badge.svg)](https://github.com/QuiteNew/rsvp-desktop-reader/actions/workflows/tests.yml)

A lightweight, fully offline speed-reading app that flashes transcript text
one word at a time - eliminating eye movement so you can read faster without
losing comprehension.

**Documentation:** https://quitenew.github.io/rsvp-desktop-reader/


## About

RSVP Desktop Reader takes raw video transcripts, strips out timestamps, and  flashes them word by word in a fixed spot 
on screen, with each word's **Optimal Recognition Point** highlighted, the exact letter your eye  naturally lands on to recognize a word in the 
fastest time. Instead of your eyes  scanning back and forth across a page, the words come to you.
I built this because I found [this](https://www.instagram.com/reel/DTf6Bh9jSNn/?stkn=ZWdpeHJlb2o1bGp6) reel on instagram 
and I immediately wanted to recreate it, not using an extension or a web tool, I wanted something local, lightweight, and fully  mine, created in a way that I wanted it to look and function.

I built this slowly, in small sessions where I could also apply my knowledge of Python that I got from uni, also learn 
and use libraries such as [CustomTkinter](https://customtkinter.tomschimansky.com/)

Every piece (the reading engine, the GUI, persistence, the  whole layout system) was built one small, testable step at a time, 
with a real architecture underneath it: a clean split between the pure reading  logic in `core/` and 
everything GUI-related in `gui/`, so the two never depend on each other.
<br>

For the background, the eye-movement physiology, the Optimal Viewing Position  research behind the highlighted letter, and what the studies actually say about
reading this way (including where it helps and where it does not), see [The science behind RSVP](docs/technique.md)


## Contents

- [Features](#features)
- [The RSVP Technique](#the-rsvp-technique)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Built With](#built-with)
- [Settings and Configuration](#settings-and-configuration)
- [Roadmap](#roadmap)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Features

- Word-by-word RSVP display with real Optimal Recognition Point highlighting
- Adjustable reading speed (words per minute)
- Optional multi-word chunking: flash a few words at once instead of one at a
  time, sized by a fixed words-per-group count or an adaptive character width,
  set per transcript
- Auto-fit for wide flashes: the words shrink to fit the window (never below
  60% of your Word size, and the saved size is never changed), with a horizontal
  scrollbar, a centre button, and a `C` shortcut for anything still too wide
- Skip forward/backward by a configurable word count, with an optional
  auto-pause when you skip
- Pause, resume, restart, and stop (return to draft) controls
- Detach any transcript into its own standalone floating window
- Organize transcripts into **Spaces**, browser-tab-style categories you
  can create and switch between
- Full transcript management: create, edit drafts, delete (with a
  confirmation step)
- Everything persists automatically: reading position, pause state, and
  in-progress drafts are saved without needing to click anything
- Deep customization: per-transcript font, highlight, and background
  colors; adjustable sidebar width and control-band height, including live
  drag-to-resize; a relocatable folder for where your data is stored
- Searchable settings: the Defaults tab has a live search that filters by a
  setting's name or, when you turn on the toggle beside it, its description
- An About dialog behind the small round **i** button at the top right of
  Settings, showing the app's version, its license, and a link to the project
- Reading profiles: save how the reader feels (guide marks, pacing, rewind on
  resume, surrounding words, skipping, the +/- step, the scrubber and paragraph
  switches, the letter spacing, and the Speed and Word size defaults) under a
  name, and switch between them from Settings in one click. Applying a profile
  never touches your transcripts, your colours or your chunking
- Optional letter spacing (Off, Small, Medium or Large) for the flashing word,
  and an OpenDyslexic font switch for the whole app. Both are comfort settings
  you can try by eye, not a treatment, and the app does not claim they help
- Optional bold word starts in the edit box: one button next to Normalize
  bolds the beginning of every word, and Ctrl+C (or right-click, **Copy with
  bold**) carries the bold into Word. It is a look you can try by eye, it is
  remembered between launches, and the app does not claim it helps
- Optional speaker cues for transcripts that mark who is talking ("Interviewer:",
  "Speaker 2:"): the reader shows the speaker's name, flashes briefly and can play
  a soft chime when the speaker changes, and holds a little longer before a new
  speaker starts. A **Configure speaker cues** window picks which cues you get, the
  chime's style and where the name sits (above the word or in the top right
  corner), and lets you review, rename or merge each transcript's speakers. It is
  off by default, and with it off reading is exactly as it was. The chime is
  Windows only for now
- Light / Dark / System theme support with reading colors that
  automatically follow the active theme unless you've customized them
- Picks up where you left off: the last transcript reopens at launch, paused
  at the same word (a Settings switch, on by default), the window comes back at
  its size and place, maximized if it was, and the sidebar keeps the sort order
  you picked
- Keyboard friendly: Up and Down change the speed by 10 WPM, and Esc and Enter
  work in the popups and in Settings
- The transcript you are reading is marked in the sidebar
- A save file that can't be read is copied aside before anything is saved over
  it, and the app tells you at launch
- Fully offline and self-contained: no browser or internet needed, and the
  fonts it uses are bundled with the project

## The RSVP Technique

**RSVP (Rapid Serial Visual Presentation)** is a reading method where text
is shown one word at a time in a single fixed location, instead of being
laid out across a page. Normal reading requires your eyes to physically
jump from word to word (these jumps are called saccades) and often
backtrack. RSVP removes that entirely, since the words come to a
stationary point instead of your eyes having to find them.

The **Optimal Recognition Point (ORP)** is the specific letter within a
word where your eye naturally focuses to recognize it fastest, usually
just left of center, and shifting slightly depending on the word's length.
This app calculates that letter for every word and bolds it in a distinct
color, keeping it aligned in the exact same screen position from word to
word, so your eye never has to search for where to look next.

## Installation

Please install the app from the releases section, if you want the full manual setup instructions for Windows, macOS, and Linux, 
including the per-platform Tkinter look at [docs/installation.md](docs/installation.md) or at the project documentation.


## Usage

1. Click **+** in the sidebar to create a new transcript - give it a title
   and choose which Space it belongs to.
2. Click the transcript to open it, paste in your raw transcript text, and
   click **Start reading**.
3. Use the playback controls above the reading canvas to pause, restart,
   skip, detach into a separate window, or enter focus mode (hides
   everything but the flashing words).
4. Adjust speed and colors for the current transcript from the control
   band at the bottom of the window.
5. Open **Settings** (top-right) for new-transcript defaults, layout
   sizing, where your data is stored, theme, font and letter spacing, and
   saved reading profiles.
<br>

For the full walkthrough, including keyboard shortcuts, see [docs/usage.md](docs/usage.md).


## Project Structure

````
rsvp-desktop-reader/
├── .github/workflows/       # GitHub Actions: tests, build & release, docs site
├── assets/
│   ├── fonts/               # Bundled Fredoka, Quicksand & OpenDyslexic font files, with their licenses
│   └── icons/               # Custom made icon
├── core/                    # Pure reading engine, no GUI dependencies
│   ├── models.py            # The Transcript data model
│   ├── importers.py         # Turns a picked file (.txt/.srt/.docx/.pdf) into plain transcript text
│   ├── parser.py            # Strips timestamps from raw transcript text
│   ├── normalizer.py        # Normalizes transcript text and can split long walls of text into paragraphs
│   ├── tokenizer.py         # Splits cleaned text into words
│   ├── punctuation.py       # Splits punctuation off each word and classifies the pause that follows it
│   ├── orp.py               # Calculates each word's Optimal Recognition Point
│   ├── colors.py            # Color helpers (hex parsing, blending one color toward another)
│   ├── timing.py            # Converts WPM into a per-word delay
│   ├── reader.py            # ReaderSession: ties the above together
│   ├── scroll.py            # Pure geometry for the reader's horizontal pan
│   ├── letter_spacing.py    # Letter spacing levels and the thin-space plan that builds each gap
│   ├── font_choice.py       # Which fonts the app uses (standard or OpenDyslexic) and the notes for the font switch
│   ├── bold_starts.py       # Which letters at the start of each word are bold in the edit box
│   ├── bold_spans.py        # Turns those letters into Tk text positions, and keeps very long lines plain
│   ├── rich_copy.py         # Builds the clipboard HTML and plain text for copying the selection with its bold
│   ├── speakers.py          # Finds who is speaking in a labelled transcript, and which speakers a transcript is read with
│   ├── chime.py             # Builds the speaker cue chime (four styles, a pattern of notes per speaker) as WAV bytes
│   ├── settings_search.py   # Pure matching for the Settings search (name, keywords, description)
│   ├── profiles.py          # Reading profiles: which settings a profile holds, name rules, loading saved ones
│   ├── profile_apply.py     # Works out what applying a profile does (clamping, guide mark colour vs. theme)
│   ├── app_info.py          # The app's name, version, license and project link, shown in the About dialog
│   ├── text_fit.py          # Shortens a line of text with an ellipsis to fit a width (the header's title)
│   ├── reopen.py            # Which transcript to open again at launch
│   ├── window_placement.py  # Where the main window goes at launch: size, position, maximized
│   ├── transcript_sort.py   # The sidebar's sort orders and the ids they are saved under
│   ├── wpm_step.py          # The Up and Down keys' 10 WPM step
│   ├── transcript_store.py  # In-memory store + persistence for transcripts/spaces
│   ├── settings_store.py    # In-memory store + persistence for app settings
│   ├── storage.py           # Low-level JSON read/write
│   └── data_bundle.py       # Cross-machine export/import: builds and applies a full-app data bundle
├── gui/
│   ├── app.py               # Main application window
│   ├── theme.py             # Central design tokens: colors, fonts, theme resolution
│   ├── icons.py             # Hand-drawn icons (avoids font-glyph rendering issues)
│   ├── rich_clipboard.py    # Puts text and its bold on the Windows clipboard together, so Word keeps the bold
│   ├── chime_player.py      # Plays the speaker cue chimes on Windows, from files it makes in the background
│   └── components/          # Every individual UI piece: header, canvas, dialogs, etc.
├── tests/                   # Automated test suite: the core engine, and the GUI through its real windows
│   ├── conftest.py          # Shared fixtures: a real app with its data in a temp folder, a Tk root, scaling
│   ├── tk_helpers.py        # Shared helpers for driving Tk: settle, real clicks, finding widgets
│   ├── edit_box_helpers.py  # Shared helpers for the edit box tests: the clipboard and Tk's real main loop
│   ├── test_adding_a_transcript.py
│   ├── test_app_info.py
│   ├── test_bold_family.py
│   ├── test_bold_spans.py
│   ├── test_bold_starts.py
│   ├── test_bold_starts_app.py
│   ├── test_bold_starts_wiring.py
│   ├── test_bookmarks_list.py
│   ├── test_center_over_parent.py
│   ├── test_chime.py
│   ├── test_chime_player.py
│   ├── test_chunking.py
│   ├── test_colors.py
│   ├── test_context_ribbon.py
│   ├── test_damaged_files.py
│   ├── test_data_bundle.py
│   ├── test_default_window_widths.py
│   ├── test_deleting_an_open_transcript.py
│   ├── test_detach_selection.py
│   ├── test_detach_selection_chunking.py
│   ├── test_detached_routing.py
│   ├── test_detached_window_controls.py
│   ├── test_dialog_keys.py
│   ├── test_edge_cases.py
│   ├── test_export_import_in_app.py
│   ├── test_font_choice.py
│   ├── test_footer_follows_the_chunking_window.py
│   ├── test_footer_size_and_colours.py
│   ├── test_gui_smoke.py
│   ├── test_header.py
│   ├── test_icons.py
│   ├── test_importer_errors.py
│   ├── test_importers.py
│   ├── test_keeping_unsaved_edits.py
│   ├── test_letter_spacing.py
│   ├── test_main_window_controls.py
│   ├── test_models.py
│   ├── test_normalize_in_app.py
│   ├── test_normalizer.py
│   ├── test_orp.py
│   ├── test_parser.py
│   ├── test_profile_apply.py
│   ├── test_profiles.py
│   ├── test_punctuation.py
│   ├── test_reader.py
│   ├── test_reader_display_speaker_cues.py
│   ├── test_reader_letter_spacing.py
│   ├── test_reader_speaker_cues.py
│   ├── test_reading_colours_follow_theme.py
│   ├── test_reopen_last_transcript.py
│   ├── test_rich_clipboard.py
│   ├── test_rich_copy.py
│   ├── test_scroll.py
│   ├── test_seeking.py
│   ├── test_seeking_in_the_windows.py
│   ├── test_selection_preview.py
│   ├── test_separator_line.py
│   ├── test_settings_apply.py
│   ├── test_settings_pickers_and_resets.py
│   ├── test_settings_search.py
│   ├── test_settings_store.py
│   ├── test_settings_store_bold_starts.py
│   ├── test_settings_store_dyslexia.py
│   ├── test_settings_store_profiles.py
│   ├── test_settings_store_speaker_cues.py
│   ├── test_sidebar_rows.py
│   ├── test_skip_and_resume.py
│   ├── test_space_and_move_guards.py
│   ├── test_spaces_and_deleting.py
│   ├── test_speaker_cues_settings_in_app.py
│   ├── test_speaker_cues_window.py
│   ├── test_speaker_cues_wiring.py
│   ├── test_speaker_rows.py
│   ├── test_speakers.py
│   ├── test_start_reading.py
│   ├── test_storage.py
│   ├── test_suite_isolation.py
│   ├── test_text_fit.py
│   ├── test_theme_following_colours.py
│   ├── test_theme_fonts.py
│   ├── test_timing.py
│   ├── test_tokenizer.py
│   ├── test_transcript_input_bold_live.py
│   ├── test_transcript_input_bold_starts.py
│   ├── test_transcript_input_edit_forwarder.py
│   ├── test_transcript_input_rich_copy.py
│   ├── test_transcript_list_current.py
│   ├── test_transcript_sort.py
│   ├── test_transcript_speaker_list.py
│   ├── test_transcript_store.py
│   ├── test_whole_transcript_speakers.py
│   ├── test_window_esc.py
│   ├── test_window_placement.py
│   ├── test_wpm_keys.py
│   └── test_wrapping_label.py
├── main.py                  # Entry point
├── RELEASING.md             # How a release is made, step by step
└── requirements.txt         # Python dependencies
````
<br>

For how these pieces fit together, the reading pipeline, the stores, and the  strict split between the pure-logic `core/` 
and the CustomTkinter `gui/`, see [docs/architecture.md](docs/architecture.md) *or the project documentation*

## Built With

- [Python](https://www.python.org/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - the GUI framework
- [Pillow](https://python-pillow.org/) - used to hand-draw a couple of icons
- [pypdf](https://pypdf.readthedocs.io/), [python-docx](https://python-docx.readthedocs.io/) & [lxml](https://lxml.de/) - read PDF, Word and HTML files for import
- [cryptography](https://cryptography.io/) (with its helpers `cffi` and `pycparser`) - lets pypdf open PDFs that are encrypted only to block printing or editing
- [Fredoka](https://fonts.google.com/specimen/Fredoka), [Quicksand](https://fonts.google.com/specimen/Quicksand) & [OpenDyslexic](https://opendyslexic.org/) - bundled fonts

## Settings and Configuration

Settings are organized into six tabs:

- **Defaults** - the speed, colours and word size new transcripts start with,
  and the reader settings that apply to every transcript straight away: guide
  marks, pacing, skipping, the surrounding-words line, reopening the last
  transcript at launch, and more. Two buttons here open their own windows:
  **Configure chunking** and **Configure speaker cues**
- **Layout** - window size (also remembered, with its place on screen, when you
  close the app), sidebar width, bottom control-band height, and a free-form
  drag-to-resize toggle
- **Storage** - where your transcript data is saved on disk, changeable at
  any time. Also where you can export everything (transcripts, spaces, and
  settings) to a file, or import one from another machine, choosing whether
  to replace what's here or add to it
- **Appearance** - Light / Dark / System theme and the OpenDyslexic font
  switch (both take effect on next launch, not live), plus the letter spacing
  (applies as soon as you press Apply)
- **Profiles** - save the current reader settings under a name, then apply,
  update, rename or delete them later. A profile holds the guide marks,
  pacing, rewind on resume, surrounding words, skipping, the +/- step, the
  scrubber and paragraph switches, the letter spacing, and the Speed and Word
  size sliders. Applying one takes effect straight away, and never changes a
  transcript, your colours, chunking, speaker cues or font (Speed and Word size only set
  where new transcripts start). Profiles are saved with your settings, so
  Export and Import carry them along
- **Stats** - read-only reading totals for each transcript (how many times
  it's been read, words read, and time spent), updated when a session ends
  rather than while you're paused

The small round **i** button at the top right of the Settings window opens an
About dialog with the app's icon, name, version, license, and a link to the
project on GitHub.

## Roadmap

- ~~A real, finished Dark theme color palette (the underlying switching
  mechanism already exists and is fully functional)~~
- ~~An automated test suite under `tests/`~~
- ~~Configurable size for words shown~~
- ~~Highlited letter position customization~~
- ~~Fixed reading-point guide marks~~
- ~~Theme-aware color sync for reading panel~~
- ~~Improvements to core engine~~
- ~~Fixing installation guide for Mac and Linux~~
- ~~Packaging and distribution (.exe(Windows) and.tz(Linux))~~ *MacOS still not finished*
- ~~Creating a custom icon~~
- ~~Cross-machine continuity~~ 
- ~~Improvements to reading engine depth~~
- ~~Data insertion beyond copy pasting~~ 
- ~~Session stats~~
- ~~Quality of life polish~~
- ~~Keyboard shortcuts~~
- ~~Comment and ctk.label clean up~~
- ~~Transcript draft normalization~~
- ~~Selective running~~
- ~~Quality of life polish 2.0~~
- ~~Settings additions~~
- ~~Peripheral context line~~
- ~~Chunking (multi-word flash)~~
- ~~Progress scrubber/seek bar~~
- ~~Bookmarks~~
- ~~Estimated read time and live progress %~~
- ~~Additional data insertion formats~~
- ~~Upgrading the test suite~~
- ~~Numorous bug fixes~~
- ~~Documentation and README reformatting~~ 
- ~~Horizontal scrollbar in the reader display (reposition the flash left/right)~~
- ~~Search functionality in settings~~
- ~~App version info dialog~~
- ~~Automated tests and repo cleanup~~
- ~~Setting profiles~~
- ~~Dyslexia-friendly font and letter spacing~~
- ~~Bold word starts in the edit box, with copying the bold into Word~~
- ~~Upgrading the test suite 2.0~~
- ~~Speaker cues~~


## License

Released under the MIT License. See [LICENSE](LICENSE) for the full text.

The bundled Fredoka, Quicksand and OpenDyslexic fonts are each released under
the SIL Open Font License, not the MIT license. A copy of each font's license
sits next to the font files in [assets/fonts](assets/fonts), and the fonts are
credited under Acknowledgments. The MIT license covers the project's own code.

The bold word starts look is similar to the one sold as Bionic Reading, a
trademark of BRCG Casutt GmbH. This project is not affiliated with or endorsed by
them and does not use their software. The
[FAQ](docs/faq.md#is-this-the-same-as-bionic-reading) has more.

## Acknowledgments

- [Fredoka](https://fonts.google.com/specimen/Fredoka), by Milena Brandão and
  Ben Nathan (Hafontia), licensed under the
  [SIL Open Font License](https://openfontlicense.org/). See
  [OFL-Fredoka.txt](assets/fonts/OFL-Fredoka.txt)
- [Quicksand](https://fonts.google.com/specimen/Quicksand), by Andrew
  Paglinawan, licensed under the SIL Open Font License. See
  [OFL-Quicksand.txt](assets/fonts/OFL-Quicksand.txt)
- [OpenDyslexic](https://opendyslexic.org/), by Abbie Gonzalez, licensed under
  the SIL Open Font License. See
  [OFL-OpenDyslexic.txt](assets/fonts/OFL-OpenDyslexic.txt)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) by Tom Schimansky