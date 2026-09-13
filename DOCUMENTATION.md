# SnapXO documentation

Every command, every flag, every file SnapXO writes. The
[README](https://github.com/posch-dev/snapxo/blob/main/README.md) is the short version.

- [Install](#install)
- [Flow](#flow)
- [Commands](#commands)
- [Output](#output)
- [Resume and re-runs](#resume-and-re-runs)
- [Privacy](#privacy)

## Install

```bash
pip install snapxo
snapxo doctor        # what is missing, and the command to install it
```

Python 3.10+, Windows, Linux or macOS.

| What | Install | Needed for |
|---|---|---|
| ffmpeg, ffprobe | Windows `winget install Gyan.FFmpeg`<br>Debian/Ubuntu `sudo apt install ffmpeg`<br>Fedora `sudo dnf install ffmpeg`<br>Arch `sudo pacman -S ffmpeg`<br>macOS `brew install ffmpeg` | videos, voice messages, overlays |
| `snapxo[ffmpeg]` | `pip install "snapxo[ffmpeg]"` | ffmpeg without a system install, no hardware encoding |
| Chromium | `playwright install chromium`<br>Linux maybe also `playwright install-deps chromium` | `snapxo pdf` only |
| `snapxo[spreadsheet]` | `pip install "snapxo[spreadsheet]"` | `snapxo spreadsheet --format xlsx` |
| `snapxo[docker]` | `pip install "snapxo[docker]"` | `snapxo docker --password` and `--append` |

Photos alone need none of it. The export buttons inside `index.html` need no
Chromium either.

From a clone, every command runs as `python -m snapxo ...`.

## Flow

1. Request your data at [accounts.snapchat.com](https://accounts.snapchat.com), download the ZIP
2. `snapxo info mydata.zip`
3. `snapxo organize mydata.zip -o ./archive -y`
4. Open `archive/index.html`
5. Later exports: organize each one, then `snapxo merge`
6. Optional: `pdf`, `spreadsheet`, `docker`, `verify`

What `organize` runs, in order:

Input → Inspect → Extract → Scan → Fix types → Dedup → Voice check → Organize →
Voice convert → Overlay → Encode H.265 → EXIF/GPS → File dates → Thumbnails →
Snap Map → Pages → Meta → Checksums → Cleanup

## Commands

| Command | Does |
|---|---|
| `snapxo info EXPORT` | show what an export contains, writes nothing |
| `snapxo organize EXPORT -o ARCHIVE` | turn an export into an archive |
| `snapxo rebuild ARCHIVE` | rewrite the pages of an archive with the current version |
| `snapxo html ARCHIVE` | one page per topic, beside `index.html` |
| `snapxo pdf ARCHIVE` | media, statistics and chats as PDFs |
| `snapxo spreadsheet ARCHIVE` | statistics as XLSX, ODS or CSV |
| `snapxo merge ARCHIVE... -o ARCHIVE` | combine archives into one |
| `snapxo docker ARCHIVE` | serve an archive on your network |
| `snapxo verify ARCHIVE...` | check an archive against its manifest |
| `snapxo doctor` | check ffmpeg, hardware encoding, Chromium, free space |
| `snapxo -i` | answer questions instead of typing flags |

`ARCHIVE` is a folder SnapXO made, or anything inside it (`_meta`, a year folder).

### organize

```bash
snapxo organize mydata.zip -o ./archive -y
snapxo organize export1.zip export2.zip -o ./archive -y
snapxo organize ~/Downloads -o ./archive -y          # every Snapchat ZIP in it
snapxo organize ./extracted/ -o ./archive -y
snapxo organize mydata.zip --media memories --types photos,videos --since 2024-01-01
```

| Flag | Does |
|---|---|
| `-o, --output PATH` | archive folder, created if missing |
| `-y, --yes` | no questions |
| `--dry-run` | show, write nothing |
| `--media memories,chat` | where media come from (default: both) |
| `--types photos,videos,voice` | what they are (default: all) |
| `--since YYYY-MM-DD` / `--until YYYY-MM-DD` | time range, inclusive |
| `--timezone ZONE` | convert UTC, e.g. `Europe/Vienna`, stored in the archive |
| `--folder-structure [year\|year-month]` | folder per year or per month (default: year) |
| `--no-encode` | keep videos as they are |
| `--no-overlay` | don't burn overlays |
| `--no-exif` | don't write EXIF/GPS |
| `--no-dedup` | keep duplicates |
| `--no-meta` | don't keep the raw export in `_meta/`, **see below** |
| `--software-encoding` | CPU only, ignore QSV and NVENC |
| `--crf INT` | video quality 0-51, lower is better (default: 23) |
| `--ffmpeg-path PATH` / `--ffprobe-path PATH` | binaries not on `PATH` |
| `--resume / --no-resume` | continue an interrupted run (default: resume) |
| `--keep-raw-html` | keep Snapchat's own HTML in `_meta/html/` |
| `--no-checksums` | skip the fingerprints `verify` uses |
| `-v, --verbose` | every file, not just totals |

`index.html` is always written, even with no media copied.
`--types voice` needs ffprobe, `--types photos` needs no ffmpeg at all.

> **`--no-meta` cannot be undone.** `rebuild` and `merge` need `_meta/json/`
> and never work on that folder again.

### info

```bash
snapxo info mydata.zip
snapxo info ~/Downloads
```

| Flag | Does |
|---|---|
| `-v, --verbose` | every file |

### rebuild

```bash
snapxo rebuild ./archive
```

Pages, map and thumbnails from `_meta/`, without the original export. Media are
never touched.

| Flag | Does |
|---|---|
| `--timezone ZONE` | switch the archive to this zone, later commands use it too |
| `--dry-run` | show, write nothing |
| `-v, --verbose` | every file |

### html

```bash
snapxo html ./archive
snapxo html ./archive --chats-with alex,sam --min-messages 50
```

Writes `gallery.html`, `chats.html`, `stats.html` and `conversations/` into the
archive. No `-o`: the pages reach the media by relative path. `stats.html` also
works on its own.

| Flag | Does |
|---|---|
| `--chats-with NAME,NAME` | only these contacts, by Snapchat username |
| `--min-messages N` | skip chats with fewer messages (default: 1) |
| `--stats-only CAT,CAT` | only these categories: `account`, `calls`, `engagement`, `friends`, `locations`, `search`, `stickers` |
| `--dry-run` | show, write nothing |
| `-v, --verbose` | every file |

### pdf

```bash
snapxo pdf ./archive
snapxo pdf ./archive --media-plain
snapxo pdf ./archive --chats --chats-with alex,sam
snapxo pdf ./archive -o ~/Desktop/printing
```

No flag renders everything. Media and chats are split into parts of at most
110 MB, each with its own cover page (part, range, account, sources):

| Output | Flag | Holds |
|---|---|---|
| `media-details/<year>/media-details-<year>-part-x-of-y.pdf` | `--media-details` | every file with its details |
| `media-plain/<year>/media-plain-<year>-part-x-of-y.pdf` | `--media-plain` | picture book, only the date |
| `stats.pdf` | `--stats` | numbers and charts |
| `chats/<chat>/<chat>-part-x-of-y.pdf` | `--chats` | one folder per chat, attachments with details |

A re-run replaces a year or chat only once all its new parts are written.
PDFs from 2.0.0 (`media-plain.pdf`, `chats/<chat>.pdf`) are removed after that.

| Flag | Does |
|---|---|
| `--media-details` | only media with details |
| `--media-plain` | only the picture book |
| `--stats` | only statistics |
| `--chats` | only chats |
| `--chats-with NAME,NAME` | only these contacts |
| `--min-messages N` | skip chats with fewer messages (default: 1) |
| `--stats-only CAT,CAT` | only these statistics categories |
| `-o, --output PATH` | instead of `pdf/` in the archive |
| `--dry-run` | show, write nothing |

### spreadsheet

```bash
snapxo spreadsheet ./archive                  # XLSX with editable Excel charts
snapxo spreadsheet ./archive --format ods
snapxo spreadsheet ./archive --format csv     # one file per table
```

The numbers behind the charts, not chats or media.

| Flag | Does |
|---|---|
| `--format [xlsx\|ods\|csv]` | format (default: xlsx, needs `snapxo[spreadsheet]`) |
| `-o, --output PATH` | instead of `spreadsheet/` in the archive |
| `--dry-run` | show, write nothing |

### merge

```bash
snapxo merge ./archive-2024 ./archive-2026 -o ./merged
snapxo merge ./all-archives -o ./merged
snapxo merge ./all-archives -o ./merged --hardlink --delete-sources
```

Deduplicates by content, renumbers by date, combines the JSON and rebuilds the
pages. Nothing is re-encoded. Chats and data missing from a newer export, e.g.
after blocking someone, stay in. The timezone comes from the newest archive.
PDFs are not carried over: run `snapxo pdf` on the result.

| Flag | Does |
|---|---|
| `-o, --output PATH` | merged archive (not needed with `--dry-run`) |
| `--hardlink` | link instead of copy, same drive only |
| `--delete-sources` | delete the inputs after re-hashing and asking |
| `-y, --yes` | don't ask before deleting |
| `--folder-structure [year\|year-month]` | folder per year or per month |
| `--verify / --no-verify` | check inputs first, a damaged file stops the merge (default: verify) |
| `--skip-damaged` | with `--no-verify`: leave damaged files out instead of marking them |
| `--dry-run` | show, write nothing |

An intact copy in another input beats a damaged one.
`--delete-sources` cannot be combined with `--no-verify`.

### docker

```bash
snapxo docker ./archive --password
snapxo docker ./archive --no-auth --port 9000 --up
```

Writes a `docker-compose.yml`: nginx, archive mounted read-only. Images load
only when a page asks for them.

| Flag | Does |
|---|---|
| `--password` | basic auth, prompts for it, user `snapxo` |
| `--no-auth` | no password |
| `--port INT` | host port (default: 7627) |
| `-o, --output PATH` | compose file elsewhere |
| `--append FILE` | add the service to an existing compose file |
| `--up` | `docker compose up -d` afterwards |
| `--dry-run` | show, write nothing |

`--password` or `--no-auth` is required.

> **Never forward this port through your router.** Basic auth over HTTP sends
> the password with every request. From outside: VPN or a reverse proxy with TLS.

### verify

```bash
snapxo verify ./archive
snapxo verify ./archive --hash
```

| Flag | Does |
|---|---|
| `--hash` | read every byte against `_meta/checksums.json` (slow, finds bit rot) |
| `--update` | accept the current state as the new baseline |

Without `--hash`: every file present, right size.

### doctor

```bash
snapxo doctor
```

ffmpeg, ffprobe, hardware encoding, Chromium, free space, and the install
command for whatever is missing.

## Output

```
archive/
├── 2026/
│   ├── 2026-05-08_0444.mp4  H.265, with EXIF/GPS
│   ├── 2026-05-08_0445.jpg
│   └── 2026-05-08_0446.mp3  voice message
├── _overlays/               overlays that matched no media
├── _meta/
│   ├── manifest.json        every file: origin, folder, type, size, media ID
│   ├── checksums.json       baseline for verify
│   ├── integrity.json       files that arrived damaged
│   ├── app-chats.js         Chats tab data
│   ├── app-media.js         Media tab data
│   ├── app-stats.js         Stats tab data
│   ├── thumbs/              previews
│   │   └── medium/          print size, from snapxo pdf
│   ├── json/                raw export JSON
│   └── html/                Snapchat's HTML, with --keep-raw-html
├── index.html               Overview, Stats, Media, Chats
└── map.html                 Snap Map
```

| Command | Adds |
|---|---|
| `snapxo pdf` | `pdf/`: `stats.pdf`, `media-details/`, `media-plain/`, `chats/` |
| `snapxo spreadsheet` | `spreadsheet/` |
| `snapxo docker` | `docker-compose.yml`, with `--password` also `snapxo.conf` and `.htpasswd` |
| `snapxo html` | `gallery.html`, `chats.html`, `stats.html`, `conversations/` |

## Resume and re-runs

- An interrupted `organize` continues where it stopped, via
  `.snaporganizer_checkpoint.json`. Nothing is encoded, overlaid or copied twice.
- Changed input, output or flags start fresh, as does `--no-resume`.
- `rebuild`, `html`, `pdf`, `spreadsheet` and `verify` can run on the same
  archive as often as you like. Older archives are brought up to date, never
  broken.

## Privacy

- Runs offline on your own export, never logs in, never contacts Snapchat.
- `map.html` loads Leaflet and OpenStreetMap tiles in your browser when opened.
- Chromium for `snapxo pdf` runs in offline mode.
- `snapxo docker` listens on every network interface: set a password.

Licenses and the Snap Inc. disclaimer: [README](https://github.com/posch-dev/snapxo/blob/main/README.md#license).
