# Microsoft Store listing

The text pasted into Partner Center for the English (United States) listing.
Each section below is one Partner Center field. The tests in
tests/test_store_listing.py read this file, so keep the headings as they are
and keep every field inside the limits noted next to it.

## Description

<!-- Limit 10,000 characters. Paragraphs are separated by a blank line. -->

RSVP Reader shows text one word at a time, always in the same spot on the screen, with one letter of each word marked in colour: the letter your eye naturally lands on. Your eyes stay still and the words come to you.

It was made for reading transcripts of videos, lectures, interviews and podcasts. Paste the text in, or open a .txt, .srt, .vtt, Markdown, HTML, Word or PDF file. Timestamps are stripped out, and you start reading at the speed you choose.

You stay in control of the pace. Pause, skip back or forward, drag the scrubber to any point, or set bookmarks. You can flash a few words at a time instead of one, slow down for long words and hold a little longer at the end of a sentence. When you come back, it opens the transcript you were reading, at the same word.

Make it look the way you like: your own colours and word size for each transcript, a light or dark theme, letter spacing, guide marks around the focus letter, and an OpenDyslexic font option. Save a reading setup as a profile and switch between them in one click.

Everything stays on your computer. The app never goes online by itself, and has no account, no ads and no tracking. Your transcripts are kept in plain files in your user folder, and you can export everything to move it to another computer.

A note on speed: reading this way makes a fast pace easy to set, but studies find that going well past your normal reading speed has diminishing returns. The app gives you the controls and leaves the pace to you.

RSVP Reader is free and open source, under the MIT licence.

## Product features

<!-- Up to 20 features, 200 characters each. -->

1. One word at a time in a fixed spot, with the focus letter marked in colour
2. Paste text in, or open .txt, .srt, .vtt, Markdown, HTML, Word and PDF files
3. Strips timestamps from video, lecture and podcast transcripts
4. Speed you set, and change while reading with the Up and Down keys
5. Flash a few words at a time instead of one
6. Pause, skip, scrub to any point and set bookmarks
7. Slows down for long words and holds longer at the end of a sentence
8. Picks up where you left off, at the same word
9. Speaker cues for interviews: shows who is talking and can chime when the speaker changes
10. Organise transcripts into Spaces
11. Detach a transcript into its own window, or hide everything but the words
12. Your own colours, word size, theme, guide marks and letter spacing
13. OpenDyslexic font option
14. Reading profiles that switch your whole setup in one click
15. Reading stats for each transcript
16. Export and import everything to move to another computer
17. Fully offline: no account, no ads, no tracking
18. Free and open source (MIT licence)

## Search terms

<!-- Up to 7 terms, 30 characters each. -->

- speed reading
- RSVP
- transcript reader
- one word at a time
- reading app
- subtitle reader
- focus reading

## Copyright and trademark info

<!-- Limit 200 characters. -->

© 2026 QuiteNew

## Links

- Privacy policy: https://quitenew.github.io/rsvp-desktop-reader/privacy/
- Website: https://quitenew.github.io/rsvp-desktop-reader/
- Support: https://github.com/QuiteNew/rsvp-desktop-reader/issues

## Category

Productivity

## What's new

<!-- Limit 1,500 characters. Left empty for the first release. -->

## Notes for certification

<!-- Limit 2,000 characters. Goes under Submission options. -->

No account or sign-in is needed, and the app makes no network connections. To try it: press the + button, give the transcript a title, paste any text, and press Start reading. Settings are under the gear icon at the top right.

## runFullTrust justification

<!-- Goes under Submission options, where Partner Center asks why the app needs the restricted capability. -->

RSVP Reader is a classic Win32 desktop app, written in Python with a Tkinter interface and packaged with PyInstaller. It uses the runFullTrust capability only to work normally: it opens files the user picks, saves its own data in %USERPROFILE%\.rsvp_reader, and plays short sounds. It makes no network connections.