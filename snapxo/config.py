from dataclasses import dataclass, field
from pathlib import Path

from .selection import Selection


@dataclass
class Config:
    inputs: list[Path] = field(default_factory=list)
    output: Path | None = None
    yes: bool = False
    info: bool = False
    dry_run: bool = False

    # Empty lists mean everything.
    media_sources: list[str] = field(default_factory=list)
    media_types: list[str] = field(default_factory=list)

    # "YYYY-MM-DD", both bounds inclusive
    since: str | None = None
    until: str | None = None

    # Skip
    no_encode: bool = False
    no_overlay: bool = False
    no_exif: bool = False
    no_dedup: bool = False
    no_meta: bool = False

    # Encoding
    software_encoding: bool = False
    crf: int = 23
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    # Output layout
    folder_structure: str = "year"
    # IANA name, empty means leave the export's UTC timestamps alone
    timezone: str = ""

    # System
    resume: bool = True
    verbose: bool = False
    keep_raw_html: bool = False
    no_checksums: bool = False

    @property
    def selection(self) -> Selection:
        return Selection(self.media_sources, self.media_types)

    def should_process_meta(self) -> bool:
        # rebuild and merge live on the raw JSON, so narrowing the media never
        # costs it. Only --no-meta drops it.
        return not self.no_meta

    def in_date_range(self, date: str | None) -> bool:
        # Undated entries are kept, dropping them would hide files over a typo.
        if not self.since and not self.until:
            return True
        if not date or len(date) < 10:
            return True
        day = date[:10]
        if self.since and day < self.since:
            return False
        if self.until and day > self.until:
            return False
        return True

    def should_encode(self) -> bool:
        return not self.no_encode and self.selection.wants_type("videos")

    def should_overlay(self) -> bool:
        return not self.no_overlay

    def should_exif(self) -> bool:
        return not self.no_exif

    def should_dedup(self) -> bool:
        return not self.no_dedup
