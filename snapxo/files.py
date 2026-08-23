import hashlib
import os
from pathlib import Path


def file_hash(filepath: Path, chunk_size: int = 65536) -> str:
    digest = hashlib.md5()
    with open(filepath, "rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def copy_timestamps(src: Path, dst: Path):
    stat = os.stat(src)
    os.utime(dst, (stat.st_atime, stat.st_mtime))


def format_size(size) -> str:
    if not isinstance(size, int):
        return "unknown"
    if size < 1024:
        return f"{size} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"
    if size < 1024 ** 3:
        return f"{size / 1024 ** 2:.1f} MB"
    return f"{size / 1024 ** 3:.2f} GB"
