# Changelog

All notable changes to SnapXO are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the version numbers
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
