from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from .ffmpeg import FFmpeg
from .utils import copy_timestamps

console = Console()


def _mark_done(checkpoint, entry: dict):
    if checkpoint is not None:
        checkpoint.mark_file_done("encode", f"{entry['subfolder']}/{entry['new_name']}")


def encode_videos(
    file_index: list[dict],
    ff: FFmpeg,
    overlay_burned: set[str] | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    checkpoint=None,
) -> int:
    # Encode videos to H.265, skipping already burned overlay videos. Returns the count.
    overlay_burned = overlay_burned or set()

    videos = [
        entry for entry in file_index
        if entry["type"] == "video" and entry["original_name"] not in overlay_burned
    ]
    if checkpoint is not None:
        videos = [
            entry for entry in videos
            if not checkpoint.is_file_done("encode", f"{entry['subfolder']}/{entry['new_name']}")
        ]

    if not videos:
        return 0

    encoded = 0
    skipped = 0
    total_saved_mb = 0.0

    with Progress(console=console) as progress:
        task = progress.add_task("Encoding H.265...", total=len(videos))

        for i, entry in enumerate(videos, 1):
            dest = Path(entry["dest"])
            if not dest.exists():
                skipped += 1
                progress.advance(task)
                continue

            codec = ff.get_video_codec(dest)
            if codec == "hevc":
                skipped += 1
                _mark_done(checkpoint, entry)
                progress.advance(task)
                continue

            if dry_run:
                if verbose:
                    progress.console.print(f"  [dim]Would encode {dest.name}[/dim]")
                encoded += 1
                progress.advance(task)
                continue

            tmp = dest.with_suffix(".tmp.mp4")
            size_mb = dest.stat().st_size / (1024 * 1024)

            if verbose:
                progress.console.print(
                    f"  [cyan][{i}/{len(videos)}][/cyan] {dest.name} ({size_mb:.1f} MB)"
                )
            else:
                progress.update(task, description=f"Encoding [{i}/{len(videos)}] {dest.name}")

            if ff.convert_to_h265(dest, tmp):
                new_size = tmp.stat().st_size / (1024 * 1024)
                copy_timestamps(dest, tmp)
                dest.unlink()
                tmp.rename(dest)
                encoded += 1
                saved = size_mb - new_size
                total_saved_mb += saved
                _mark_done(checkpoint, entry)
                if verbose:
                    if new_size < size_mb:
                        shrink = (1 - new_size / size_mb) * 100
                        progress.console.print(
                            f"    [green]OK[/green] {size_mb:.1f} → {new_size:.1f} MB ({shrink:.0f}% smaller)"
                        )
                    else:
                        progress.console.print(
                            f"    [green]OK[/green] {size_mb:.1f} → {new_size:.1f} MB (re-encoded for compatibility)"
                        )
            else:
                progress.console.print(f"  [red]FAILED[/red] {dest.name}")
                if tmp.exists():
                    tmp.unlink()

            progress.advance(task)

    if skipped:
        console.print(f"  Skipped {skipped} (already HEVC or missing)")
    if total_saved_mb > 0:
        console.print(f"  Saved {total_saved_mb:.0f} MB total")

    return encoded
