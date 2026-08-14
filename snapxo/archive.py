# Everything that happens to a ZIP before its contents can be trusted: size checks
# up front, then an extraction that refuses to write outside the target directory.

import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

GIB = 1024 ** 3

# A Snapchat export is almost entirely media that is already compressed, so its
# ratio sits around 1. Both limits have to be exceeded before a ZIP is refused,
# which keeps a small but highly compressible archive out of the trap.
MAX_RATIO = 50
RATIO_MIN_UNCOMPRESSED = 1 * GIB

# Extraction needs the full payload, plus room for the output that follows.
SPACE_MARGIN = 1.1


def zip_payload(zip_path: Path) -> tuple[int, int]:
    # Returns (uncompressed, compressed) in bytes, read from the central directory.
    uncompressed = 0
    compressed = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            uncompressed += info.file_size
            compressed += info.compress_size
    return uncompressed, compressed


def looks_like_zip_bomb(uncompressed: int, compressed: int) -> bool:
    if uncompressed < RATIO_MIN_UNCOMPRESSED:
        return False
    if compressed <= 0:
        return True
    return (uncompressed / compressed) > MAX_RATIO


def free_space(path: Path) -> int:
    # Falls back to the nearest existing parent, the target itself may not exist yet.
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        return shutil.disk_usage(str(probe)).free
    except OSError:
        return -1


def _is_unsafe_name(name: str) -> str | None:
    # Returns the reason the entry is refused, or None if it is fine. Checked against
    # both path flavours because a ZIP written on Windows can carry "C:\" or "\" and
    # PurePosixPath would read those as an ordinary file name.
    if not name or name in (".", ".."):
        return "empty name"
    if name.startswith("/") or name.startswith("\\"):
        return "absolute path"
    if PureWindowsPath(name).is_absolute() or PureWindowsPath(name).drive:
        return "absolute path"
    parts = PurePosixPath(name.replace("\\", "/")).parts
    if ".." in parts:
        return "path traversal"
    return None


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    # Unix mode lives in the upper 16 bits of external_attr, and only for archives
    # written on Unix. A symlink could point anywhere, so it is never followed.
    return stat.S_ISLNK(info.external_attr >> 16)


def safe_extract(zip_path: Path, dest: Path, verbose: bool = False) -> tuple[int, list[dict]]:
    # Extracts into `dest` and returns (files written, problems). Entries that would
    # land outside `dest` are refused, and an entry with a broken CRC costs that one
    # file instead of the whole run.
    dest_root = dest.resolve()
    written = 0
    problems: list[dict] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename

            reason = _is_unsafe_name(name)
            if reason:
                problems.append({"zip": zip_path.name, "entry": name, "reason": reason})
                continue
            if _is_symlink(info):
                problems.append({"zip": zip_path.name, "entry": name, "reason": "symlink"})
                continue

            target = (dest_root / name).resolve()
            if target != dest_root and dest_root not in target.parents:
                problems.append({"zip": zip_path.name, "entry": name, "reason": "path traversal"})
                continue

            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with zf.open(info, "r") as src, open(target, "wb") as out:
                    # Reading through ZipFile.open verifies the CRC as it goes
                    shutil.copyfileobj(src, out)
                written += 1
            except (zipfile.BadZipFile, OSError, EOFError) as e:
                problems.append({"zip": zip_path.name, "entry": name, "reason": f"unreadable ({e})"})
                target.unlink(missing_ok=True)

    return written, problems
