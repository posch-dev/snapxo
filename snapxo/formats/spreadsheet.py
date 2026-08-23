from datetime import datetime
from pathlib import Path

from rich.console import Console

from ..archive.manifest import load_manifest, manifest_to_file_index
from ..clock import load_zone, localize
from ..facts.datasets import numbers_dataset, stats_datasets
from ..facts.mediacounts import summarize_folder
from ..facts.series import build_series
from ..pages.stats import stat_card_values
from ..read.inspector import load_json_data
from .tables import file_name, write_csv_folder, write_ods, write_xlsx

console = Console()

SPREADSHEET_DIR = "spreadsheet"


def spreadsheet_dir(folder: Path) -> Path:
    return folder / SPREADSHEET_DIR


def collect_datasets(folder: Path) -> list[dict] | None:
    manifest = load_manifest(folder)
    if not manifest:
        console.print(f"[red]{folder} has no _meta/manifest.json, so it is not a "
                      f"folder SnapXO produced.[/red]")
        return None

    file_index = manifest_to_file_index(manifest, folder)
    json_data = load_json_data(folder / "_meta")
    zone = load_zone(str(manifest.get("timezone") or ""))
    if zone is not None:
        json_data = localize(json_data, zone)

    series = build_series(json_data, file_index)
    file_stats = summarize_folder(folder, file_index)
    return [numbers_dataset(stat_card_values(json_data, file_stats, series))] + stats_datasets(series)


def export_stats(folder: Path, spreadsheet_format: str = "xlsx",
                 target: Path | None = None, dry_run: bool = False) -> bool:
    datasets = collect_datasets(folder)
    if datasets is None:
        return False
    if not datasets:
        console.print(f"[yellow]{folder} has no statistics to export.[/yellow]")
        return False

    stamp = datetime.now().strftime("%Y-%m-%d")
    target_dir = target or spreadsheet_dir(folder)
    if dry_run:
        console.print(f"Would write {len(datasets)} tables as {spreadsheet_format} "
                      f"to {target_dir}")
        return True

    target_dir.mkdir(parents=True, exist_ok=True)

    if spreadsheet_format == "csv":
        written = write_csv_folder(datasets, target_dir, stamp)
        console.print(f"  Wrote {len(written)} CSV files to {target_dir}")
        return True

    written = target_dir / file_name("stats", spreadsheet_format, stamp)
    if spreadsheet_format == "ods":
        write_ods(datasets, written)
    else:
        try:
            write_xlsx(datasets, written)
        except ImportError:
            console.print("[red]XLSX needs openpyxl: pip install \"snapxo[spreadsheet]\". "
                          "Or use --format ods, which needs nothing.[/red]")
            return False
    console.print(f"  Wrote {written} ({len(datasets)} sheets)")
    return True
