# Changelog

All notable changes to SnapXO are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the version numbers
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-08-24

### Added

- **One page instead of four**: `index.html` is the whole archive now, with
  Overview, Stats, Media and Chats.

  - Overview is a quick look at your stats, your busiest chats and the newest media
  - Chats got a sidebar and a search across every message, see the next point
  - Media has a year dropdown that filters, where the old buttons only jumped
  - Stats groups the numbers into a table instead of loose tiles
  - a way back to the top appears once there is something to scroll back from

  It reads well on a phone. The bars keep clear of the notch, and the columns
  reorder into the order you actually use them in on a small screen.

- **Reactive UI support for mobile**: every `.html` file now has reactive design,
  optimised for both Desktop and Mobile. 

- **Master chat view**: the chats look like Snapchat Web now.

  - the header search finds chat names and message text at once
  - a second search filters inside the open chat alone
  - the open chat saves as a PDF from the page, without the command line

- **Charts**: statistics show curves and rings now, not only totals.

  - messages, chat media, snaps and story views over time
  - a friend headcount curve, rebuilt from when people were added and left
  - activity by time of day or by weekday
  - type distribution as a ring: text, snaps, memories, chat media, voice notes
  - who writes you most, and who you interact with most

  Every chart has an info button for what it does *not* show, and an export button
  for its numbers or a PNG of the picture. They fold away and sit two to a row.
  They are inline SVG, so they need no library and print unchanged. On paper they
  switch to blue, dark red and green.

- **New Snap Map**: the same places, two ways to look at them.

  - Locations plays your route back and draws it
  - Memory locations clusters like the real SnapMap

  A time bar is pinned to the bottom on every screen size, with two month pickers
  and step buttons. A desktop also gets the two handle sliders.

- **Display names in the chats**: names instead of usernames, the way Snapchat
  shows them. They come from every friend list, deleted and blocked included. The
  username stays in small grey brackets. Three coloured circles mark a group, and
  an untitled group takes the names of its members instead of a raw uuid.

- **`snapxo pdf <folder>`**: the archive rendered for paper.

  - `media-plain.pdf`, every media file
  - `media-details.pdf`, every media file with all of its metadata printed out too.
  - `stats.pdf`, the numbers and charts in colours meant for paper
  - `chats/*.pdf`, one per conversation, attachments with their details beside them

  Every one gets a cover page, a running header and page numbers. Sender colours
  survive the print. A video prints its still frame with a play mark. Images go in
  at 1280 px, which beats what a 300 dpi page resolves and keeps a chat with many
  photos small. `-o` puts the files anywhere.

- **Spreadsheet export**: the numbers behind the charts as a table. Use
  `snapxo spreadsheet` or the buttons in the page, as XLSX, ODS or CSV. The command
  line additionally offers editable Excel charts.

- **Timezones**: `--timezone Europe/Vienna` moves every timestamp out of UTC, so
  your busiest hour is the hour you actually lived in. The archive remembers the
  choice, and `-i` offers 59 zones in columns.

- **More Archive Data**: which export files went in, what period they cover, in
  which timezone, and when the pages were last written. On the Stats tab and on
  every PDF cover page.

- **More Media Data**: length, resolution, encoding and bitrate for every file.
  ffprobe measures it once and the manifest keeps it, so a later run does not pay
  for it again. It shows up in the details panel, in `media-details.pdf` and beside
  every attachment in a chat PDF.

- **`snapxo rebuild <folder>`**: writes the pages of a finished archive again. It
  works from `_meta/manifest.json` and `_meta/json/` alone, so an older archive
  picks up everything new without the original export. It never touches your media.

- **`snapxo html <folder>`**: writes the one page per topic layout beside the app.
  You can hand a single page on without the rest of the archive.

- **`snapxo info <export>`**: what an export contains, before converting anything.
  It was previously: `organize --info`.

- **`snapxo docker <folder>`**: writes a `docker-compose.yml` that serves the
  archive read-only with nginx, to reach it from a phone or another machine on
  your network. It listens on every interface, so it insists on a decision:
  `--password` puts basic auth in front, `--no-auth` serves it openly. Port 7627
  by default, which is SNAP on a phone keypad ^^.

- **`snapxo -i`**: asks questions instead of making you read the flags. It prints
  the matching command line before it starts, which doubles as a way to learn
  them. It covers all ten commands and asks which media before anything about
  encoding.

- **Forgiving input pointer**: point at anything inside an archive and SnapXO
  finds it. `_meta`, a year folder, `_meta/thumbs/medium`, or a folder holding
  several archives. Three levels up, two down, thirty folders at most.

### Changed

- **Flag restructure**: two flags replace eighteen. Nine `--only-*` and nine
  `--no-*` all answered one question, and every new part cost two more. `--media
  memories,chat` says where a file came from, `--types photos,videos,voice` says
  what it is. The pages left that question, because `index.html` is one app and
  picking its parts apart only ever produced a broken page.

- **Voice Message handling**: voice sits on `--types`, not on `--media`. Snapchat
  ships voice messages as MP4 without a picture and SnapXO makes the MP3 itself,
  so it is a property of the file, not a place in the export.

- **No ffmpeg for photos**: `--types photos` skips the voice detection. That step
  opens every video with ffprobe and was the slowest part of the run.

- **Safer defaults**: `--clean` and `--checksums` both had to be asked for, which
  is backwards for an archive meant to outlive the export it came from. Both are
  on now, with `--keep-raw-html` and `--no-checksums` as the opposites.

- **`--no-meta` safety**: it is the one flag that makes a folder impossible to
  rebuild or merge, forever, and it used to pass in silence. It warns and waits
  for an answer now. `-y` skips the question, a dry run only warns, and with no
  terminal to ask on it stops and names `-y`.

- **A command is required now**: `snapxo mydata.zip -o out` used to be read as
  `snapxo organize`. A mistyped command became an export path and failed deep in
  the pipeline instead of right away.

- **`--no-hwaccel` is `--software-encoding`**: the name says what happens instead
  of naming the thing that does not.

- **Page filters moved**: `--conversations-for`, `--conversations-min-messages`
  and `--stats-only-categories` are now `--chats-with`, `--min-messages` and
  `--stats-only`, on `snapxo html` and `snapxo pdf`. On `organize` they only ever
  reached the loose pages and never the app.

- **Media gallery moved**: it is `gallery.html` now, since `index.html` is the
  app. Only `snapxo html` writes it.

- **Date picker offers patterns**: `YYYY-MM-DD` instead of an example date, under
  the label "Date formatting".

### Fixed

- **Missing location history**: Snapchat writes some entries as
  `52.67455 ± 65.00 meters`, which the coordinate parser could not read. SnapXO
  reads them now and keeps the accuracy.

- **map.html size reduced**: down to a tenth. It no longer embeds a block of
  markup for every marker.

- **Message Count label**: `3468 messages` rather than a bare number next to a name.

- **Merging used wrong metadata**: anything that is not a list kept the older
  value, so a merged archive showed the older Snapscore and Last Active. The
  newer export wins now.

- **`--only-memories` quietly cost you `rebuild` and `merge` forever**:
  `should_process_meta()` returned False as soon as any `--only` flag was set, so
  `_meta/json/` was never written and nothing on screen said so. Narrowing the
  media no longer touches the raw export.

- **`--only-voice` never worked**: it appeared in `has_only_filter` and in
  `should_process_media()`, but in none of the conditions that actually pick the
  files. Doing roughly the right thing was a side effect.

- **"No raw export" messages were unreachable**: `load_json_data()` also reads
  JSON lying directly in the folder it is given, and `_meta` holds
  `manifest.json` and `checksums.json`. A `--no-meta` folder came back full
  instead of empty. SnapXO skips its own bookkeeping files now.

- **Overlay burning used ffmpeg**: only encoding triggered the check, so a run
  with `--no-encode` and no ffmpeg reached the burning step before failing.

- **ffprobe errors passed silently**: `has_video_stream()` answers True on any
  error, so the voice detection found nothing and said nothing. `--types voice`
  stops outright now, and `--types videos` warns that they come along as MP4.

- **Nothing was written when the selection copied no media**: the pages hung on a
  non-empty file index. The chats, the statistics and the map come from the JSON
  and work without a single file copied.

- **No video preview with `merge`**: it never handed ffmpeg to the thumbnail step,
  so a merged gallery showed video tiles without an image.

### Removed

- **`--conversation-format`, `--index-format` and `--stats-format`**: asking for a
  PDF used to mean giving up the HTML. `snapxo pdf` renders them as an addition
  instead.

- **The fallback to `organize`**: a command has to be named on every run now.

- **`--only-*` and `--no-*` flags**: nine of each, replaced by `--media` and
  `--types`. The four that picked pages apart are gone without replacement,
  because `index.html` is one app.

- **`--separate-pages`** on `organize` and `rebuild`, replaced by `snapxo html`.

- **`--info`** on `organize`, replaced by `snapxo info`.

### Migration from 1.1.1

Nothing in an existing archive has to change. `snapxo rebuild` brings a folder made
with any earlier version up to date, and `merge` and `verify` read them as they
always did. Only the command line moved.

| 1.1.1 | Now |
|---|---|
| `snapxo mydata.zip -o out` | `snapxo organize mydata.zip -o out` |
| `organize --info` | `snapxo info` |
| `organize --only-memories` | `organize --media memories` |
| `organize --only-chat-media` | `organize --media chat` |
| `organize --only-media` | nothing, the media are copied by default |
| `organize --only-photos` | `organize --types photos` |
| `organize --only-videos` | `organize --types videos` |
| `organize --only-voice` | `organize --types voice` |
| `organize --only-conversations` | gone, `index.html` is one page |
| `organize --only-stats` | gone, `index.html` is one page |
| `organize --only-map` | gone, the map is always written |
| `organize --no-index` | gone, `index.html` is the app |
| `organize --no-conversations` | gone, the chats are part of the app |
| `organize --no-stats` | gone, the statistics are part of the app |
| `organize --no-map` | gone, the map is always written |
| `organize --clean` | on by default, `--keep-raw-html` is the opposite |
| `organize --checksums` | on by default, `--no-checksums` is the opposite |
| `organize --no-hwaccel` | `organize --software-encoding` |
| `organize --conversations-for` | `snapxo html --chats-with` |
| `organize --conversations-min-messages` | `snapxo html --min-messages` |
| `organize --stats-only-categories` | `snapxo html --stats-only` |
| `organize --separate-pages` | `snapxo html` |
| `rebuild --separate-pages` | `snapxo html` |

`--no-meta` still exists and still does the same thing. It now says what it costs and
asks before doing it.

## [1.1.1] - 2026-08-15

### Changed

- **README**: screenshots of the gallery, the chat overview and a conversation,
  badges for version, Python and license, and a shorter description of what the
  tool is for. The license badge points at the file on GitHub, so the link also
  works on the PyPI page. No changes to the code

## [1.1.0] - 2026-08-14

### Added

- **Chat overview**: `chats.html` next to the other pages, listing every chat
  with avatar, last message, date and message count, sorted by recency or name.
  A search runs over the text of all messages and jumps straight to the message,
  which every conversation page now carries an anchor for
- **Media gallery as PDF**: `--index-format html|pdf` renders `index.pdf` from a
  print build of the gallery, with name, date, source, sender, chat, size and
  coordinates under each tile
- **Thumbnails**: preview images are written once to `_meta/thumbs/` and used by
  the gallery, its PDF and the images embedded in the conversations, instead of
  those pages pointing at the full files. A click still opens the original, and
  the conversation PDFs keep the full image, where it is printed much larger
- **`--stats-format html|pdf`**, which replaces the hidden coupling where
  `--conversation-format pdf` also rendered `stats.html`
- **`snapxo verify`**: checks a finished folder against its manifest. Without
  `--hash` only existence and size, with `--hash` against `_meta/checksums.json`,
  which finds bit rot. `--checksums` writes that baseline during a normal run
- **`snapxo doctor`**: reports ffmpeg, ffprobe, hardware encoding, the PDF
  browser and the free space, with the install command for what is missing
- **`--since` and `--until`**: process only a date range, both bounds inclusive
- **File dates**: every organized file gets the capture date as its modification
  time, which is the only date a video has
- **Integrity handling in merge**: input folders are checked before anything is
  written, damaged files stop the merge unless `--no-verify` is given, in which
  case they are taken along and marked in the manifest, in
  `_meta/integrity.json`, on the gallery tile and at the attachment.
  `--skip-damaged` leaves them out, and a damaged file is dropped when another
  export holds the same file intact

### Changed

- `-o/--output` is only required when something is written, so `--info` and
  `--dry-run` work without it, in `organize` and in `merge`
- `merge` writes `_meta/checksums.json` for the merged folder from the hashes it
  computes anyway
- Pillow is now required at 12.3.0 or newer, which fixes CVE-2026-59204
- The `map.html` libraries are pinned with subresource integrity hashes

### Fixed

- **A third of the location history never reached the map.** Snapchat writes some
  entries as `48.12345 ± 65.00 meters`, which the coordinate parser could not read,
  so it dropped them without a word. 378 of 1086 points here. The accuracy is kept
  and shown now
- **map.html went from 6.5 MB to under 600 KB**, because it no longer embeds a
  block of markup for every single marker
- **The last updated line ignored the date format picker**, being plain text rather
  than a tagged date. The same applied to the timestamps in the about block
- **The chat list counts now say what they count**, `1191 msg` rather than a bare
  number
- **Merging two overlapping exports** kept the older value for anything that is
  not a list, so a merged archive showed the older Snapscore and Last Active
- **A media tile is a link**, and an unstyled link underline in the accent colour
  drew a thick yellow bar under the audio icon
- **The info button did nothing in the app**: the details panel reads a variable
  only the standalone gallery ever set
- **`rebuild` and `merge` gave videos no preview**, because neither handed ffmpeg
  to the thumbnail step
- **Windows has no timezone database**, so `zoneinfo` would have silently done
  nothing; `tzdata` is a dependency there now

### Removed

- The sticker step, along with `--only-stickers` and `--no-stickers`. Snapchat
  ships the metadata but none of the PNGs, so it never produced anything. The
  sticker count stays in the inspect summary

### Security

- **Zip slip**: ZIP entries are checked before extraction. Absolute paths, drive
  letters, `..` traversal and symlink entries are refused, and the resolved
  target has to stay under the destination
- A damaged entry is skipped with its name reported, instead of aborting the run
- A ZIP whose unpacked size is out of all proportion to its compressed size is
  refused before extraction, and the free space on the temp and output volumes is
  checked against what it will need

## [1.0.0] - 2026-08-10

Initial release.

- **Media organization**: memories and chat media sorted into year or
  year-month folders with clean filenames (`2026-05-08_0444.mp4`)
- **H.265 encoding**: videos re-encoded with Intel QSV hardware acceleration,
  falling back to libx265
- **Overlay burning**: Snapchat overlays burned onto photos and videos
- **GPS and EXIF**: coordinates from `memories_history.json` written into image
  EXIF data
- **Duplicate removal**: content-hash deduplication, before encoding
- **Voice messages**: audio-only MP4s detected and converted to MP3
- **Conversations**: per-contact pages with messages, photos, videos and voice
  messages
- **Statistics**: overview page with cards and detail tables
- **Snap Map**: interactive map with route, timeline slider, playback animation
  and the location of each memory
- **Media gallery**: `index.html` with navigation, type filters, thumbnails and
  a details panel per file
- **Merge**: several exports combined into one, deduplicated and renumbered,
  without re-encoding
- **PDF export**: conversations and statistics rendered to PDF
- **Resume**: an interrupted run picks up where it stopped instead of copying
  and encoding everything again

Runs on Windows, Linux and macOS.
