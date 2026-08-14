from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    inputs: list[Path] = field(default_factory=list)
    output: Path | None = None
    yes: bool = False
    info: bool = False
    dry_run: bool = False

    # Filter
    only_media: bool = False
    only_memories: bool = False
    only_chat_media: bool = False
    only_voice: bool = False
    only_photos: bool = False
    only_videos: bool = False
    only_conversations: bool = False
    only_stats: bool = False
    only_map: bool = False

    # Date range, "YYYY-MM-DD", both bounds inclusive
    since: str | None = None
    until: str | None = None

    # Skip
    no_encode: bool = False
    no_overlay: bool = False
    no_exif: bool = False
    no_dedup: bool = False
    no_index: bool = False
    no_conversations: bool = False
    no_stats: bool = False
    no_map: bool = False
    no_meta: bool = False

    # Encoding
    no_hwaccel: bool = False
    crf: int = 23
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    # Output format
    folder_structure: str = "year"
    conversation_format: str = "html"
    index_format: str = "html"
    stats_format: str = "html"

    # Conversations
    conversations_for: list[str] = field(default_factory=list)
    conversations_min_messages: int = 1

    # Stats
    stats_only_categories: list[str] = field(default_factory=list)

    # System
    resume: bool = True
    verbose: bool = False
    clean: bool = False
    checksums: bool = False

    @property
    def has_only_filter(self) -> bool:
        return any([
            self.only_media, self.only_memories, self.only_chat_media,
            self.only_voice, self.only_photos, self.only_videos,
            self.only_conversations, self.only_stats, self.only_map,
        ])

    def should_process_media(self) -> bool:
        if not self.has_only_filter:
            return True
        return any([self.only_media, self.only_memories, self.only_chat_media,
                    self.only_voice, self.only_photos, self.only_videos])

    def should_process_conversations(self) -> bool:
        if self.no_conversations:
            return False
        if not self.has_only_filter:
            return True
        return self.only_conversations

    def should_process_stats(self) -> bool:
        if self.no_stats:
            return False
        if not self.has_only_filter:
            return True
        return self.only_stats

    def should_process_map(self) -> bool:
        if self.no_map:
            return False
        if not self.has_only_filter:
            return True
        return self.only_map

    def should_process_meta(self) -> bool:
        if self.no_meta:
            return False
        if not self.has_only_filter:
            return True
        return False

    def wants_pdf(self) -> bool:
        return "pdf" in (self.conversation_format, self.index_format, self.stats_format)

    def in_date_range(self, date: str | None) -> bool:
        # `date` is the "YYYY-MM-DD" prefix used everywhere in the file index. Anything
        # without a usable date is kept, dropping it would hide files over a typo.
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
        return not self.no_encode and self.should_process_media()

    def should_overlay(self) -> bool:
        return not self.no_overlay and self.should_process_media()

    def should_exif(self) -> bool:
        return not self.no_exif and self.should_process_media()

    def should_dedup(self) -> bool:
        return not self.no_dedup and self.should_process_media()

    def should_index(self) -> bool:
        return not self.no_index and self.should_process_media()
