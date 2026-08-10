> **Not affiliated with Snap Inc.**
> This is an independent, unofficial open-source tool. It is not created,
> endorsed, sponsored or supported by Snap Inc., and has no connection to
> Snapchat, Snap Inc. or any of its products. "Snapchat" and "Snap" are
> trademarks of Snap Inc., used here only to describe what this tool reads.
> SnapXO works purely offline on a data export you requested and downloaded
> yourself. This tool never logs into an account and never contacts Snapchat.

# SnapXO (Snapchat Export Organizer)

Turn a Snapchat data export into a clean, browsable archive
with sorted media, efficient video encoding, GPS metadata, chat
histories, statistics and an interactive map.

>*XO as in the prehistoric kiss emoji hihi^^
>with **X** for eXport and **O** for Organizer.* 

```bash
pip install snapxo
```

## Features

- **Media Organization**: Sort memories + chat media into structured folders with clean filenames (`2026-05-08_0444.mp4`)
- **H.265 Encoding**: Re-encode videos with Intel QSV hardware acceleration (auto-fallback to libx265)
- **Overlay Burning**: Burn Snapchat overlays onto photos/videos
- **GPS/EXIF**: Write GPS coordinates from `memories_history.json` into image EXIF data
- **Duplicate Removal**: MD5-based deduplication before encoding
- **Voice Messages**: Detect audio-only MP4s and convert to MP3
- **Conversations**: Per-contact chat pages with chat messages, photos, videos and voice messages
- **Statistics**: Overview page with cards + detail tables
- **Snap Map**: Interactive map with route, timeline slider, playback animation and Locations of each Snapchat Memories
- **Media Gallery**: `index.html` with navigation, type filters, thumbnails and a details panel per file (like Snapchat's Memories Tab)
- **Merge**: Combine several exports into one (deduplicated and renumbered, without re-encoding)
- **PDF Export**: Convert conversations and stats to PDF
- **Resume**: An interrupted run picks up where it stopped instead of copying and encoding everything again

Runs on Windows, Linux and macOS.

## Installation

```bash
pip install snapxo
```

If something is missing, SnapXO says so and prints the
install command for the system you are on.

### For PDF export

```bash
playwright install chromium
```

This downloads the browser that
renders the PDFs. On Linux it may also need system libraries, which
`playwright install-deps chromium` takes care of.

### For video processing

**ffmpeg and ffprobe** are needed for video encoding, overlay burning and voice
conversion. They are native programs, so pip cannot install them:

| System | Command |
|--------|---------|
| Windows | `winget install Gyan.FFmpeg` |
| Debian/Ubuntu | `sudo apt install ffmpeg` |
| Fedora | `sudo dnf install ffmpeg` |
| Arch | `sudo pacman -S ffmpeg` |
| macOS | `brew install ffmpeg` |

If you cannot install one system-wide, `pip install "snapxo[ffmpeg]"` pulls in
`static-ffmpeg`, which provides both binaries and is picked up automatically.
Those builds normally don't ship with hardware encoders like Intel QSV, so encoding falls
back to software and gets considerably slower. Choose a system-wide ffmpeg installation if possible.

## Usage

```bash
# Basic: organize everything from ZIP(s)
snapxo mydata.zip -o ./output -y

# Multiple ZIPs (Snapchat splits large exports)
snapxo export1.zip export2.zip -o ./output -y

# A folder full of ZIPs, anything that isn't a Snapchat export is ignored
snapxo ~/Downloads -o ./output -y

# Already extracted directory
snapxo ./extracted-export/ -o ./output -y

# Just show what's in the export
snapxo mydata.zip -o ./output --info

# Dry run (show what would happen)
snapxo mydata.zip -o ./output --dry-run
```

`-o` is required. The directory is created if it doesn't exist and reused if it does. `--info` and
`--dry-run` still want the flag, but neither one creates the folder.

Also available as `python -m snapxo ...`.

Passing a ZIP explicitly and passing a folder behave differently on purpose: a
named ZIP that isn't a Snapchat export is an error, while ZIPs discovered by
scanning a folder are silently skipped.

### Custom ffmpeg path (e.g. WinGet install)

ffmpeg is located on `PATH`; you can also point at it explicitly with
`--ffmpeg-path` and `--ffprobe-path`.

```bash
snapxo mydata.zip -o ./output -y \
  --ffmpeg-path "C:\...\ffmpeg.exe" \
  --ffprobe-path "C:\...\ffprobe.exe"
```

### Re-generate specific outputs from an existing export

The input here is the `_meta/json` folder of the finished export, not the export
folder itself.

```bash
# Re-generate conversations as PDF
snapxo ./output/_meta/json -o ./output -y --only-conversations --conversation-format pdf

# Re-generate stats
snapxo ./output/_meta/json -o ./output -y --only-stats

# Re-generate map
snapxo ./output/_meta/json -o ./output -y --only-map

# Everything that can be a PDF, in one go: conversations + stats
snapxo ./output/_meta/json -o ./output -y \
  --only-conversations --only-stats --conversation-format pdf
```

### Merging several output folders

```bash
# Merge two or more finished exports
snapxo merge ./out-2024 ./out-2026 -o ./merged

# Or point at a folder that contains them all
snapxo merge ./all-exports -o ./merged

# Instant merge without extra disk space, then drop the originals
snapxo merge ./all-exports -o ./merged --hardlink --delete-sources
```

Duplicates are removed by content hash, everything is renumbered
chronologically, and conversations, stats, map and index are rebuilt from the
combined JSON data. Media is copied, never re-encoded.

`--hardlink` links instead of copying: instant and free, but only works within
one drive, and the merged files stay physically identical to the originals, so
re-encoding the merged folder later would change the source folders too.
`--delete-sources` removes the input folders, but only after re-hashing every
merged file and asking for confirmation.

## Output Structure

```
output/
├── 2022/                    folders with organized media
├── 2023/
├── ...
├── 2026/
│   ├── 2026-05-08_0444.mp4  H.265 encoded, with EXIF/GPS
│   ├── 2026-05-08_0445.jpg
│   ├── 2026-05-08_0446.mp3
│   └── ...
├── _stickers/               Custom sticker PNGs (usually empty)
├── _overlays/               Overlays that matched no media
├── _meta/                   Raw JSON + HTML from export
│   ├── manifest.json        What each file is and where it came from
│   ├── json/
│   └── html/
├── conversations/           Per-contact chat files
│   ├── john-doe.html
│   ├── john-doe.pdf
│   ├── max_mustermann.html
│   ├── group_my-group-chat.html
│   └── ...
├── index.html               Media gallery
├── stats.html               Statistics overview
├── stats.pdf
└── map.html                 Interactive Snap Map
```

## Flags

### Input and output
| Flag | Description |
|------|-------------|
| `INPUT...` | One or more ZIPs, a folder containing ZIPs, or an already extracted export directory |
| `-o, --output PATH` | **Required.** Directory the archive is written to, created if it doesn't exist |

### Mode
| Flag | Description |
|------|-------------|
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
| `--only-stickers` | Only stickers |

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
| `--no-stickers` | Don't export stickers |
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

### Conversations
| Flag | Description |
|------|-------------|
| `--conversations-for NAME,NAME` | Only these contacts, by the name Snapchat exported |
| `--conversations-min-messages INT` | Skip conversations with fewer messages (default: 1) |

### Stats
| Flag | Description |
|------|-------------|
| `--stats-only-categories CAT,CAT` | Only these stats categories, by their JSON file name (e.g. `account,friends`) |

### System
| Flag | Description |
|------|-------------|
| `--resume / --no-resume` | Pick up where an interrupted run left off (default: resume), see [Resuming](#resuming) |
| `-v, --verbose` | Print every file as it is processed. Without it each step only reports its totals |
| `--clean` | Delete the bulky raw HTML export (keeps `manifest.json` and `_meta/json/`, which `merge` needs) |
| `--version` | Print the version and exit |
| `--help` | Show all options and exit |

### Merge
| Flag | Description |
|------|-------------|
| `FOLDERS...` | Two or more output folders, or one parent folder containing them |
| `-o, --output PATH` | **Required.** Target directory for the merged export |
| `--hardlink` | Link files instead of copying (same drive only, no extra space) |
| `--delete-sources` | Delete the input folders after a verified merge |
| `-y, --yes` | Don't ask before deleting the input folders |
| `--folder-structure [year\|year-month]` | One folder per year, or one per month (default: year) |
| `--conversation-format [html\|pdf]` | Rebuild conversations as HTML pages or PDFs (default: html) |
| `--dry-run` | Show what would happen, without writing anything |

### Resuming

Encoding a large export could take hours, so an interrupted run does not start over.
While it works, SnapXO writes `.snaporganizer_checkpoint.json` into the output
folder, recording which files it has already copied, converted, burned and
encoded, and which steps are finished. Start the same command again and it picks
up there:

```
Resuming from checkpoint (1 steps, 14 files already done)
```

Videos that are already encoded are not encoded again, overlays are not burned a
second time (which would stack them on top of each other), and organized files
are not overwritten with their unprocessed originals.

The checkpoint belongs to one specific run: it stores a fingerprint of the input,
the output folder and every flag that changes what gets produced. Change any of
them and the next run ignores it and starts fresh. `--no-resume` ignores it too.

Once a run completes, the checkpoint is deleted, so a finished export never
carries one around. It also survives being killed mid-write, since it is written
to a temporary file and moved into place.

### Stickers

Snapchat exports sticker metadata in `custom_sticker.json` but does **not**
include the PNG files, so the tool reports `0 of N sticker files found`. Nothing
can be done about that.

## Privacy

SnapXO runs entirely on your machine. It reads the export ZIP you downloaded
yourself, writes files to the folder you choose, and makes no network requests.

The browser used for PDF export renders local files only and is explicitly put
into offline mode, so it cannot reach the network even if a page asked it to.

The one exception is `map.html`: when *you* open it in a browser, it loads its
map library and map tiles from the internet. Generating it does not.

## License

GPL-3.0
