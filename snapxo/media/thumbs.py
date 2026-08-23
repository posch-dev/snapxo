from pathlib import Path

from PIL import Image
from rich.console import Console

console = Console()

THUMB_DIR = "_meta/thumbs"
THUMB_HEIGHT = 320
JPEG_QUALITY = 80

# A PDF prints far larger than a chat bubble, where 320 px looks mushy. 1280 px
# beats what a 300 dpi page resolves. Only `snapxo pdf` asks for these.
MEDIUM_DIR = "_meta/thumbs/medium"
MEDIUM_SIZE = 1280
MEDIUM_QUALITY = 85


def thumb_dir(output_dir: Path) -> Path:
    return output_dir / "_meta" / "thumbs"


def medium_dir(output_dir: Path) -> Path:
    return thumb_dir(output_dir) / "medium"


def _thumb_name(entry: dict) -> str:
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
    with_medium: bool = False,
) -> dict[int, str]:
    if dry_run:
        return {}

    target_dir = thumb_dir(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    mid_dir = medium_dir(output_dir)
    if with_medium:
        mid_dir.mkdir(parents=True, exist_ok=True)

    thumbs: dict[int, str] = {}
    built = 0
    reused = 0
    failed = 0
    mediums = 0

    for i, entry in enumerate(file_index):
        ftype = entry.get("type")
        if ftype not in ("image", "video"):
            continue

        target = target_dir / _thumb_name(entry)
        rel = f"{THUMB_DIR}/{target.name}"
        source = _source_path(entry, output_dir)

        if target.is_file() and target.stat().st_size > 0:
            thumbs[i] = rel
            entry["thumb"] = rel
            reused += 1
        elif not source.is_file():
            continue
        else:
            ok = False
            if ftype == "image":
                ok = _image_thumb(source, target)
            elif ff is not None:
                ok = ff.grab_frame(source, target, height=THUMB_HEIGHT)

            if ok:
                thumbs[i] = rel
                # The conversations reach their media through the media map and
                # never see this index.
                entry["thumb"] = rel
                built += 1
                if verbose:
                    console.print(f"  [cyan][{built}][/cyan] {target.name}")
            else:
                failed += 1

        if with_medium and ftype == "image" and _attach_medium(entry, source, mid_dir):
            mediums += 1

    if built or reused:
        note = f"  Thumbnails: {built} new, {reused} reused"
        if mediums:
            note += f", {mediums} in print size"
        if failed:
            note += f", {failed} without preview"
        console.print(note)

    return thumbs


def _attach_medium(entry: dict, source: Path, target_dir: Path) -> bool:
    # True only for a newly written copy, so the summary counts the actual work.
    target = target_dir / _thumb_name(entry)
    rel = f"{MEDIUM_DIR}/{target.name}"

    if target.is_file() and target.stat().st_size > 0:
        entry["medium"] = rel
        return False
    if not source.is_file():
        return False
    if not _medium_image(source, target):
        return False

    entry["medium"] = rel
    return True


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


def _medium_image(source: Path, target: Path) -> bool:
    try:
        with Image.open(source) as img:
            # Already small enough, a copy would only cost space and quality.
            if max(img.width, img.height) <= MEDIUM_SIZE:
                return False
            img.draft("RGB", (MEDIUM_SIZE, MEDIUM_SIZE))
            img = img.convert("RGB")
            img.thumbnail((MEDIUM_SIZE, MEDIUM_SIZE), Image.LANCZOS)
            img.save(target, "JPEG", quality=MEDIUM_QUALITY, optimize=True)
        return True
    except Exception:
        target.unlink(missing_ok=True)
        return False
