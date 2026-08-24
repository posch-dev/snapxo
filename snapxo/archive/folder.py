# _meta, a year folder and a folder of archives all lead to the right place.

from pathlib import Path

from rich.console import Console

console = Console()

# Deep enough for every folder SnapXO creates, shallow enough that a mistyped
# path cannot wander off across the disk.
LEVELS_UP = 3
LEVELS_DOWN = 2
FOLDER_BUDGET = 30

# An archive never holds another archive, and these are its own subfolders.
OWN_SUBFOLDERS = {"_meta", "_overlays", "conversations", "pdf", "thumbs", "spreadsheet"}

MEDIA_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif",
                  ".mp4", ".mov", ".mp3", ".m4a", ".heic"}


def _year_folder_with_media(path: Path) -> bool:
    try:
        entries = list(path.iterdir())
    except OSError:
        return False
    for entry in entries:
        if not entry.is_dir() or not entry.name[:4].isdigit():
            continue
        try:
            if any(f.suffix.lower() in MEDIA_SUFFIXES for f in entry.iterdir() if f.is_file()):
                return True
        except OSError:
            continue
    return False


def is_archive(path: Path) -> bool:
    if not path.is_dir():
        return False
    if (path / "_meta" / "manifest.json").is_file() or (path / "index.html").is_file():
        return True
    return _year_folder_with_media(path)


def _walk_up(start: Path) -> Path | None:
    current = start
    for _ in range(LEVELS_UP):
        parent = current.parent
        if parent == current:
            return None
        if is_archive(parent):
            return parent
        current = parent
    return None


def _walk_down(start: Path, budget: list[int]) -> list[Path]:
    found: list[Path] = []
    level = [start]
    for _ in range(LEVELS_DOWN):
        below: list[Path] = []
        for folder in level:
            try:
                children = sorted(entry for entry in folder.iterdir() if entry.is_dir())
            except OSError:
                continue
            for child in children:
                if child.name in OWN_SUBFOLDERS:
                    continue
                budget[0] -= 1
                if budget[0] < 0:
                    return found
                if is_archive(child):
                    found.append(child)
                else:
                    below.append(child)
        level = below
    return found


def find_archives(path: Path) -> list[Path]:
    if is_archive(path):
        return [path]

    # Archives below win over one above. A folder holding archives is what the
    # caller named, while the way up can wander into an unrelated ancestor that
    # only looks like an archive.
    budget = [FOLDER_BUDGET]
    found = _walk_down(path, budget)
    if budget[0] < 0:
        console.print(f"[yellow]Stopped after looking through {FOLDER_BUDGET} folders under "
                      f"{path}. Point at the archive itself, or at the folder right above "
                      f"it.[/yellow]")
        return found
    if found:
        return found

    above = _walk_up(path)
    return [above] if above else []


def _say_nothing_found(path: Path) -> None:
    console.print(f"[red]{path} is not a folder SnapXO produced, and there is none nearby. "
                  f"A folder it produced has _meta/manifest.json or index.html in it.[/red]")


def resolve_one(path: Path) -> Path | None:
    # None means the caller should stop, the reason is already on screen.
    found = find_archives(path)
    if not found:
        _say_nothing_found(path)
        return None
    if len(found) > 1:
        console.print(f"[yellow]{path} holds {len(found)} archives. Name the one you mean:[/yellow]")
        for archive in found:
            console.print(f"  {archive}")
        return None
    if found[0] != path:
        console.print(f"[dim]Using {found[0]}[/dim]")
    return found[0]


def resolve_many(paths: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        found = find_archives(path)
        if not found:
            _say_nothing_found(path)
            continue
        if len(found) > 1:
            console.print(f"  {path}: expanded to {len(found)} archives")
        for archive in found:
            key = archive.resolve()
            if key not in seen:
                seen.add(key)
                resolved.append(archive)
    return resolved
