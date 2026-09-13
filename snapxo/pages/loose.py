# One page per topic, the versions you can hand on without the whole archive.

from pathlib import Path

from rich.console import Console

from ..archive.manifest import build_media_id_map, load_archive
from ..facts.mediacounts import summarize_folder
from ..media.thumbs import build_thumbnails
from ..tools.ffmpeg import FFmpeg
from .conversations import generate_conversations
from .gallery import generate_index_html
from .stats import generate_stats_html

console = Console()


def write_loose_pages(
    folder: Path,
    chats_with: list[str] | None = None,
    min_messages: int = 1,
    stats_only: list[str] | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    archive = load_archive(folder)
    if archive is None:
        return False
    _, file_index, json_data = archive
    if not json_data:
        console.print(f"[red]{folder} has no _meta/json, so the chats and the statistics "
                      f"cannot be written. Only --no-meta runs end up like this.[/red]")
        return False

    if dry_run:
        console.print(f"Would write gallery.html, chats.html, stats.html and "
                      f"conversations/ to {folder}")
        return True

    ff = FFmpeg()
    thumbs = build_thumbnails(file_index, folder, ff=ff if ff.check() else None,
                              verbose=verbose)
    media_map = build_media_id_map(file_index)

    count = generate_conversations(
        json_data, folder,
        conversations_for=chats_with or None,
        min_messages=min_messages,
        media_map=media_map,
        verbose=verbose,
    )
    console.print(f"Generated {count} conversation files")

    generate_stats_html(json_data, summarize_folder(folder, file_index),
                        folder, categories=stats_only or None, file_index=file_index)
    console.print("Generated stats.html")

    generate_index_html(file_index, folder, json_data=json_data, thumbs=thumbs)
    console.print("Generated gallery.html")
    return True
