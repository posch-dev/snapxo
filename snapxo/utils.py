import hashlib
import os
import re
import shutil
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
VIDEO_EXTS = {".mp4", ".mov"}
AUDIO_EXTS = {".mp3", ".aac", ".m4a"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS

UUID_RE = re.compile(r"[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}")
DATE_PREFIX_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_(.+)")


def file_hash(filepath: Path, chunk_size: int = 65536) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def copy_timestamps(src: Path, dst: Path):
    stat = os.stat(src)
    os.utime(dst, (stat.st_atime, stat.st_mtime))


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def extract_date_from_filename(name: str) -> str | None:
    m = DATE_PREFIX_RE.match(name)
    return m.group(1) if m else None


def extract_uuid_from_name(name: str) -> str | None:
    m = UUID_RE.search(name)
    return m.group(0) if m else None


def extract_media_id(name: str) -> str | None:
    # Media ID from a chat_media filename. Files are named <date>_<media id><ext> and
    # that id is what chat_history.json lists under "Media IDs":
    #   2026-07-20_b~EiASFXhhbXBsZW1lZGlhaWRleGFtcGwyAXlIAlAEYAE.jpg
    stem = name.rsplit(".", 1)[0] if "." in name else name
    m = DATE_PREFIX_RE.match(stem)
    return m.group(2) if m else None


def find_executable(name: str, extra_paths: list[str] | None = None) -> str | None:
    # Locate an external tool on PATH, falling back to well known locations.
    found = shutil.which(name)
    if found:
        return found
    for candidate in extra_paths or []:
        if Path(candidate).is_file():
            return candidate
    return None


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', name)
