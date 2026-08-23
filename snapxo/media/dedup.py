from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from ..files import file_hash
from ..filetypes import MEDIA_EXTS

console = Console()


def find_duplicates(files: list[Path]) -> list[tuple[Path, list[Path]]]:
    hashes: dict[str, list[Path]] = defaultdict(list)

    with Progress(console=console) as progress:
        task = progress.add_task("Hashing files...", total=len(files))
        for f in files:
            h = file_hash(f)
            hashes[h].append(f)
            progress.advance(task)

    duplicates = []
    for paths in hashes.values():
        if len(paths) > 1:
            paths.sort(key=lambda p: p.name)
            duplicates.append((paths[0], paths[1:]))

    return duplicates


def remove_duplicates(files: list[Path], dry_run: bool = False,
                      verbose: bool = False) -> tuple[int, int, dict[str, str]]:
    # The alias maps each removed path to the one it duplicated, so callers can
    # still resolve media that is now gone.
    dupes = find_duplicates(files)
    total = sum(len(dups) for _, dups in dupes)

    removed = 0
    freed = 0
    alias: dict[str, str] = {}
    for keep, dups in dupes:
        for dup in dups:
            size = dup.stat().st_size
            removed += 1
            freed += size
            if verbose:
                console.print(
                    f"  [cyan][{removed}/{total}][/cyan] {dup.parent.name}/{dup.name} ({size / (1024*1024):.1f} MB)"
                )
                console.print(f"    [dim]same as {keep.parent.name}/{keep.name}[/dim]")
            if not dry_run:
                dup.unlink()
            alias[str(dup)] = str(keep)

    return removed, freed, alias


def collect_media_files(directory: Path) -> list[Path]:
    files = []
    for f in sorted(directory.rglob("*")):
        if f.is_file() and f.suffix.lower() in MEDIA_EXTS and not f.name.startswith("."):
            files.append(f)
    return files
