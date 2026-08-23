from pathlib import Path

from rich.console import Console

from ..clock import load_zone, localize
from ..facts.mediacounts import count_overlays
from ..pages.site import generate_site
from ..read.inspector import load_json_data
from .manifest import load_manifest, manifest_to_file_index, write_manifest

console = Console()


def rebuild_folder(folder: Path, timezone: str = "",
                   dry_run: bool = False, verbose: bool = False) -> bool:
    manifest = load_manifest(folder)
    if not manifest:
        console.print(f"[red]{folder} has no _meta/manifest.json, so it is not a "
                      f"folder SnapXO produced.[/red]")
        return False

    file_index = manifest_to_file_index(manifest, folder)
    if not file_index:
        console.print(f"[red]The manifest in {folder} lists no file that still exists.[/red]")
        return False

    json_data = load_json_data(folder / "_meta")
    json_data = _localized(json_data, manifest, timezone)
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
                   timezone_name=str(manifest.get("timezone") or ""),
                   dry_run=dry_run)
    return True


def _localized(json_data: dict, manifest: dict, wanted: str) -> dict:
    # Another timezone leaves the pages disagreeing with the media file names.
    stored = str(manifest.get("timezone") or "UTC")
    chosen = wanted or stored
    if wanted and wanted != stored:
        console.print(f"[yellow]This archive was built in {stored}, rebuilding in "
                      f"{wanted}. The media file names keep their old dates.[/yellow]")
    zone = load_zone(chosen)
    return localize(json_data, zone) if zone is not None else json_data
