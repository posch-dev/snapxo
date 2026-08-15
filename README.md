# SnapXO (Snapchat Export Organizer)

[![PyPI](https://img.shields.io/pypi/v/snapxo)](https://pypi.org/project/snapxo/)
[![Python](https://img.shields.io/pypi/pyversions/snapxo)](https://pypi.org/project/snapxo/)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue)](https://github.com/posch-dev/snapxo/blob/main/LICENSE)

Snapchat hands you your data as a few thousand files named by ID and a pile of
JSON. This turns it into an archive you can still open in ten years: a clean,
browsable archive with sorted media, efficient video encoding, GPS metadata,
chat histories, statistics and an interactive map.

```bash
pip install snapxo
```

<table>
<tr>
<td valign="top"><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/gallery.jpg" height="230" alt="Media gallery"></td>
<td valign="top"><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/chats.png" height="230" alt="Chat overview with a search across all messages"></td>
<td valign="top"><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/conversation.png" height="230" alt="Rebuilt conversation with attachments"></td>
</tr>
</table>

## Features

- **Media Gallery**: `index.html` with navigation, type filters, thumbnails and a details panel per file
- **Chat Overview**: `chats.html` lists every chat like the app does, with a search across all messages
- **Conversations**: per-contact chat pages with messages, photos, videos and voice messages
- **Media Organization**: memories and chat media in structured folders with clean filenames (`2026-05-08_0444.mp4`)
- **H.265 Encoding**: Intel QSV hardware acceleration, automatic fallback to libx265
- **Overlay Burning**: Snapchat overlays burned onto photos and videos
- **GPS/EXIF**: coordinates from `memories_history.json` written into image EXIF
- **Duplicate Removal**: MD5 deduplication, before encoding
- **Voice Messages**: audio-only MP4s detected and converted to MP3
- **Statistics**: memories, chat media, friends, calls, searches and your Snapscore, with a table behind every number
- **Snap Map**: every memory pinned where it was taken, with a timeline you can play back
- **Merge**: several exports combined into one, deduplicated and renumbered, without re-encoding
- **PDF Export**: conversations, statistics and the media gallery as PDF
- **Verify**: a finished archive checked against its manifest and its checksums
- **Resume**: an interrupted run picks up where it stopped

Runs on Windows, Linux and macOS.

## Installation

```bash
pip install snapxo
```

`snapxo doctor` says what is missing and prints the install command for the
system you are on.

**For PDF export**: `playwright install chromium` downloads the browser that
renders them. On Linux it may also need `playwright install-deps chromium`.

**For video processing**: ffmpeg and ffprobe are native programs, so pip cannot
install them.

| System | Command |
|--------|---------|
| Windows | `winget install Gyan.FFmpeg` |
| Debian/Ubuntu | `sudo apt install ffmpeg` |
| Fedora | `sudo dnf install ffmpeg` |
| Arch | `sudo pacman -S ffmpeg` |
| macOS | `brew install ffmpeg` |

`pip install "snapxo[ffmpeg]"` provides both binaries through `static-ffmpeg` if
you cannot install them system-wide. Those builds have no hardware encoding, so
prefer a system-wide ffmpeg.

## Usage

```bash
# Organize everything from ZIP(s)
snapxo mydata.zip -o ./output -y
snapxo export1.zip export2.zip -o ./output -y

# A folder full of ZIPs, anything that isn't a Snapchat export is ignored
snapxo ~/Downloads -o ./output -y

# An already extracted directory
snapxo ./extracted-export/ -o ./output -y

# Look before you write
snapxo mydata.zip --info
snapxo mydata.zip --dry-run

# One year only, and the gallery as a PDF as well
snapxo mydata.zip -o ./output -y --since 2026-01-01 --until 2026-12-31
snapxo mydata.zip -o ./output -y --index-format pdf
```

`-o` is required whenever something is written. The directory is created if it
doesn't exist and reused if it does. `--info` and `--dry-run` write nothing, so
they work without it. Everything is also available as `python -m snapxo ...`.

A named ZIP that isn't a Snapchat export is an error, while ZIPs found by
scanning a folder are skipped silently. ffmpeg is taken from `PATH` unless
`--ffmpeg-path` and `--ffprobe-path` point elsewhere.

### Re-generate pages from a finished export

The input is the `_meta/json` folder of the finished export, not the export.

```bash
snapxo ./output/_meta/json -o ./output -y --only-conversations --conversation-format pdf
snapxo ./output/_meta/json -o ./output -y --only-stats
snapxo ./output/_meta/json -o ./output -y --only-map
```

### Check a finished archive

```bash
# Seconds: is every file from the manifest there, and the right size
snapxo verify ./output

# Reads everything and compares it to _meta/checksums.json, the first run writes it
snapxo verify ./output --hash
```

Worth doing after moving the archive to another drive, and once in a while
against bit rot. `--update` accepts the current state as the new baseline, and
`--checksums` writes the baseline during a normal run.

### Merge several output folders

```bash
snapxo merge ./out-2024 ./out-2026 -o ./merged

# Or point at a folder that contains them all
snapxo merge ./all-exports -o ./merged

# Instant merge without extra disk space, then drop the originals
snapxo merge ./all-exports -o ./merged --hardlink --delete-sources
```

Duplicates are removed by content hash, everything is renumbered
chronologically, and the pages are rebuilt from the combined JSON data. Media is
copied, never re-encoded. `--hardlink` is instant and free but works within one
drive only, and the merged files stay physically identical to the originals.
`--delete-sources` removes the inputs, after re-hashing every merged file and
asking.

Every input folder is checked against its manifest first, and against its
checksums where they exist. A damaged file stops the merge. `--no-verify` takes
those files along instead, marked in the manifest, in `_meta/integrity.json`, on
the gallery tile and at the attachment in the conversation, and `--skip-damaged`
leaves them out. If another export holds the same file intact, the intact copy
wins. `--delete-sources` cannot be combined with `--no-verify`.

## Output Structure

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
│   ├── thumbs/              Preview images for the gallery and the chats
│   ├── json/
│   └── html/
├── conversations/           Per-contact chat files
│   ├── john-doe.html
│   ├── john-doe.pdf
│   └── group_my-group-chat.html
├── index.html               Media gallery
├── index.pdf
├── chats.html               Chat overview with search
├── stats.html               Statistics overview
├── stats.pdf
└── map.html                 Interactive Snap Map
```

## Flags

### Input and output
| Flag | Description |
|------|-------------|
| `INPUT...` | One or more ZIPs, a folder containing ZIPs, or an already extracted export directory |
| `-o, --output PATH` | Directory the archive is written to, created if it doesn't exist. Required except with `--info` or `--dry-run` |
| `-y, --yes` | Organize everything without asking |
| `--info` | Only show what the export contains, then exit |
| `--dry-run` | Show what would happen, without writing anything |

### Filter (what to process)
| Flag | Description |
|------|-------------|
| `--only-media` | Only media (Memories + chat media + voice) |
| `--only-memories` | Only Memories |
| `--only-chat-media` | Only chat media |
| `--only-voice` | Only voice messages |
| `--only-photos` | Only photos |
| `--only-videos` | Only videos |
| `--only-conversations` | Only conversations |
| `--only-stats` | Only `stats.html` |
| `--only-map` | Only `map.html` |
| `--since YYYY-MM-DD` | Only media and messages from this day on, inclusive |
| `--until YYYY-MM-DD` | Only media and messages up to this day, inclusive |

### Skip (what NOT to do)
| Flag | Description |
|------|-------------|
| `--no-encode` | Don't encode videos to H.265 |
| `--no-overlay` | Don't burn overlays onto media |
| `--no-exif` | Don't write EXIF/GPS into images |
| `--no-dedup` | Don't remove duplicate media |
| `--no-index` | Don't generate `index.html` (media gallery) |
| `--no-conversations` | Don't generate conversations |
| `--no-stats` | Don't generate `stats.html` |
| `--no-map` | Don't generate `map.html` |
| `--no-meta` | Don't copy the raw JSON/HTML export to `_meta/` |

### Encoding
| Flag | Description |
|------|-------------|
| `--no-hwaccel` | Force software encoding (no QSV/NVENC) |
| `--crf INT` | Video quality, lower is better, 0-51 (default: 23) |
| `--ffmpeg-path PATH` | Path to the ffmpeg binary (default: `ffmpeg`) |
| `--ffprobe-path PATH` | Path to the ffprobe binary (default: `ffprobe`) |

### Output Format
| Flag | Description |
|------|-------------|
| `--folder-structure [year\|year-month]` | One folder per year, or one per month (default: year) |
| `--conversation-format [html\|pdf]` | Write conversations as HTML pages or PDFs (default: html) |
| `--index-format [html\|pdf]` | Also render the media gallery to `index.pdf` (default: html) |
| `--stats-format [html\|pdf]` | Also render the statistics to `stats.pdf` (default: html) |

### Conversations and stats
| Flag | Description |
|------|-------------|
| `--conversations-for NAME,NAME` | Only these contacts, by the name Snapchat exported |
| `--conversations-min-messages INT` | Skip conversations with fewer messages (default: 1) |
| `--stats-only-categories CAT,CAT` | Only these stats categories, by their JSON file name (e.g. `account,friends`) |

### System
| Flag | Description |
|------|-------------|
| `--resume / --no-resume` | Pick up where an interrupted run left off (default: resume), see [Resuming](#resuming) |
| `-v, --verbose` | Print every file as it is processed. Without it each step only reports its totals |
| `--clean` | Delete the bulky raw HTML export (keeps `manifest.json` and `_meta/json/`, which `merge` needs) |
| `--checksums` | Fingerprint the finished archive for later `snapxo verify` runs |
| `--version` | Print the version and exit |
| `--help` | Show all options and exit |

### Merge
| Flag | Description |
|------|-------------|
| `FOLDERS...` | Two or more output folders, or one parent folder containing them |
| `-o, --output PATH` | Target directory for the merged export. Required except with `--dry-run` |
| `--hardlink` | Link files instead of copying (same drive only, no extra space) |
| `--delete-sources` | Delete the input folders after a verified merge |
| `-y, --yes` | Don't ask before deleting the input folders |
| `--folder-structure [year\|year-month]` | One folder per year, or one per month (default: year) |
| `--conversation-format [html\|pdf]` | Rebuild conversations as HTML pages or PDFs (default: html) |
| `--index-format [html\|pdf]` | Also render the media gallery to `index.pdf` (default: html) |
| `--verify / --no-verify` | Check the input folders against their manifests first (default: verify) |
| `--skip-damaged` | With `--no-verify`: leave damaged files out instead of taking them along marked |
| `--dry-run` | Show what would happen, without writing anything |

### Verify
| Flag | Description |
|------|-------------|
| `FOLDERS...` | One or more finished output folders |
| `--hash` | Read every file and compare it to the stored checksums |
| `--update` | Write the current state as the new baseline |

### Resuming

Encoding a large export can take hours, so an interrupted run does not start
over. SnapXO writes `.snaporganizer_checkpoint.json` into the output folder
while it works and picks up there when the same command runs again:

```
Resuming from checkpoint (1 steps, 14 files already done)
```

Encoded videos are not encoded twice, overlays are not burned on top of each
other, and organized files are not overwritten with their originals. The
checkpoint stores a fingerprint of the input, the output folder and every flag
that changes what gets produced, so changing any of them starts fresh, as does
`--no-resume`. A completed run deletes it.

### Stickers

Snapchat exports sticker metadata in `custom_sticker.json` but none of the PNG
files, and `STICKER` messages carry no sticker reference. There is nothing to
export, which is why 1.1.0 dropped the step.

## Privacy

SnapXO runs entirely on your machine, on the export you downloaded yourself, and
makes no network requests. The browser used for PDF export is put into offline
mode, so it cannot reach the network even if a page asked it to.

The one exception is `map.html`: when *you* open it, it loads its map library and
map tiles from the internet. Generating it does not.

> **Not affiliated with Snap Inc.**
> This is an independent, unofficial open-source tool. It is not created,
> endorsed, sponsored or supported by Snap Inc., and has no connection to
> Snapchat, Snap Inc. or any of its products. "Snapchat" and "Snap" are
> trademarks of Snap Inc., used here only to describe what this tool reads.
> SnapXO works purely offline on a data export you requested and downloaded
> yourself. This tool never logs into an account and never contacts Snapchat.

## License

GPL-3.0
