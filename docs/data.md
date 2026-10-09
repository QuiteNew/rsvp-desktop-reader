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

**Guide marks** (global)

| Field | Default | Meaning |
| --- | --- | --- |
| `guide_mark_horizontal_enabled` | false | Show the horizontal crosshair lines. |
| `guide_mark_thickness_px` | 2 | Vertical mark thickness. |
| `guide_mark_length_percent` | 35 | Mark length as a percent of word size. |
| `guide_mark_color` | `#3B2E27` | Mark color. |
| `guide_mark_color_is_default` | true | Whether the mark color still follows the theme default. |

**Normalize, storage, and appearance**

| Field | Default | Meaning |
| --- | --- | --- |
| `split_long_paragraphs_enabled` | false | Whether Normalize also splits long prose into paragraphs. |
| `data_directory` | `~/.rsvp_reader` | Where `data.json` is written. |
| `appearance_mode` | `light` | Theme: `light`, `dark`, or `system`. |

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
  meaningless, or wrong, on another computer.
- `bundle_format` is the format version, currently `1`. A bundle from a
  different format version is refused rather than misread.

Importing (under Storage, then **Import Data**) offers two modes:

- **Replace** wipes everything on this machine and replaces it with the
  bundle's transcripts, Spaces, and settings. Your local `data_directory` is
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