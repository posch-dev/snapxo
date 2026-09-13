from pathlib import Path

from rich.console import Console

from ..facts.mediacounts import count_overlays
from ..pages.site import generate_site
from .manifest import archive_zone, load_archive, write_manifest

console = Console()


def rebuild_folder(folder: Path, timezone: str = "",
                   dry_run: bool = False, verbose: bool = False) -> bool:
    archive = load_archive(folder, timezone)
    if archive is None:
        return False
    manifest, file_index, json_data = archive
    if not file_index:
        console.print(f"[red]The manifest in {folder} lists no file that still exists.[/red]")
        return False

    stored = archive_zone(manifest)
    if timezone and timezone != stored:
        console.print(f"Timestamps move from {stored} to {timezone}")
    if not json_data:
        console.print(f"[yellow]{folder} has no _meta/json, so only the media gallery can be "
                      f"rebuilt. Folders organized with --no-meta never kept the raw export.[/yellow]")

    console.print(f"Rebuilding from {len(file_index)} files")
    generate_site(folder, json_data, file_index, overlay_count=count_overlays(folder),
                  dry_run=dry_run, verbose=verbose)

    # Measurements go back in, so the next rebuild does not pay for them again.
    write_manifest(folder, file_index,
                   own_username=manifest.get("own_username"),
                   sources=manifest.get("sources"),
                   timezone_name=timezone or stored,
                   dry_run=dry_run)
    return True
