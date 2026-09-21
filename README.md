# Rapid Serial Visualization Presentation Desktop Reader

A lightweight, fully offline speed-reading app that flashes transcript text
one word at a time - eliminating eye movement so you can read faster without
losing comprehension.


## About

RSVP Desktop Reader takes raw video transcripts, strips out timestamps, and
flashes them word by word in a fixed spot on screen, with each word's
**Optimal Recognition Point** highlighted - the exact letter your eye
naturally lands on to recognize a word in the fastest time. Instead of your eyes
scanning back and forth across a page, the words come to you.

I built this because I found [this](https://www.instagram.com/reel/DTf6Bh9jSNn/?stkn=ZWdpeHJlb2o1bGp6) reel on instagram 
and I immediately wanted to recreate it, not using an extension or a web tool, 
I wanted something local, lightweight, and fully
mine, created in a way that I wanted it to look and function

I built this slowly, in small sessions where I could also apply my knowledge of Python that I got from uni, also learn 
and use libraries such as [CustomTkinter](https://customtkinter.tomschimansky.com/)

Every piece - the reading engine, the GUI, persistence, the
whole layout system - was built one small, testable step at a time, with a
real architecture underneath it: a clean split between the pure reading
logic in `core/` and everything GUI-related in `gui/`, so the two never
depend on each other.

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
- Skip forward/backward by a configurable word count, with an optional
  auto-pause when you skip
- Pause, resume, restart, and stop (return to draft) controls
- Detach any transcript into its own standalone floating window
- Organize transcripts into **Spaces** - browser-tab-style categories you
  can create and switch between
- Full transcript management: create, edit drafts, delete (with a
  confirmation step)
- Everything persists automatically - reading position, pause state, and
  in-progress drafts are saved without needing to click anything
- Deep customization: per-transcript font, highlight, and background
  colors; adjustable sidebar width and control-band height, including live
  drag-to-resize; a relocatable folder for where your data is stored
- Light / Dark / System theme support, with reading colors that
  automatically follow the active theme unless you've customized them
- Fully offline and self-contained - no browser, offline,
  custom fonts bundled directly into the project

## The RSVP Technique

**RSVP (Rapid Serial Visual Presentation)** is a reading method where text
is shown one word at a time in a single fixed location, instead of being
laid out across a page. Normal reading requires your eyes to physically
jump from word to word (these jumps are called saccades) and often
backtrack - RSVP removes that entirely, since the words come to a
stationary point instead of your eyes having to find them.

The **Optimal Recognition Point (ORP)** is the specific letter within a
word where your eye naturally focuses to recognize it fastest - usually
just left of center, and shifting slightly depending on the word's length.
This app calculates that letter for every word and bolds it in a distinct
color, keeping it aligned in the exact same screen position from word to
word, so your eye never has to search for where to look next.

## Installation

Requires Python 3.10 or newer.

```bash
git clone <your-repo-url>
cd rsvp-desktop-reader
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS

Homebrew's Python doesn't bundle `tkinter` - it needs the separate `python-tk`
formula, installed alongside Python itself:

```bash
brew install python@3.13 python-tk@3.13

/opt/homebrew/bin/python3.13 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Creating the virtual environment with the full interpreter path (rather than a
bare `python -m venv venv`) makes sure it's built from the Python you just
installed `tkinter` for, even if you have more than one Python on your Mac.

### Linux

Most distributions split Tkinter out of the base Python package too, so it
needs installing separately, before creating the virtual environment:

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

```bash
python3 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Verify it worked

```bash
python -c "import tkinter; print('Tk:', tkinter.TkVersion)"
python -c "import customtkinter; print('CustomTkinter:', customtkinter.__version__)"
```

Both commands should print a version number with no errors. If the second one
fails, check that `pip` and `python` point at the same interpreter -
`python -m pip install ...` (rather than a bare `pip install ...`) keeps them
in sync.

The two fonts the app uses (Fredoka and Quicksand) are already bundled in
`assets/fonts/` and committed to this repo, so there's nothing extra to
download - they're registered automatically, just for this app, when it
launches.

Then run it:

```bash
python main.py
```


Creating the virtual environment with the full interpreter path (rather than a
bare `python -m venv venv`) makes sure it's built from the Python you just
installed `tkinter` for, even if you have more than one Python on your Mac.

### Verify it worked

```bash
python -c "import tkinter; print('Tk:', tkinter.TkVersion)"
python -c "import customtkinter; print('CustomTkinter:', customtkinter.__version__)"
```

Both commands should print a version number with no errors. If the second one
fails, check that `pip` and `python` point at the same interpreter -
`python -m pip install ...` (rather than a bare `pip install ...`) keeps them
in sync.

The two fonts the app uses (Fredoka and Quicksand) are already bundled in
`assets/fonts/` and committed to this repo, so there's nothing extra to
download - they're registered automatically, just for this app, when it
launches.

Then run it:

```bash
python main.py
```

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
   sizing, where your data is stored, and theme.

## Project Structure

````
rsvp-desktop-reader/
├── assets/
│ └── fonts/ # Bundled Fredoka & Quicksand font files
├── core/ # Pure reading engine — no GUI dependencies
│ ├── models.py # The Transcript data model
│ ├── parser.py # Strips timestamps from raw transcript text
│ ├── tokenizer.py # Splits cleaned text into words
│ ├── orp.py # Calculates each word's Optimal Recognition Point
│ ├── timing.py # Converts WPM into a per-word delay
│ ├── reader.py # ReaderSession — ties the above together
│ ├── transcript_store.py # In-memory store + persistence for transcripts/spaces
│ ├── settings_store.py # In-memory store + persistence for app settings
│ ├── storage.py # Low-level JSON read/write
│ └── data_bundle.py # Cross-machine export/import: builds and applies a full-app data bundle
├── gui/
│ ├── app.py # Main application window
│ ├── theme.py # Central design tokens: colors, fonts, theme resolution
│ ├── icons.py # Hand-drawn icons (avoids font-glyph rendering issues)
│ └── components/ # Every individual UI piece — header, canvas, dialogs, etc.
├── tests/ # Automated test suite covering core engine modules
│ ├── test_orp.py
│ ├── test_parser.py
│ ├── test_reader.py
│ ├── test_settings_store.py
│ ├── test_timing.py
│ ├── test_tokenizer.py
│ └── test_transcript_store.py
├── main.py # Entry point
└── requirements.txt
````

## Built With

- [Python](https://www.python.org/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - the GUI framework
- [Pillow](https://python-pillow.org/) - used to hand-draw a couple of icons
- [Fredoka](https://fonts.google.com/specimen/Fredoka) &
  [Quicksand](https://fonts.google.com/specimen/Quicksand) - bundled fonts,
  both released under the SIL Open Font License

## Settings and Configuration

Settings are organized into four tabs:

- **Defaults** - speed, colors, and skip behavior applied to newly created
  transcripts (skip settings apply live to whatever you're currently
  reading too)
- **Layout** - window size, sidebar width, bottom control-band height, and
  a free-form drag-to-resize toggle
- **Storage** - where your transcript data is saved on disk, changeable at
  any time; also where you can export everything (transcripts, spaces, and
  settings) to a file, or import one from another machine, choosing whether
  to replace what's here or add to it
- **Appearance** - Light / Dark / System theme (takes effect on next
  launch, not live)

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
- Improvements to reading engine depth
- Data insertion beyond copy pasting 
- Session stats
- Quality of life polish


## License

*Not yet chosen*

## Acknowledgments

- [Fredoka](https://fonts.google.com/specimen/Fredoka) and
  [Quicksand](https://fonts.google.com/specimen/Quicksand), by their
  respective creators, licensed under the
  [SIL Open Font License](https://openfontlicense.org/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) by Tom
  Schimansky
