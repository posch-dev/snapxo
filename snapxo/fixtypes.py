from pathlib import Path

from rich.console import Console

console = Console()

# Magic bytes for common image/video types
MAGIC_MAP = [
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"RIFF", ".webp"),  # RIFF....WEBP
    (b"\x00\x00\x00\x1cftyp", ".mp4"),
    (b"\x00\x00\x00\x18ftyp", ".mp4"),
    (b"\x00\x00\x00\x20ftyp", ".mp4"),
    (b"\x00\x00\x00", ".mp4"),  # generic ftyp
]

# AVIF starts with ftyp but contains "avif" or "avis"
def _detect_type(filepath: Path) -> str | None:
    try:
        with open(filepath, "rb") as f:
            header = f.read(32)
    except OSError:
        return None

    if len(header) < 4:
        return None

    if len(header) >= 12 and header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in (b"avif", b"avis"):
            return ".avif"
        if brand in (b"isom", b"mp41", b"mp42", b"M4V ", b"qt  "):
            return ".mp4"
        if brand == b"mif1":
            return ".avif"

    # WEBP: RIFF....WEBP
    if header[:4] == b"RIFF" and len(header) >= 12 and header[8:12] == b"WEBP":
        return ".webp"

    for magic, ext in MAGIC_MAP:
        if header[:len(magic)] == magic:
            return ext

    return None


def fix_unknown_files(files: list[Path], verbose: bool = False) -> dict[Path, Path]:
    # Rename .unknown files to their actual type. Returns {old_path: new_path}.
    unknown = [f for f in files if f.suffix.lower() == ".unknown"]

    renamed = {}
    for i, f in enumerate(unknown, 1):
        detected = _detect_type(f)
        if verbose:
            console.print(f"  [cyan][{i}/{len(unknown)}][/cyan] {f.name}")
        if detected:
            new_path = f.with_suffix(detected)
            f.rename(new_path)
            renamed[f] = new_path
            if verbose:
                console.print(f"    [green]OK[/green] → {new_path.name}")
        elif verbose:
            console.print("    [yellow]SKIPPED[/yellow] type not recognized")
    return renamed
