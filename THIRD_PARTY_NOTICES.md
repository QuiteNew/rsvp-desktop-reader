# Third-party notices

RSVP Desktop Reader is released under the MIT License (see [LICENSE](LICENSE)).
It's built on other people's open source work, and this page lists what the
app includes, what each part is for, and the licence it's shared under.

Every licence text named here comes with the app itself, not just with this
repository. In the Windows and Linux downloads they sit next to the app's own
files: this page and `LICENSE` at the top of the `_internal` folder, and the
full licence texts in `_internal/licenses`, one folder per package. The
package texts are copied from the exact versions the build was made with, so
they always match what's inside.

## Python and what comes with it

| Component | What it's for | Licence | Full text |
| --- | --- | --- | --- |
| [Python](https://www.python.org/) | Runs the app | Python Software Foundation License | `licenses/python/LICENSE.txt` |

On Windows, Python's licence file also holds the terms for the parts it brings
with it, one after another: the Microsoft C runtime files, bzip2, libffi,
OpenSSL, and Tcl and Tk, which draw the app's windows. Three of them don't
carry their names. OpenSSL's is the Apache License 2.0 text that comes after
libffi's, and Tcl's and Tk's are the two texts from the University of
California at the end. Licences for the smaller pieces built into Python
itself are listed on the
[Python licence page](https://docs.python.org/3/license.html).

## Packages

| Component | What it's for | Licence | Full text |
| --- | --- | --- | --- |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | The app's buttons, sliders and windows | MIT | `licenses/customtkinter/` |
| [Roboto](https://fonts.google.com/specimen/Roboto), copyright 2011 Google Inc., which CustomTkinter brings with it | CustomTkinter's default font | Apache License 2.0 | `licenses/Roboto-Apache-2.0.txt` |
| [darkdetect](https://github.com/albertosottile/darkdetect) | Tells whether the system is set to light or dark mode | BSD 3-Clause | `licenses/darkdetect/` |
| [packaging](https://github.com/pypa/packaging) | Used by CustomTkinter to compare version numbers | Apache License 2.0, or BSD 2-Clause | `licenses/packaging/` |
| [Pillow](https://python-pillow.org/) | Draws the app's icons, along with the image libraries it's built with, which its licence file lists one by one | MIT-CMU | `licenses/pillow/` |
| [pypdf](https://github.com/py-pdf/pypdf) | Reads text from PDF files | BSD 3-Clause | `licenses/pypdf/` |
| [python-docx](https://github.com/python-openxml/python-docx) | Reads text from Word files | MIT | `licenses/python-docx/` |
| [lxml](https://lxml.de/) | Reads HTML files, and Word files through python-docx, along with the libraries it's built with, which its licence files list | BSD 3-Clause | `licenses/lxml/` |
| [typing_extensions](https://github.com/python/typing_extensions) | Used by python-docx | Python Software Foundation License | `licenses/typing_extensions/` |
| [cryptography](https://github.com/pyca/cryptography) | Lets pypdf open PDFs that are encrypted only to stop printing or editing | Apache License 2.0, or BSD 3-Clause | `licenses/cryptography/` |
| [cffi](https://github.com/python-cffi/cffi) | Used by cryptography to reach its compiled code | MIT | `licenses/cffi/` |

Where a package offers a choice of two licences, the app uses it under either
one, and both texts are included.

## Fonts

| Component | What it's for | Licence | Full text |
| --- | --- | --- | --- |
| [Fredoka](https://fonts.google.com/specimen/Fredoka) | Headings | SIL Open Font License 1.1 | `assets/fonts/OFL-Fredoka.txt` |
| [Quicksand](https://fonts.google.com/specimen/Quicksand) | Body text | SIL Open Font License 1.1 | `assets/fonts/OFL-Quicksand.txt` |
| [OpenDyslexic](https://opendyslexic.org/) | The optional OpenDyslexic font | SIL Open Font License 1.1 | `assets/fonts/OFL-OpenDyslexic.txt` |

## The Linux and macOS builds

The Linux and macOS builds also carry a few libraries copied from the machine
they were built on, such as the system's own Tcl and Tk and the libraries
those need, and on Linux, lxml includes GNU libiconv, which is under the GNU
Lesser General Public License 2.1. The notices for those aren't in the builds
yet, but everything listed above is.

## How the app is built

The downloadable builds are made with [PyInstaller](https://pyinstaller.org/).
The small program it adds to start the app is under the GNU General Public
License 2.0 or later, with an exception that lets it be shipped with any
program under any licence, so it places no conditions on the app.