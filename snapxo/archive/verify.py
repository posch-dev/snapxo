import json
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from ..files import file_hash
from ..filetypes import MEDIA_EXTS
from .manifest import load_manifest

console = Console()

CHECKSUM_VERSION = 1


def checksum_path(folder: Path) -> Path:
    return folder / "_meta" / "checksums.json"


def integrity_path(folder: Path) -> Path:
    return folder / "_meta" / "integrity.json"


def load_checksums(folder: Path) -> dict[str, str]:
    path = checksum_path(folder)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        console.print(f"[yellow]Could not read {path}[/yellow]")
        return {}
    files = data.get("files")
    return files if isinstance(files, dict) else {}


def write_checksums(folder: Path, hashes: dict[str, str], dry_run: bool = False) -> bool:
    if dry_run or not hashes:
        return False
    path = checksum_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": CHECKSUM_VERSION, "algorithm": "md5", "files": dict(sorted(hashes.items()))}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return True


def load_integrity(folder: Path) -> list[dict]:
    path = integrity_path(folder)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []
    entries = data.get("files")
    return entries if isinstance(entries, list) else []


def write_integrity(folder: Path, entries: list[dict], generated: str = "", dry_run: bool = False) -> bool:
    if dry_run or not entries:
        return False
    path = integrity_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"generated": generated, "files": entries}, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return True


@dataclass
class Report:
    folder: Path
    checked: int = 0
    missing: list[str] = field(default_factory=list)
    wrong_size: list[str] = field(default_factory=list)
    wrong_hash: list[str] = field(default_factory=list)
    unlisted: list[str] = field(default_factory=list)
    hashed: bool = False
    has_manifest: bool = True
    has_baseline: bool = False
    damaged_on_arrival: int = 0

    @property
    def problems(self) -> int:
        return len(self.missing) + len(self.wrong_size) + len(self.wrong_hash)

    @property
    def ok(self) -> bool:
        return self.has_manifest and self.problems == 0


def verify_folder(folder: Path, hashes: bool = False) -> tuple[Report, dict[str, str]]:
    # Without `hashes` only existence and size are checked, which is instant and
    # still finds the common half-copied folder.
    report = Report(folder=folder, hashed=hashes)
    manifest = load_manifest(folder)
    if not manifest:
        report.has_manifest = False
        return report, {}

    baseline = load_checksums(folder)
    report.has_baseline = bool(baseline)
    report.damaged_on_arrival = len(load_integrity(folder))

    computed: dict[str, str] = {}
    listed: set[str] = set()

    for entry in manifest.get("files", []):
        rel = entry.get("rel", "")
        if not rel:
            continue
        listed.add(rel)
        path = folder / rel
        if not path.is_file():
            report.missing.append(rel)
            continue

        report.checked += 1
        size = entry.get("size")
        if isinstance(size, int) and path.stat().st_size != size:
            report.wrong_size.append(rel)
            continue

        if hashes:
            digest = file_hash(path)
            computed[rel] = digest
            if baseline.get(rel) and baseline[rel] != digest:
                report.wrong_hash.append(rel)

    for path in folder.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTS:
            continue
        rel = path.relative_to(folder).as_posix()
        # Unmatched overlays are output too, they were never in the manifest.
        if rel.startswith(("_meta/", "_overlays/")) or rel in listed:
            continue
        report.unlisted.append(rel)

    return report, computed


def print_report(report: Report) -> None:
    name = report.folder.name or str(report.folder)
    if not report.has_manifest:
        console.print(f"[yellow]{name}: no manifest, nothing to check against[/yellow]")
        return

    if report.ok:
        console.print(f"[green]{name}: {report.checked} files in order[/green]")
    else:
        console.print(f"[red]{name}: {report.problems} problems in {report.checked} files[/red]")

    for label, items in (("missing", report.missing),
                         ("wrong size", report.wrong_size),
                         ("changed content", report.wrong_hash)):
        for rel in items[:10]:
            console.print(f"  [red]{label}: {rel}[/red]")
        if len(items) > 10:
            console.print(f"  [red]... and {len(items) - 10} more {label}[/red]")

    if report.unlisted:
        console.print(f"  [yellow]{len(report.unlisted)} media files are not in the manifest[/yellow]")
    if report.hashed and not report.has_baseline:
        console.print("  [dim]No checksums yet, this run writes the baseline[/dim]")
    if report.damaged_on_arrival:
        console.print(f"  [yellow]{report.damaged_on_arrival} files were already damaged when they "
                      f"were merged in, see _meta/integrity.json[/yellow]")
