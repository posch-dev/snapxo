# Records where each file in an output folder came from. Paths are relative so
# a manifest survives moving the folder between drives and between Windows and Linux.

import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

console = Console()

MANIFEST_VERSION = 1


def manifest_path(output_dir: Path) -> Path:
    return output_dir / "_meta" / "manifest.json"


def _rel(path: Path, output_dir: Path) -> str:
    # POSIX form, so the manifest reads the same on either platform.
    try:
        return Path(path).resolve().relative_to(Path(output_dir).resolve()).as_posix()
    except (ValueError, OSError):
        return Path(path).name


def build_manifest(
    output_dir: Path,
    file_index: list[dict],
    own_username: str | None = None,
    sources: list[str] | None = None,
) -> dict:
    entries = []
    for i, entry in enumerate(file_index):
        dest = entry.get("dest", "")
        entries.append({
            "id": f"f{i:06d}",
            "rel": _rel(Path(dest), output_dir) if dest else "",
            "name": entry.get("new_name", ""),
            "subfolder": entry.get("subfolder", entry.get("year", "unknown")),
            "date": entry.get("date", ""),
            "type": entry.get("type", ""),
            "ext": entry.get("ext", ""),
            "source": entry.get("source", ""),
            "original_name": entry.get("original_name", ""),
            "media_id": entry.get("media_id"),
            # every Media ID resolving here, including ones dedup removed the copy of
            "media_ids": entry.get("media_ids") or ([entry["media_id"]] if entry.get("media_id") else []),
            "uuid": entry.get("uuid"),
            "size": entry.get("size"),
            # Only set when the file arrived damaged, see verify.py
            "integrity": entry.get("integrity"),
        })

    return {
        "version": MANIFEST_VERSION,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "own_username": own_username,
        "sources": sources or [],
        "files": entries,
    }


def write_manifest(
    output_dir: Path,
    file_index: list[dict],
    own_username: str | None = None,
    sources: list[str] | None = None,
    dry_run: bool = False,
) -> bool:
    if dry_run:
        return True

    # Sizes are read here rather than during organize, where files may still change.
    for entry in file_index:
        dest = entry.get("dest")
        if dest and entry.get("size") is None:
            try:
                entry["size"] = Path(dest).stat().st_size
            except OSError:
                entry["size"] = None

    data = build_manifest(output_dir, file_index, own_username, sources)
    path = manifest_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return True


def load_manifest(output_dir: Path) -> dict | None:
    path = manifest_path(output_dir)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        console.print(f"[yellow]Could not read {path}[/yellow]")
        return None


def manifest_to_file_index(manifest: dict, output_dir: Path) -> list[dict]:
    # Rebuild a file_index from a manifest, dropping entries whose file is gone.
    file_index = []
    for entry in manifest.get("files", []):
        rel = entry.get("rel", "")
        if not rel:
            continue
        dest = output_dir / rel
        if not dest.is_file():
            continue
        file_index.append({
            "date": entry.get("date", ""),
            "year": entry.get("subfolder", "unknown")[:4],
            "subfolder": entry.get("subfolder", "unknown"),
            "new_name": entry.get("name", dest.name),
            "original_name": entry.get("original_name", ""),
            "source": entry.get("source", ""),
            "type": entry.get("type", ""),
            "ext": entry.get("ext", dest.suffix.lower()),
            "uuid": entry.get("uuid"),
            "media_id": entry.get("media_id"),
            "media_ids": entry.get("media_ids") or [],
            "size": entry.get("size"),
            "dest": str(dest),
            "integrity": entry.get("integrity"),
        })
    return file_index


def build_media_id_map(
    file_index: list[dict],
    dup_alias: dict[str, str] | None = None,
) -> dict[str, dict]:
    # Map Media IDs to the file they became. `dup_alias` maps a path dedup deleted
    # to the one it duplicated, without it those messages would show no media.
    from .utils import extract_media_id

    by_media_id: dict[str, dict] = {}
    by_original: dict[str, dict] = {}

    for entry in file_index:
        original = entry.get("original_name", "")
        if original:
            by_original[original] = entry
        # from a manifest this already includes dedup aliases
        ids = entry.get("media_ids") or ([entry["media_id"]] if entry.get("media_id") else [])
        for media_id in ids:
            if media_id and media_id not in by_media_id:
                by_media_id[media_id] = entry

    for removed_path, kept_path in (dup_alias or {}).items():
        media_id = extract_media_id(Path(removed_path).name)
        if not media_id or media_id in by_media_id:
            continue
        kept_entry = by_original.get(Path(kept_path).name)
        if kept_entry:
            by_media_id[media_id] = kept_entry

    return by_media_id


def attach_media_ids(file_index: list[dict], media_map: dict[str, dict]) -> None:
    # Record on each entry which Media IDs resolve to it, ready for the manifest.
    by_dest: dict[str, list[str]] = {}
    for media_id, entry in media_map.items():
        by_dest.setdefault(entry.get("dest", ""), []).append(media_id)
    for entry in file_index:
        ids = by_dest.get(entry.get("dest", ""))
        if ids:
            entry["media_ids"] = sorted(ids)
