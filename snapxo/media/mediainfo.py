# Measured once and kept in the manifest, because ffprobe costs a process per file.

from pathlib import Path

from PIL import Image
from rich.console import Console

console = Console()

PROBED_TYPES = ("video", "audio")


def image_info(path: Path) -> dict:
    try:
        with Image.open(path) as picture:
            return {"width": picture.width, "height": picture.height,
                    "codec": (picture.format or "").lower()}
    except Exception:
        return {}


def measure(entry: dict, ff=None) -> dict:
    source = entry.get("dest")
    path = Path(source) if source else None
    if path is None or not path.is_file():
        return {}
    if entry.get("type") == "image":
        return image_info(path)
    if entry.get("type") in PROBED_TYPES and ff is not None:
        return ff.probe(path)
    return {}


def attach(file_index: list[dict], ff=None, verbose: bool = False) -> int:
    # Leaves what is already there, so a rebuild on a measured archive is free.
    measured = 0
    for entry in file_index:
        if entry.get("media"):
            continue
        info = measure(entry, ff)
        if info:
            entry["media"] = info
            measured += 1
            if verbose:
                console.print(f"  [dim]{entry.get('new_name', '')}: {describe(info)}[/dim]")
    if measured:
        console.print(f"  Measured {measured} files")
    return measured


def human_duration(seconds) -> str:
    try:
        total = int(round(float(seconds)))
    except (TypeError, ValueError):
        return ""
    if total >= 3600:
        return f"{total // 3600}:{total % 3600 // 60:02d}:{total % 60:02d}"
    return f"{total // 60}:{total % 60:02d}"


def human_bitrate(bits) -> str:
    try:
        value = int(bits)
    except (TypeError, ValueError):
        return ""
    return f"{value // 1000} kbit/s" if value else ""


def describe(info: dict) -> str:
    parts = []
    if info.get("width") and info.get("height"):
        parts.append(f'{info["width"]}x{info["height"]}')
    if info.get("codec"):
        parts.append(str(info["codec"]))
    if info.get("duration"):
        parts.append(human_duration(info["duration"]))
    if info.get("bitrate"):
        parts.append(human_bitrate(info["bitrate"]))
    return ", ".join(part for part in parts if part)
