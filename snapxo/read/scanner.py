from dataclasses import dataclass, field
from pathlib import Path

from ..filenames import DATE_PREFIX_RE, UUID_RE
from ..filetypes import IMAGE_EXTS, VIDEO_EXTS


@dataclass
class MediaFile:
    path: Path
    date: str
    uuid: str | None
    ext: str
    source: str  # "memory" or "chat"
    original_name: str
    is_overlay: bool = False

    @property
    def is_video(self) -> bool:
        return self.ext in VIDEO_EXTS

    @property
    def is_image(self) -> bool:
        return self.ext in IMAGE_EXTS


@dataclass
class ScanResult:
    memories: list[MediaFile] = field(default_factory=list)
    overlays: list[MediaFile] = field(default_factory=list)
    chat_media: list[MediaFile] = field(default_factory=list)
    unknown_files: list[Path] = field(default_factory=list)

    @property
    def all_media(self) -> list[MediaFile]:
        return self.memories + self.chat_media


def scan_export(export_dir: Path) -> ScanResult:
    result = ScanResult()

    memories_dir = export_dir / "memories"
    if memories_dir.is_dir():
        for f in sorted(memories_dir.iterdir()):
            if not f.is_file():
                continue
            _categorize_memory_file(f, result)

    chat_dir = export_dir / "chat_media"
    if chat_dir.is_dir():
        for f in sorted(chat_dir.iterdir()):
            if not f.is_file():
                continue
            _categorize_chat_file(f, result)

    return result


def _categorize_memory_file(f: Path, result: ScanResult):
    name = f.name
    ext = f.suffix.lower()

    date_match = DATE_PREFIX_RE.match(name)
    date_str = date_match.group(1) if date_match else "unknown"

    uuid = None
    uuid_match = UUID_RE.search(name)
    if uuid_match:
        uuid = uuid_match.group(0)

    is_overlay = "overlay" in name.lower()

    mf = MediaFile(
        path=f,
        date=date_str,
        uuid=uuid,
        ext=ext,
        source="memory",
        original_name=name,
        is_overlay=is_overlay,
    )

    if is_overlay:
        result.overlays.append(mf)
    elif ext in IMAGE_EXTS or ext in VIDEO_EXTS:
        result.memories.append(mf)
    elif ext == ".unknown":
        result.unknown_files.append(f)
    else:
        result.unknown_files.append(f)


def _categorize_chat_file(f: Path, result: ScanResult):
    name = f.name
    ext = f.suffix.lower()

    date_match = DATE_PREFIX_RE.match(name)
    date_str = date_match.group(1) if date_match else "unknown"

    mf = MediaFile(
        path=f,
        date=date_str,
        uuid=None,
        ext=ext,
        source="chat",
        original_name=name,
    )

    if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
        result.chat_media.append(mf)
    elif ext == ".unknown":
        result.unknown_files.append(f)
    else:
        result.unknown_files.append(f)
