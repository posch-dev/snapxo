# Changelog

All notable changes to SnapXO are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the version numbers
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
