# Installation

Requires Python 3.10 or newer.

```bash
git clone https://github.com/QuiteNew/rsvp-desktop-reader.git
cd rsvp-desktop-reader
```

## Windows

```bash
python -m venv venv
venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## macOS

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

## Linux

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

## Verify it worked

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