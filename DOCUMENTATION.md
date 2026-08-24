# SnapXO documentation

The complete documentation.
The [README](https://github.com/posch-dev/snapxo/blob/main/README.md) is the short version and the place to start.

- [Requirements](#requirements)
- [Installation](#installation)
- [What SnapXO makes](#what-snapxo-makes)
- [What a run does](#what-a-run-does)
- [Commands](#commands)
- [Output structure](#output-structure)
- [Flags](#flags)
- [Resuming](#resuming)
- [Privacy](#privacy)

## Requirements

Python 3.10 or newer, on Windows, Linux or macOS.

ffmpeg and ffprobe are needed for videos, voice messages and overlays. Photos
alone need neither. `snapxo pdf` additionally needs a Chromium that Playwright
downloads; nothing else in SnapXO uses a browser.

`snapxo doctor` checks all of it and prints the install command for the system
you are on.

## Installation

```bash
pip install snapxo
```

### ffmpeg

ffmpeg and ffprobe are native programs, so pip cannot install them.

| System | Command |
|--------|---------|
| Windows | `winget install Gyan.FFmpeg` |
| Debian/Ubuntu | `sudo apt install ffmpeg` |
| Fedora | `sudo dnf install ffmpeg` |
| Arch | `sudo pacman -S ffmpeg` |
| macOS | `brew install ffmpeg` |

You can also `pip install "snapxo[ffmpeg]"`, which brings both binaries along
through `static-ffmpeg`. Those builds have no hardware
encoding, so a system-wide ffmpeg is the better option where you can have one.

If ffmpeg lives somewhere that is not on `PATH`, point at it with
`--ffmpeg-path` and `--ffprobe-path`.

### The extras

| Extra | Install | Needed for |
|---|---|---|
| `ffmpeg` | `pip install "snapxo[ffmpeg]"` | ffmpeg and ffprobe without a system install |
| `spreadsheet` | `pip install "snapxo[spreadsheet]"` | `snapxo spreadsheet --format xlsx` |
| `docker` | `pip install "snapxo[docker]"` | `snapxo docker --password` and `--append` |

None of them are needed for a normal run. ODS and CSV spreadsheets need nothing
extra, and `snapxo docker --no-auth` writes its compose file without the extra
as well.

### Chromium, for `snapxo pdf` only

```bash
playwright install chromium
```

On Linux it may also need `playwright install-deps chromium`. This is for the
`snapxo pdf` command on the command line and nothing else. The export buttons
inside the pages build their files in the browser you are already looking at
them with, so using the archive never needs this.

### From a clone

Every command works the same as `python -m snapxo ...`, so nothing has to be
installed to run it out of a cloned repo of **SnapXO**:

```bash
python -m snapxo organize mydata.zip -o ./output -y
```

## What SnapXO makes

`index.html` is the archive, with Overview, Stats, Media and Chats as tabs. It
opens straight from disk, needs no server, and works just as well on a phone as
on a desktop.

- **Chats** read like a messenger: list on the left, conversation on the right,
  one search across names and message text, a second one inside the open chat
- **Media** is the gallery: type filters, year dropdown, a details panel per
  file, loading more as you scroll
- **Stats** shows the numbers as a grouped table with a chart for each of them
- **Overview** opens on a pick of it all: the headline numbers, the busiest
  chats and the newest media

### What it does to your export

- **Media organization**: memories and chat media in structured folders with
  clean filenames (`2026-05-08_0444.mp4`)
- **H.265 encoding**: Intel QSV hardware acceleration, automatic fallback to libx265
- **Overlay burning**: Snapchat overlays burned onto photos and videos
- **GPS/EXIF**: coordinates from `memories_history.json` written into image EXIF
- **Duplicate removal**: MD5 deduplication, before encoding so nothing is encoded twice
- **Voice messages**: audio-only MP4s detected and converted to MP3
- **Timezone**: `--timezone Europe/Vienna` converts every timestamp out of UTC,
  so the busiest hour is the hour you lived in

### What it can tell you

- **Charts**: messages, chat media, snaps, friends and story views over time,
  activity by time of day or weekday, type distribution, who writes you most.
  Every one carries an info button saying what it does *not* show
- **Statistics**: memories, chat media, friends, calls, searches and your
  Snapscore, with a table behind every number
- **Snap Map**: two modes. Locations plays your route back, drawing it point by
  point. Memories clusters everywhere something was saved, and a click opens a
  strip of what is there

### What you can take out of it

- **Spreadsheet**: `snapxo spreadsheet` or the buttons in the page, as XLSX, ODS
  or CSV. The XLSX carries real Excel charts you can still edit yourself
- **PDF**: `snapxo pdf` renders the media, the statistics and every chat for paper
- **Serve**: `snapxo docker` writes a compose file that hosts the archive
  read-only on your own network, so you can reach it from your phone

### Made to outlive the export

- **Rebuild**: `snapxo rebuild` brings an older archive up to the current version
  without the original export, which is usually long deleted by then
- **Merge**: several exports combined into one, deduplicated and renumbered,
  without re-encoding anything
- **Verify**: a finished archive checked against its manifest and its checksums
- **Resume**: an interrupted run picks up where it stopped
- **Interactive**: `snapxo -i` asks the questions instead of making you read the flags

## What a run does

`snapxo organize` prints each step as it reaches it. In order:

| Step | What happens |
|---|---|
| Input | The inputs are read and the output folder is prepared |
| Inspect | The export is counted and summarised before anything is written |
| Extract | ZIPs are unpacked to a working directory |
| Scan | Memories, overlays and chat media are sorted into their groups |
| Fix Types | Files Snapchat named `.unknown` get their real extension from their magic bytes |
| Dedup | Identical files are found by MD5 and dropped, before any encoding |
| Voice Check | Every video is opened with ffprobe to find the ones with no picture |
| Organize | Files are copied into year folders and renamed by date and number |
| Voice Convert | The picture-less MP4s become MP3 |
| Overlay | Overlays are matched by date and UUID and burned onto their media |
| Encode H.265 | Videos are re-encoded, on the GPU where one is available |
| EXIF/GPS | Coordinates from `memories_history.json` are written into the images |
| File dates | Every file gets its capture date as its modification time |
| Thumbnails | Previews are measured and generated for the gallery and the chats |
| Snap Map | `map.html` is built from the location history and the memories |
| Pages | `index.html` and the `_meta/app-*.js` sidecars are written |
| Meta | The raw export is copied into `_meta/`, unless `--no-meta` |
| Checksums | Every file is fingerprinted for later `snapxo verify` runs |
| Cleanup | Working files are removed |

Steps that have nothing to do are skipped silently. A step that is switched off
by a flag, `--no-encode` and the like, never runs at all.

## Commands

Ten of them. `organize` makes the archive, the rest work on a finished one.

| Command | What it does |
|---|---|
| `snapxo info EXPORT` | what an export contains, writes nothing |
| `snapxo organize EXPORT -o ARCHIVE` | turn an export into an archive |
| `snapxo rebuild ARCHIVE` | bring a finished archive up to date |
| `snapxo html ARCHIVE` | the one page per topic versions |
| `snapxo pdf ARCHIVE` | the same, rendered for printing |
| `snapxo spreadsheet ARCHIVE` | the statistics as a table |
| `snapxo merge ARCHIVE...` | fold several archives into one |
| `snapxo docker ARCHIVE` | serve an archive over HTTP |
| `snapxo verify ARCHIVE...` | check an archive against its manifest |
| `snapxo doctor` | check whether ffmpeg and Chromium are there |

`ARCHIVE` means a folder SnapXO already organized. Pointing at something inside
it, like `_meta` or a year folder, works too.

### Organize an export

```bash
# Organize everything from ZIP(s)
snapxo organize mydata.zip -o ./output -y
snapxo organize export1.zip export2.zip -o ./output -y

# A folder full of ZIPs, anything that isn't a Snapchat export is ignored
snapxo organize ~/Downloads -o ./output -y

# An already extracted directory
snapxo organize ./extracted-export/ -o ./output -y

# Look before you write
snapxo organize mydata.zip --dry-run

# Answer questions instead of setting flags
snapxo -i
```

- `-o` is required whenever something is written. The directory is created if it
  doesn't exist and reused if it does.
- `--dry-run` shows what would happen, without it happening.

A named ZIP that isn't a Snapchat export is an error, ZIPs found by scanning a
folder are not.

### Look at an export before converting it

```bash
snapxo info mydata.zip
snapxo info ~/Downloads
```

Counts the media, lists the JSON files Snapchat included and says how much space
the whole thing takes up. Writes nothing.

### Rebuild the pages of a finished archive

```bash
snapxo rebuild ./output

# pointing at _meta or at a year folder works too
snapxo rebuild ./output/_meta
```

Reads `_meta/manifest.json` and `_meta/json/` and writes the pages again, so an
archive made with an older version picks up new features without the original
export. Your media files are never touched.

### Write the one page per topic versions

```bash
snapxo html ./output
snapxo html ./output --chats-with alex,sam
snapxo html ./output --min-messages 50
```

Writes `gallery.html`, `chats.html`, `stats.html` and one file per chat in
`conversations/`. `index.html` holds all of it too, so these are for handing a
single page on without the rest of the archive.

They are written into the archive and have no `-o`, on purpose: the pages find
their media through relative paths like `2026/photo.jpg`, so anywhere else they
would arrive as empty frames. `stats.html` is the exception — its charts are
inline SVG, so that one file travels on its own.

### Render PDFs

```bash
snapxo pdf ./output
snapxo pdf ./output --chats
snapxo pdf ./output --media-plain
snapxo pdf ./output --chats --chats-with alex,sam

# somewhere else entirely
snapxo pdf ./output -o ~/Desktop/printing
```

Writes into `pdf/` unless `-o` says otherwise. A PDF carries its pictures inside
it, so unlike the HTML pages it works anywhere you put it.

| File | Flag | What it holds |
|---|---|---|
| `media-details.pdf` | `--media-details` | every file with its filename, date, size, length and encoding beside it |
| `media-plain.pdf` | `--media-plain` | the same media as a picture book: uncropped, nothing under it but the date |
| `stats.pdf` | `--stats` | the numbers and charts, in colours meant for paper |
| `chats/*.pdf` | `--chats` | one per conversation, attachments with their details beside them |

Without a flag all four are rendered. Every one gets a cover page, a running
header and page numbers. The HTML pages stay as they are, a PDF is an addition.
This is the one command that needs `playwright install chromium`.

### Write the statistics to a spreadsheet

```bash
snapxo spreadsheet ./output                  # XLSX with real Excel charts
snapxo spreadsheet ./output --format ods     # OpenDocument, needs nothing extra
snapxo spreadsheet ./output --format csv     # one file per table
snapxo spreadsheet ./output -o ~/Desktop     # somewhere else entirely
```

Writes into `spreadsheet/` unless `-o` says otherwise. This is the numbers behind
the charts, not your chats or media.

The XLSX charts are real Excel charts, not pictures of charts: you can recolour
them, change their type or point them at other cells. They need
`pip install "snapxo[spreadsheet]"`. The same tables sit behind the buttons on
the Stats tab, which also offer a chart as a PNG.

### Serve the archive on your network

```bash
snapxo docker ./output --password
snapxo docker ./output --no-auth --port 9000 --up
```

Writes a `docker-compose.yml` that serves the archive as read-only with nginx, so
you can open it from a phone or another machine. Got a Raspberry Pi or a home
server sitting around? Run it there and browse your archive comfortably from
your phone whenever you want, without keeping your main machine on.

**Set a password.** This is years of your private messages, and the container
listens on every network interface, so anyone else in your home or on your office
network can reach it. `--password` prompts for one and puts basic auth in front,
`--no-auth` serves it openly. One of the two is required, there is no default
either way.

**Never forward this port through your router.** Basic auth over plain HTTP sends
the password on every request, only base64 encoded. That is fine on your own
network and not on the open internet. If you want it reachable from outside, put
it behind a VPN or a reverse proxy that terminates TLS.

`-o` writes the compose file into another directory, `--append` adds the service
to an existing compose file instead, which needs
`pip install "snapxo[docker]"`. `--up` starts it, in whichever of those places the
file ended up.

### Check a finished archive

```bash
snapxo verify ./output
snapxo verify ./output --hash
```

Without `--hash` it takes seconds: is every file from the manifest there, and is
it the right size. That already finds the usual half-copied folder. With `--hash`
it reads every byte and compares it to `_meta/checksums.json`, which is what
catches bit rot.

Worth doing after moving the archive to another drive, and once in a while just
because. The baseline is written during a normal run unless `--no-checksums` says
otherwise, and `--update` accepts the current state as a new one.

### Merge several output folders

```bash
snapxo merge ./out-2024 ./out-2026 -o ./merged

# Or point at a folder that contains them all
snapxo merge ./all-exports -o ./merged

# Instant merge without extra disk space, then drop the originals
snapxo merge ./all-exports -o ./merged --hardlink --delete-sources
```

Two exports of the same account overlap almost completely, and each one numbers
its year folders from `0001`. Merging removes the duplicates by content hash,
renumbers everything chronologically, and rebuilds the pages from the combined
JSON. Media is copied, never re-encoded.

- `--hardlink` is instant and costs no extra space, but works within one drive only
- `--delete-sources` removes the inputs, after re-hashing every merged file and asking

Every input folder is checked against its manifest first, and against its
checksums where they exist. A damaged file stops the merge:

- `--no-verify` takes those files along instead, marked in the manifest
- `--skip-damaged` leaves them out
- if another export holds the same file intact, the intact copy wins
- `--delete-sources` cannot be combined with `--no-verify`

### Check the tools

```bash
snapxo doctor
```

Says whether ffmpeg, ffprobe, hardware encoding and the PDF browser are in
place, prints the install command for anything missing, and reports the free
space on the drive.

## Output structure

```
output/
├── 2022/                    folders with organized media
├── ...
├── 2026/
│   ├── 2026-05-08_0444.mp4  H.265 encoded, with EXIF/GPS
│   ├── 2026-05-08_0445.jpg
│   └── 2026-05-08_0446.mp3
├── _overlays/               Overlays that matched no media
├── _meta/                   Raw JSON + HTML from export
│   ├── manifest.json        What each file is and where it came from
│   ├── checksums.json       Fingerprint for `snapxo verify`
│   ├── integrity.json       Files that arrived damaged, if any
│   ├── app-chats.js         Every chat and message, for the Chats tab
│   ├── app-media.js         Every file and its details, for the Media tab
│   ├── app-stats.js         The numbers behind the charts, for the export buttons
│   ├── thumbs/              Preview images for the gallery and the chats
│   │   └── medium/          Larger copies, written by `snapxo pdf` only
│   ├── json/
│   └── html/
├── index.html               The archive: Overview, Stats, Media, Chats
└── map.html                 Interactive Snap Map
```

The other commands add to it:

| Command | What it adds |
|---|---|
| `snapxo pdf` | `pdf/` with `media-details.pdf`, `media-plain.pdf`, `stats.pdf` and `pdf/chats/` |
| `snapxo spreadsheet` | `spreadsheet/` with one file per format |
| `snapxo docker` | `docker-compose.yml` |
| `snapxo html` | `gallery.html`, `chats.html`, `stats.html` and `conversations/` |

`_meta/manifest.json` is the record of where every file came from: its original
name in the export, the year folder it went to, its type, its size and the media
ID that links chat media to the message it arrived in. `rebuild`, `merge` and
`verify` all read it, which is why `--no-meta` costs you all three.

## Flags

### Input and output
| Flag | Description |
|------|-------------|
| `INPUT...` | One or more ZIPs, a folder containing ZIPs, or an already extracted export directory |
| `-o, --output PATH` | Directory the archive is written to, created if it doesn't exist. Required for `organize` and `merge`, optional on `pdf`, `spreadsheet` and `docker`, not taken at all by `info`, `rebuild`, `html` and `verify` |
| `-y, --yes` | Organize everything without asking |
| `--dry-run` | Show what would happen, without it happening |

### Which media are copied

Two axes, both defaulting to everything:

| Flag | Description |
|------|-------------|
| `--media SOURCE,SOURCE` | Where they came from: `memories`, `chat` |
| `--types KIND,KIND` | What they are: `photos`, `videos`, `voice` |
| `--since YYYY-MM-DD` | Only media and messages from this day on, inclusive |
| `--until YYYY-MM-DD` | Only media and messages up to this day, inclusive |

They combine, so `--media memories --types voice` takes the voice messages you
saved and nothing else.

The pages are not part of this question. `index.html` is one app and is always
written, even when no media are copied at all, because the chats, the statistics
and the map all come from the JSON.

Voice sits on `--types` because Snapchat ships voice messages as MP4 without a
picture and SnapXO makes the MP3 itself: it is a property of the file, not a
place in the export. Telling them apart means opening every video with ffprobe,
so `--types voice` needs ffprobe, and `--types photos` skips that step entirely
and needs no ffmpeg at all.

### Skip (what NOT to do)
| Flag | Description |
|------|-------------|
| `--no-encode` | Don't encode videos to H.265 |
| `--no-overlay` | Don't burn overlays onto media |
| `--no-exif` | Don't write EXIF/GPS into images |
| `--no-dedup` | Don't remove duplicate media |
| `--no-meta` | Don't copy the raw export to `_meta/` — **see the warning below** |

> **`--no-meta` is the one flag you cannot take back.** `rebuild` and `merge`
> live on the raw export in `_meta/json/`, and without it neither will ever work
> on that folder again. Not after a reinstall, not after an update, never. By
> then the export it came from is usually deleted. SnapXO warns and asks before
> doing it.

### Encoding
| Flag | Description |
|------|-------------|
| `--software-encoding` | Encode on the CPU, ignoring QSV and NVENC |
| `--crf INT` | Video quality, lower is better, 0-51 (default: 23) |
| `--ffmpeg-path PATH` | Path to the ffmpeg binary (default: `ffmpeg` on PATH) |
| `--ffprobe-path PATH` | Path to the ffprobe binary (default: `ffprobe` on PATH) |

### Output layout
| Flag | Description |
|------|-------------|
| `--folder-structure [year\|year-month]` | One folder per year, or one per month (default: year) |
| `--timezone ZONE` | Convert every timestamp out of UTC into this IANA zone, e.g. `Europe/Vienna`. The archive remembers it |

### System
| Flag | Description |
|------|-------------|
| `--resume / --no-resume` | Pick up where an interrupted run left off (default: resume), see [Resuming](#resuming) |
| `-v, --verbose` | Print every file as it is processed. Without it each step only reports its totals |
| `--keep-raw-html` | Keep Snapchat's own HTML pages in `_meta/html/`, which are dropped by default |
| `--no-checksums` | Skip fingerprinting the archive, which is what `snapxo verify` compares against |
| `--version` | Print the version and exit |
| `--help` | Show all options and exit |

### Merge
| Flag | Description |
|------|-------------|
| `FOLDERS...` | Two or more output folders, or one parent folder containing them |
| `-o, --output PATH` | Target directory for the merged archive. Required except with `--dry-run` |
| `--hardlink` | Link files instead of copying (same drive only, no extra space) |
| `--delete-sources` | Delete the input folders after a verified merge |
| `-y, --yes` | Don't ask before deleting the input folders |
| `--folder-structure [year\|year-month]` | One folder per year, or one per month (default: year) |
| `--verify / --no-verify` | Check the input folders against their manifests first (default: verify) |
| `--skip-damaged` | With `--no-verify`: leave damaged files out instead of taking them along marked |
| `--dry-run` | Show what would happen, without it happening |

### Rebuild
| Flag | Description |
|------|-------------|
| `FOLDER` | A finished output folder, or anything inside one |
| `--timezone ZONE` | Show timestamps in this zone instead of the stored one |
| `--dry-run` | Show what would happen, without it happening |
| `-v, --verbose` | Print every file as it is processed |

### HTML
| Flag | Description |
|------|-------------|
| `FOLDER` | A finished output folder, or anything inside one |
| `--chats-with NAME,NAME` | Only these contacts, by their Snapchat username |
| `--min-messages N` | Leave out conversations with fewer messages than this (default: 1) |
| `--stats-only CAT,CAT` | Only these statistics categories: `account`, `calls`, `engagement`, `friends`, `locations`, `search`, `stickers` |
| `--timezone ZONE` | Show timestamps in this zone instead of the stored one |
| `--dry-run` | Show what would happen, without it happening |
| `-v, --verbose` | Print every file as it is processed |

### PDF
| Flag | Description |
|------|-------------|
| `FOLDER` | A finished output folder, or anything inside one |
| `--media-details` | Only the media, with every detail beside each file |
| `--media-plain` | Only the media, as a picture book with nothing but the date |
| `--stats` | Only the statistics |
| `--chats` | Only the conversations |
| `--chats-with NAME,NAME` | Only these contacts, by their Snapchat username |
| `--min-messages N` | Leave out conversations with fewer messages than this (default: 1) |
| `--stats-only CAT,CAT` | Only these statistics categories: `account`, `calls`, `engagement`, `friends`, `locations`, `search`, `stickers` |
| `-o, --output PATH` | Directory to write the PDFs into, instead of `pdf/` inside the archive |
| `--dry-run` | Show what would happen, without it happening |

### Spreadsheet
| Flag | Description |
|------|-------------|
| `FOLDER` | A finished output folder, or anything inside one |
| `--format [xlsx\|ods\|csv]` | Which format to write (default: xlsx) |
| `-o, --output PATH` | Directory to write into, instead of `spreadsheet/` inside the archive |
| `--dry-run` | Show what would happen, without it happening |

### Docker
| Flag | Description |
|------|-------------|
| `FOLDER` | A finished output folder |
| `--password` | Protect the site with a password, which you are prompted for |
| `--no-auth` | Serve without any password |
| `--port INT` | Host port (default: 7627) |
| `-o, --output PATH` | Directory to write the compose file into, instead of the archive |
| `--append PATH` | Add the service to an existing `docker compose` file instead |
| `--up` | Run `docker compose up -d` afterwards, where the file ended up |
| `--dry-run` | Show what would happen, without it happening |

`--password` or `--no-auth` is required — the command refuses to guess, because
one default publishes your messages to the whole network and the other breaks
the reason the command exists.

### Verify
| Flag | Description |
|------|-------------|
| `FOLDERS...` | One or more finished output folders |
| `--hash` | Read every file and compare it to the stored checksums |
| `--update` | Write the current state as the new baseline |

## Resuming

Encoding a large export can take hours, so an interrupted run does not start
over. SnapXO writes `.snaporganizer_checkpoint.json` into the output folder while
it works and picks up there when the same command runs again:

```
Resuming from checkpoint (1 steps, 14 files already done)
```

Picking up means picking up properly:

- encoded videos are not encoded a second time
- overlays are not burned on top of each other
- organized files are not overwritten with their originals

The checkpoint stores a fingerprint of the input, the output folder and every
flag that changes what gets produced. Change any of them and the run starts
fresh, as it does with `--no-resume`. A completed run deletes it.

## Privacy

SnapXO runs entirely on your machine, on the export you downloaded yourself, and
makes no network requests while it works. It never logs into an account and never
contacts Snapchat.

Two things are worth knowing:

- **`map.html` loads its map library and its map tiles from the internet** when
  *you* open it. Generating it does not. Every other page works with no network
  at all.
- **`snapxo docker` serves your archive on every network interface**, which is
  what makes it reachable from your phone. Set a password, and do not forward the
  port through your router.

The browser Chromium that `snapxo pdf` uses is put into offline mode, so it
cannot reach the network even if a page asked it to.

> **Not affiliated with Snap Inc.**<br>
> This is an independent, unofficial open-source tool. It is not created,
> endorsed, sponsored or supported by Snap Inc., and has no connection to
> Snapchat, Snap Inc. or any of its products. "Snapchat" and "Snap" are
> trademarks of Snap Inc., used here only to describe what this tool reads.
> SnapXO works purely offline on a data export you requested and downloaded
> yourself. This tool never logs into an account and never contacts Snapchat.

## Credits and licence

SnapXO stands on other people's work, all of it listed with its licence in
[THIRD-PARTY-NOTICES.md](https://github.com/posch-dev/snapxo/blob/main/THIRD-PARTY-NOTICES.md). SnapXO itself is GPL-3.0.
