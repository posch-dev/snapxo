from pathlib import Path

from rich.console import Console

from ..app.shell import generate_app
from ..archive.manifest import build_media_id_map
from ..facts.mediacounts import summarize_file_index
from ..media.mediainfo import attach as attach_media_info
from ..media.thumbs import build_thumbnails
from ..tools.ffmpeg import FFmpeg
from .snapmap import generate_map_html

console = Console()


def generate_site(
    output_dir: Path,
    json_data: dict,
    file_index: list[dict],
    overlay_count: int = 0,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    # Without ffmpeg videos get no preview, which is not worth failing over.
    ff = FFmpeg()
    usable = ff if ff.check() else None
    if not dry_run:
        # Older archives were written before this was measured.
        attach_media_info(file_index, ff=usable, verbose=verbose)
    thumbs = build_thumbnails(file_index, output_dir, ff=usable,
                              dry_run=dry_run, verbose=verbose)

    if json_data:
        if generate_map_html(json_data, output_dir, file_index=file_index, dry_run=dry_run):
            console.print("Generated map.html")
    else:
        console.print("[yellow]No JSON data available, so no chats, statistics or map[/yellow]")

    generate_app(output_dir, json_data, file_index,
                 summarize_file_index(file_index, overlay_count), thumbs=thumbs,
                 media_map=build_media_id_map(file_index), dry_run=dry_run)
