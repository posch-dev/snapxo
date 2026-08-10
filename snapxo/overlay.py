import shutil
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from .ffmpeg import FFmpeg
from .scanner import MediaFile
from .utils import copy_timestamps

console = Console()


def match_overlays(
    main_files: list[MediaFile],
    overlays: list[MediaFile],
) -> tuple[list[tuple[MediaFile, MediaFile]], list[MediaFile]]:
    # Match overlays to main files by date and UUID. Returns (matched, unmatched).
    uuid_lookup: dict[tuple[str, str], MediaFile] = {}
    for mf in main_files:
        if mf.uuid:
            uuid_lookup[(mf.date, mf.uuid)] = mf

    matched = []
    unmatched = []

    for ov in overlays:
        if ov.uuid:
            key = (ov.date, ov.uuid)
            if key in uuid_lookup:
                matched.append((uuid_lookup[key], ov))
                continue
        unmatched.append(ov)

    return matched, unmatched


def burn_overlays(
    matched: list[tuple[MediaFile, MediaFile]],
    file_index: list[dict],
    output_dir: Path,
    ff: FFmpeg,
    dry_run: bool = False,
    verbose: bool = False,
    checkpoint=None,
) -> int:
    # Burn overlays into their matched files in place. Returns the count burned.
    # Build lookup: original_name -> dest path from file_index
    name_to_dest: dict[str, Path] = {}
    for entry in file_index:
        name_to_dest[entry["original_name"]] = Path(entry["dest"])

    # Burning twice would stack the overlay on top of itself.
    if checkpoint is not None:
        matched = [
            pair for pair in matched
            if not checkpoint.is_file_done("overlay", pair[0].original_name)
        ]

    if not matched:
        return 0

    burned = 0
    skipped = 0
    failed = 0

    with Progress(console=console) as progress:
        task = progress.add_task("Burning overlays...", total=len(matched))

        for i, (main_file, overlay) in enumerate(matched, 1):
            dest = name_to_dest.get(main_file.original_name)
            if not dest or not dest.exists():
                skipped += 1
                progress.advance(task)
                continue

            if dry_run:
                if verbose:
                    progress.console.print(f"  [dim]Would burn overlay onto {dest.name}[/dim]")
                burned += 1
                progress.advance(task)
                continue

            tmp = dest.with_suffix(".tmp" + dest.suffix)
            size_mb = dest.stat().st_size / (1024 * 1024)

            if verbose:
                progress.console.print(f"  [cyan][{i}/{len(matched)}][/cyan] {dest.name} ({size_mb:.1f} MB)")
            else:
                progress.update(task, description=f"Burning overlays [{i}/{len(matched)}] {dest.name}")

            if main_file.is_video:
                success = ff.burn_overlay_video_h265(dest, overlay.path, tmp)
            else:
                success = ff.burn_overlay_image(dest, overlay.path, tmp)

            if success:
                new_size = tmp.stat().st_size / (1024 * 1024)
                copy_timestamps(dest, tmp)
                dest.unlink()
                tmp.rename(dest)
                burned += 1
                if checkpoint is not None:
                    checkpoint.mark_file_done("overlay", main_file.original_name)
                if verbose:
                    progress.console.print(f"    [green]OK[/green] {size_mb:.1f} → {new_size:.1f} MB")
            else:
                failed += 1
                progress.console.print(f"  [red]FAILED[/red] {dest.name}")
                if tmp.exists():
                    tmp.unlink()

            progress.advance(task)

    if skipped:
        console.print(f"  Skipped {skipped} (target file missing)")
    if failed:
        console.print(f"  {failed} failed")

    return burned


def copy_unmatched_overlays(unmatched: list[MediaFile], output_dir: Path, dry_run: bool = False):
    # Copy overlays that matched nothing to _overlays/.
    if not unmatched:
        return

    overlays_dir = output_dir / "_overlays"
    if not dry_run:
        overlays_dir.mkdir(parents=True, exist_ok=True)

    for ov in unmatched:
        dest = overlays_dir / ov.original_name
        if not dry_run:
            shutil.copy2(str(ov.path), str(dest))
