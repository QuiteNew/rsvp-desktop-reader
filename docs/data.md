# Data and export format

RSVP Desktop Reader is fully offline. Everything it saves lives in a couple of
plain JSON files on your own machine, in a format that is easy to read, back up,
or move between computers. This page documents exactly what is stored, where,
and in what shape.

## Where your data lives

There are two files, and they do not necessarily live in the same place.

- **`data.json`** holds your transcripts and Spaces. It is written in your
  **data directory**, which defaults to `~/.rsvp_reader` and can be relocated
  from Settings, under Storage.
- **`settings.json`** holds the application settings. It always lives in the
  fixed location `~/.rsvp_reader`, regardless of where your data directory
  points. It has to, because one of the things it records is where the data
  directory is.

So if you move your data directory to, say, a synced folder, `data.json` moves
there while `settings.json` stays in `~/.rsvp_reader`.

On Windows that home folder is `C:\Users\<you>\.rsvp_reader`; on macOS and Linux
it is `~/.rsvp_reader`. Both files are UTF-8 JSON, indented for readability.

## The transcript file: `data.json`

The top-level shape is:

```json
{
  "next_id": 7,
  "current_space_index": 0,
  "spaces": ["General", "Work"],
  "transcripts": [ { "...": "one object per transcript" } ]
}
```

| Key | Meaning |
| --- | --- |
| `next_id` | The id the next new transcript will get. Ids are never reused. |
| `current_space_index` | Which entry in `spaces` is the currently selected Space. |
| `spaces` | The list of Space names. There is always at least one; the default is `"General"`. |
| `transcripts` | Every transcript, across all Spaces, each as the object below. |

### A transcript

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `id` | int | (assigned) | Unique identifier. |
| `title` | string | | The transcript's name. |
| `space` | string | | Which Space it belongs to. |
| `raw_text` | string | `""` | The committed text that gets read. |
| `wpm` | int | 300 | This transcript's reading speed. |
| `position` | int | 0 | The last word index you were at. |
| `font_color` | string | `#FFFFFF` | Word color. |
| `highlight_color` | string | `#E74C3C` | Highlighted-letter color. |
| `background_color` | string | `#1E1E1E` | Reading-canvas background. |
| `font_size` | int | 32 | Word size in pixels. |
| `chunking_enabled` | bool | false | Whether words are flashed in groups rather than one at a time. |
| `chunk_size` | int | 2 | Words per group in fixed mode (2 to 5). |
| `chunk_mode` | string | `fixed` | How a group's size is chosen: `fixed` (a word count) or `adaptive` (a character width). |
| `chunk_char_target` | int | 30 | Target group width in characters for adaptive mode (15 to 60), counting letters and the spaces between words. |
| `is_paused` | bool | false | Whether it was paused when last saved. |
| `draft_text` | string | `""` | Unsaved text sitting in the edit box. |
| `is_stopped` | bool | false | Whether the last session was stopped (so it reopens to the edit box). |
| `font_color_is_default` | bool | true | Whether the word color still follows the theme default or was picked by hand. |
| `highlight_color_is_default` | bool | true | Same, for the highlight color. |
| `background_color_is_default` | bool | true | Same, for the background color. |
| `times_read` | int | 0 | How many sessions with real reading time this transcript has had. |
| `total_words_read` | int | 0 | Words the reader auto-advanced through (skipping does not inflate it). |
| `total_time_spent_seconds` | int | 0 | Active reading time, excluding paused time. |
| `pre_normalize_text` | string | `""` | Undo data for the Normalize button: the text before normalizing. |
| `normalized_text` | string | `""` | Undo data: the text normalizing produced. |
| `bookmarks` | list | `[]` | Saved positions, each the object below. |

The color values above are the dataclass fallbacks. A transcript you create in
the app is actually seeded with the colors from Settings, under Defaults, not
with these.

### A bookmark

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `index` | int | | The word position it points at. A transcript holds at most one bookmark per position. |
| `snippet` | string | `""` | A short piece of the surrounding text, captured when the bookmark was made, so it is recognizable in the list. |
| `created_at` | string | `""` | An ISO-8601 timestamp. |
| `label` | string | `""` | An optional name you gave it. When empty, the list shows the snippet instead. |

## The settings file: `settings.json`

A flat object, one key per setting. Defaults shown.

**Window and layout**

| Field | Default | Meaning |
| --- | --- | --- |
| `window_width` | 1000 | Main window width. |
| `window_height` | 650 | Main window height. |
| `sidebar_width` | 220 | Sidebar width. |
| `bottom_band_height` | 100 | Control-band height. |
| `freeform_resize_enabled` | false | Whether borders can be dragged directly. |

**New-transcript defaults**

| Field | Default | Meaning |
| --- | --- | --- |
| `default_wpm` | 300 | Speed for new transcripts. |
| `default_font_color` | `#3B2E27` | Word color for new transcripts. |
| `default_highlight_color` | `#D98A3D` | Highlight color for new transcripts. |
| `default_background_color` | `#F6EFE3` | Background for new transcripts. |
| `default_font_size` | 32 | Word size for new transcripts. |
| `font_size_step` | 1 | Pixels the +/- buttons change word size by. |
| `default_chunking_enabled` | false | Whether new transcripts start with grouping on. |
| `default_chunk_size` | 2 | Fixed words-per-group for new transcripts (2 to 5). |
| `default_chunk_mode` | `fixed` | Group-size mode for new transcripts: `fixed` or `adaptive`. |
| `default_chunk_char_target` | 30 | Adaptive group width for new transcripts (15 to 60). |

**Reading behavior** (all global, applied to every transcript)

| Field | Default | Meaning |
| --- | --- | --- |
| `skip_word_count` | 10 | Words per skip. |
| `pause_on_skip` | false | Pause on the word a skip lands on. |
| `length_pacing_enabled` | false | Give longer words more time. |
| `warm_up_enabled` | false | Ease in from half speed over the first words. |
| `resume_rewind_enabled` | false | Step back a few words when resuming. |
| `resume_rewind_words` | 3 | How many words to step back on resume. |
| `scrub_pause_enabled` | true | Pause on the word after releasing the scrubber. |
| `peripheral_context_enabled` | false | Show the dim surrounding-words line. |
| `highlight_offset_px` | 0 | Shift the focus letter up (positive) or down (negative). |
| `letter_spacing_level` | 0 | Room between the letters of the flashing word: 0 Off, 1 Small, 2 Medium, 3 Large. A number outside 0 to 3 is treated as the nearest level, and anything that is not a whole number as Off. |

**Guide marks** (global)

| Field | Default | Meaning |
| --- | --- | --- |
| `guide_mark_horizontal_enabled` | false | Show the horizontal crosshair lines. |
| `guide_mark_thickness_px` | 2 | Vertical mark thickness. |
| `guide_mark_length_percent` | 35 | Mark length as a percent of word size. |
| `guide_mark_color` | `#3B2E27` | Mark color. |
| `guide_mark_color_is_default` | true | Whether the mark color still follows the theme default. |

**Reading profiles**

| Field | Default | Meaning |
| --- | --- | --- |
| `profiles` | `[]` | The saved reading profiles, in the order they were added. Each is the object below. |

**Normalize, storage, and appearance**

| Field | Default | Meaning |
| --- | --- | --- |
| `split_long_paragraphs_enabled` | false | Whether Normalize also splits long prose into paragraphs. |
| `data_directory` | `~/.rsvp_reader` | Where `data.json` is written. |
| `appearance_mode` | `light` | Theme: `light`, `dark`, or `system`. |
| `dyslexia_font_enabled` | false | Use the OpenDyslexic font for the whole app. Only `true` turns it on. Like the theme, it is read once at startup, so a change shows on the next launch. |

### A reading profile

Each entry in `profiles` is an object with a name and the settings it holds:

```json
{
  "name": "Fast skim",
  "values": { "skip_word_count": 25, "length_pacing_enabled": false, "guide_mark_color": null }
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | string | The profile's name: at most 30 characters, and unique without regard to capitals. |
| `values` | object | The settings it holds, keyed by the same names as in `settings.json`. |

A profile can hold these settings: `highlight_offset_px`,
`guide_mark_horizontal_enabled`, `guide_mark_thickness_px`,
`guide_mark_length_percent`, `guide_mark_color`, `length_pacing_enabled`,
`warm_up_enabled`, `resume_rewind_enabled`, `resume_rewind_words`,
`peripheral_context_enabled`, `skip_word_count`, `pause_on_skip`,
`default_wpm`, `default_font_size`, `font_size_step`,
`split_long_paragraphs_enabled`, `scrub_pause_enabled` and
`letter_spacing_level`. It never holds a transcript's own values, the Defaults
colours, the chunking defaults, the window and layout sizes, the data
directory, the theme, or the `dyslexia_font_enabled` font switch. The font is
left out because it is only read at startup, so a profile could not switch it
on the spot the way it does everything else.

- A setting that is missing from `values` means "leave that setting alone" when
  the profile is applied. That is how a profile saved before a setting joined
  the list keeps working.
- `guide_mark_color` is `null` when the colour was still following the Light /
  Dark theme at the moment the profile was saved, and a `"#RRGGBB"` value only
  when it was picked by hand.
- Numbers are pulled back into the range the Settings window allows when the
  profile is applied, so a hand-edited value cannot push a setting out of range.
- A malformed entry is skipped when the file is loaded, an unknown or invalid
  key inside a profile is ignored, and when two profiles share a name (ignoring
  capitals) the first one is kept.

## The export bundle

Exporting (Settings, under Storage, then **Export Data**) writes a single file,
by default named `rsvp-reader-export.json`, with this shape:

```json
{
  "bundle_format": 1,
  "data": { "next_id": 7, "current_space_index": 0, "spaces": ["General"], "transcripts": [] },
  "settings": { "window_width": 1000, "...": "every setting except data_directory" }
}
```

- `data` is exactly the contents of `data.json`.
- `settings` is everything from `settings.json` **except `data_directory`**,
  which is left out on purpose: it is a machine-specific path that would be
  meaningless, or wrong, on another computer. Your saved reading profiles are
  part of it.
- `bundle_format` is the format version, currently `1`. A bundle from a
  different format version is refused rather than misread.

Importing (under Storage, then **Import Data**) offers two modes:

- **Replace** wipes everything on this machine and replaces it with the
  bundle's transcripts, Spaces, and settings, profiles included. Your local
  `data_directory` is kept. A bundle exported before profiles existed has no
  profiles in it, and for that one the profiles already on this machine are
  kept.
- **Expand** adds the bundle's transcripts and Spaces to what you already have
  and leaves your settings untouched. There is no settings merge, since
  settings are single preferences rather than a collection.

Either way the app closes after importing, so reopen it to see the result.

## Backing up, moving, and editing by hand

To back up, copy `data.json` (and `settings.json` if you want your preferences
too). To move to another machine, use Export and Import rather than copying raw
files, so paths are handled correctly.

The files are plain JSON, so you can read or edit them, but a few cautions. The
app reads defensively: missing fields are filled in with defaults, fields it
does not recognize are ignored, and a corrupt or unreadable file is treated as
"no save yet" and falls back to defaults rather than crashing. That makes the
format forgiving across versions, but it also means a bad edit can quietly lose
data. Close the app before editing (it overwrites these files as you use it, and
saves again on close), and keep a copy first.