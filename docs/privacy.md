# Privacy policy

*Last updated: 26 November 2026*

This page explains what RSVP Desktop Reader does with your information. It
covers the app on Windows, macOS and Linux, however you got it, and it also
says what happens when you visit this website.

## The short version

- The app doesn't collect, send, share or sell any information about you. It
  has no accounts, no ads, no analytics and no crash reporting of its own.
- Everything you put into it is saved in a few plain files on your own
  computer, where you can open, copy or delete it whenever you like.
- It never connects to the internet by itself. The only time anything opens
  online is when you click one of the two links in its About dialog, and then
  it's your web browser that opens the page.
- I never see your transcripts, your settings or how you use the app.

## Who makes the app

RSVP Desktop Reader (shown inside the app as RSVP Reader) is an open source
app made by one developer, QuiteNew. All of its code is public at
[github.com/QuiteNew/rsvp-desktop-reader](https://github.com/QuiteNew/rsvp-desktop-reader),
so anyone can check what this page says against what the app really does.

## What the app saves on your computer

The app saves your work so it's still there the next time you open it. It
keeps it in two files, written as plain JSON text:

| File | Where it is | What's in it |
| --- | --- | --- |
| `data.json` | Your data folder, which is `.rsvp_reader` in your user folder unless you pick another one | Your transcripts and their drafts, your Spaces, your bookmarks, where you stopped reading, each transcript's speed, colours and other reading choices, and your reading totals (how many times you read each transcript, how many words, and for how long) |
| `settings.json` | Always `.rsvp_reader` in your user folder | Your settings and reading profiles, the window's size and place on the screen, which transcript was open last, and where your data folder is |

On Windows, `.rsvp_reader` is `C:\Users\<you>\.rsvp_reader`. On macOS and
Linux it's `~/.rsvp_reader`. Where your data folder is gets saved as a path on
your computer, so it can include your user name. It's the one setting an
export leaves out, because it would be wrong on another computer anyway. Every
field in both files is listed on the [Data and export format](data.md) page.

The app writes a few other files, all on your computer too:

- **Copies of damaged files.** If a save file can't be read when the app
  starts, the app keeps a copy of it next to the original, with a name like
  `data.damaged-20261029-153012.json`, before it saves anything over it. These
  copies stay until you delete them.
- **Chime sounds.** When speaker cues play a sound on Windows, the app makes
  short sound files of musical notes in your system's temporary folder, and
  removes them when it closes. They hold only the notes, nothing from your
  transcripts.
- **Exports.** **Export Data** writes one file, wherever you choose, holding
  your transcripts, Spaces, settings and profiles. Anyone who has that file can
  read your transcripts, so look after it as you would the transcripts
  themselves.

## What the app reads

- **Files you add.** When you add a transcript from a file, the app reads the
  text out of that one file and copies it into `data.json`. It suggests the
  file's name as the title. It doesn't change the file and doesn't remember
  where it was.
- **Exports you import.** **Import Data** reads the export file you pick and,
  as you choose, adds its contents to what's already there or replaces it.
- **Your clipboard.** The app only uses the clipboard when you copy or paste.
  What you copy is then handled by your operating system, as it is for any
  other app. On Windows that includes clipboard history and syncing, if you
  have them turned on.

Beyond that, it only reads its own files and the few things it needs from your
system to run, such as whether your system is set to light or dark mode.

## What leaves your computer

Nothing, on its own. The app has no accounts, no telemetry, no ads, no
analytics and no update checks, and it works fully with the internet turned
off.

The one exception is the About dialog, behind the small round **i** button in
Settings. It has two links: one to the project on GitHub and one to this page.
Clicking either opens it in your web browser. From then on it's an ordinary
visit to a website, covered by that website's own privacy policy.

## If you get the app from somewhere else

- **From the Microsoft Store.** Microsoft handles the download, installation
  and updates, under the
  [Microsoft Privacy Statement](https://privacy.microsoft.com/privacystatement).
  As with any app on the Store, Microsoft gives me reports in its developer
  dashboard, such as how many people installed the app and how often it
  crashed or stopped responding. Those reports come from the Store and from
  Windows' own diagnostic data, which follows your Windows diagnostic data
  settings. The app doesn't add anything to them. Ratings and reviews you post
  on the Store are public, so I can read and answer them like anyone else. I
  use all of this only to find and fix problems.
- **From GitHub.** Downloads from the project's Releases page are handled by
  GitHub, under the
  [GitHub Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).

## This website

This page and the rest of the documentation are hosted on GitHub Pages. GitHub
logs visitors' IP addresses for security, under the GitHub Privacy Statement.
When a page opens, your browser also loads the site's fonts from Google Fonts,
under [Google's Privacy Policy](https://policies.google.com/privacy), and asks
GitHub for the project's star and fork counts. Your browser remembers whether
you picked the light or dark look for the site. The site sets no cookies and
has no ads or analytics.

## How your information is protected

Your files never leave your computer, so what protects them is your computer:
the sign-in on your user account, and drive encryption such as BitLocker on
Windows or FileVault on macOS, if you use it. The app doesn't encrypt the files
itself. They're plain text on purpose, so you can read them, back them up and
fix them. That also means anyone who can sign in as you, or who gets a copy of
the files, can read them.

## Your choices

Because everything is on your computer, you're in charge of all of it:

- **See it.** Open `data.json` and `settings.json` in any text editor. Close
  the app first if you want to change anything in them, because it saves over
  them while it's open.
- **Take it with you.** Use **Export Data** in Settings, under Storage, and
  **Import Data** on the other computer.
- **Move it.** Use **Choose folder** in Settings, under Storage. From then on
  the app saves `data.json` in the new folder. The copy in the old folder is
  left where it was, so delete it yourself if you don't want it.
- **Delete some of it.** Delete a transcript, a bookmark or an empty Space in
  the app.
- **Delete all of it.** Close the app, then delete the `.rsvp_reader` folder,
  your data folder if you moved it, any copies of damaged files and any exports
  you made. Deleting or uninstalling the app isn't guaranteed to remove these
  files, so delete them yourself to be sure they're gone.

I don't hold any of your information, so there's nothing for me to look up,
hand over or delete on your behalf. You're still welcome to ask me anything
about it.

## Children

The app doesn't collect information from anyone, so it doesn't collect any from
children either. It has no chat, sharing or social features.

## Changes to this page

If the app ever changes what it does with your information, this page will be
updated in the same release, with a new date at the top. Every earlier version
of this page is kept in the
[project's public history](https://github.com/QuiteNew/rsvp-desktop-reader/commits/main/docs/privacy.md).

## Questions

If something here isn't clear, or you think the app does something this page
doesn't mention, open an issue at
[github.com/QuiteNew/rsvp-desktop-reader/issues](https://github.com/QuiteNew/rsvp-desktop-reader/issues).
Issues are public, so please don't put anything private in one.
