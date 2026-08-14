# Preview images shared by index.html and index.pdf.

from pathlib import Path

from PIL import Image
from rich.console import Console

console = Console()

THUMB_DIR = "_meta/thumbs"
THUMB_HEIGHT = 320
JPEG_QUALITY = 80


def thumb_dir(output_dir: Path) -> Path:
    return output_dir / "_meta" / "thumbs"


def _thumb_name(entry: dict) -> str:
    # Flat directory, so the subfolder goes into the name to keep it unique.
    subfolder = entry.get("subfolder") or entry.get("year") or "unknown"
    stem = Path(entry.get("new_name", "")).stem
    return f"{subfolder}__{stem}.jpg"


def _source_path(entry: dict, output_dir: Path) -> Path:
    dest = entry.get("dest")
    if dest:
        return Path(dest)
    subfolder = entry.get("subfolder") or entry.get("year") or "unknown"
    return output_dir / subfolder / entry.get("new_name", "")


def build_thumbnails(
    file_index: list[dict],
    output_dir: Path,
    ff=None,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[int, str]:
    # Returns {index in file_index: path relative to the output folder}.
    if dry_run:
        return {}

    target_dir = thumb_dir(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    thumbs: dict[int, str] = {}
    built = 0
    reused = 0
    failed = 0

    for i, entry in enumerate(file_index):
        ftype = entry.get("type")
        if ftype not in ("image", "video"):
            continue

        target = target_dir / _thumb_name(entry)
        rel = f"{THUMB_DIR}/{target.name}"

        if target.is_file() and target.stat().st_size > 0:
            thumbs[i] = rel
            reused += 1
            continue

        source = _source_path(entry, output_dir)
        if not source.is_file():
            continue

        ok = False
        if ftype == "image":
            ok = _image_thumb(source, target)
        elif ff is not None:
            ok = ff.grab_frame(source, target, height=THUMB_HEIGHT)

        if ok:
            thumbs[i] = rel
            built += 1
            if verbose:
                console.print(f"  [cyan][{built}][/cyan] {target.name}")
        else:
            failed += 1

    if built or reused:
        note = f"  Thumbnails: {built} new, {reused} reused"
        if failed:
            note += f", {failed} without preview"
        console.print(note)

    return thumbs


def _image_thumb(source: Path, target: Path) -> bool:
    try:
        with Image.open(source) as img:
            img.draft("RGB", (img.width // 2, img.height // 2))  # decode less for large JPEGs
            img = img.convert("RGB")
            img.thumbnail((THUMB_HEIGHT * 2, THUMB_HEIGHT), Image.LANCZOS)
            img.save(target, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except Exception:
        target.unlink(missing_ok=True)
        return False
