# Merge several finished output folders into one. Two exports of the same account
# overlap almost completely and each numbers its own year folder from 0001, so
# merging means: deduplicate by content, renumber chronologically, rebuild the
# generated pages. Media is copied or hardlinked, never re-encoded.

import json
import os
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from .conversations import generate_conversations
from .indexer import generate_index_html, generate_index_pdf
from .inspector import load_json_data
from .manifest import build_media_id_map, load_manifest, write_manifest
from .metadata import apply_file_times
from .snapmap import generate_map_html
from .stats import generate_stats_html
from .thumbs import build_thumbnails
from .utils import AUDIO_EXTS, IMAGE_EXTS, VIDEO_EXTS, extract_date_from_filename, file_hash
from .verify import load_checksums, print_report, verify_folder, write_checksums, write_integrity

console = Console()

SKIP_DIRS = {"conversations"}


def _is_media_dir(path: Path) -> bool:
    return path.is_dir() and not path.name.startswith("_") and path.name not in SKIP_DIRS


def _file_type(ext: str) -> str | None:
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    return None


def _collect_records(input_dir: Path) -> list[dict]:
    # Every media file in an output folder, enriched from its manifest if present.
    manifest = load_manifest(input_dir)
    by_rel: dict[str, dict] = {}
    if manifest:
        for entry in manifest.get("files", []):
            if entry.get("rel"):
                by_rel[entry["rel"]] = entry
    else:
        console.print(
            f"[yellow]{input_dir.name}: no manifest found - merging media only, "
            f"file details will be limited[/yellow]"
        )

    records = []
    for subdir in sorted(input_dir.iterdir()):
        if not _is_media_dir(subdir):
            continue
        for f in sorted(subdir.iterdir()):
            if not f.is_file():
                continue
            ftype = _file_type(f.suffix.lower())
            if ftype is None:
                continue
            rel = f"{subdir.name}/{f.name}"
            meta = by_rel.get(rel, {})
            records.append({
                "src": f,
                "input": input_dir,
                "rel": rel,
                "integrity": meta.get("integrity"),
                "subfolder": meta.get("subfolder") or subdir.name,
                "date": meta.get("date") or extract_date_from_filename(f.name) or "unknown",
                "type": meta.get("type") or ftype,
                "ext": meta.get("ext") or f.suffix.lower(),
                "source": meta.get("source", ""),
                "original_name": meta.get("original_name", f.name),
                "media_id": meta.get("media_id"),
                "media_ids": meta.get("media_ids") or [],
                "uuid": meta.get("uuid"),
                "old_name": f.name,
            })
    return records


def _deduplicate(
    records: list[dict],
    baselines: dict[Path, dict[str, str]] | None = None,
) -> tuple[list[dict], int, int]:
    # Drop files whose content already appeared in an earlier input folder. The hash
    # is needed anyway, so comparing it to the folder's checksums costs nothing.
    seen: dict[str, dict] = {}
    unique = []
    dropped = 0
    freed = 0
    baselines = baselines or {}

    with Progress(console=console) as progress:
        task = progress.add_task("Hashing files...", total=len(records))
        for rec in records:
            digest = file_hash(rec["src"])
            rec["hash"] = digest

            known = baselines.get(rec["input"], {}).get(rec.get("rel", ""))
            if known and known != digest and not rec.get("integrity"):
                rec["integrity"] = {"reason": "changed content", "folder": rec["input"].name}

            if digest in seen:
                dropped += 1
                freed += rec["src"].stat().st_size
            else:
                seen[digest] = rec
                unique.append(rec)
            progress.advance(task)

    return unique, dropped, freed


def _check_inputs(inputs: list[Path], verify: bool) -> tuple[dict[Path, list[str]], dict[Path, dict[str, str]]]:
    # Returns the damaged files per folder and the checksums to compare against.
    console.rule("[bold yellow]Verify[/bold yellow]")
    damaged: dict[Path, list[str]] = {}
    baselines: dict[Path, dict[str, str]] = {}
    problems = 0

    for input_dir in inputs:
        report, _ = verify_folder(input_dir)
        print_report(report)
        damaged[input_dir] = list(report.wrong_size)
        baselines[input_dir] = load_checksums(input_dir)
        problems += report.problems
        if not baselines[input_dir]:
            console.print("  [dim]No checksums in this folder, only names and sizes were checked[/dim]")

    if problems and verify:
        console.print()
        console.print(f"[red]{problems} files do not match their manifest. Nothing has been written.[/red]")
        console.print("Options:")
        console.print("  - copy the affected folder from its original again")
        console.print("  - [cyan]--no-verify[/cyan] takes the damaged files along, marked as damaged")
        console.print("  - [cyan]--no-verify --skip-damaged[/cyan] leaves them out")
        raise SystemExit(1)

    return damaged, baselines


def _mark_damaged(records: list[dict], damaged: dict[Path, list[str]]) -> int:
    marked = 0
    for rec in records:
        if rec.get("integrity"):
            marked += 1
            continue
        if rec.get("rel") in damaged.get(rec["input"], []):
            rec["integrity"] = {"reason": "wrong size", "folder": rec["input"].name}
            marked += 1
    return marked


def _recover_damaged(records: list[dict]) -> tuple[list[dict], int]:
    # A file damaged in one export may be intact in another, which is the whole
    # point of merging. Keep the intact copy and drop the damaged twin.
    by_identity: dict[str, list[dict]] = {}
    for rec in records:
        identity = rec.get("media_id") or rec.get("original_name") or ""
        if identity:
            by_identity.setdefault(identity, []).append(rec)

    drop = set()
    recovered = 0
    for group in by_identity.values():
        intact = [r for r in group if not r.get("integrity")]
        broken = [r for r in group if r.get("integrity")]
        if intact and broken:
            for rec in broken:
                drop.add(id(rec))
                recovered += 1

    if not drop:
        return records, 0
    return [r for r in records if id(r) not in drop], recovered


def _renumber(records: list[dict], folder_structure: str) -> list[dict]:
    # Assign fresh sequential names, chronologically, per target folder.
    for rec in records:
        date = rec["date"]
        if folder_structure == "year-month":
            rec["target_folder"] = date[:7] if date != "unknown" else "unknown"
        else:
            rec["target_folder"] = date[:4] if date != "unknown" else "unknown"

    records.sort(key=lambda r: (r["date"], r["old_name"]))

    counters: dict[str, int] = defaultdict(int)
    for rec in records:
        folder = rec["target_folder"]
        counters[folder] += 1
        ext = ".mp4" if rec["type"] == "video" else rec["ext"]
        rec["new_name"] = f"{rec['date']}_{counters[folder]:04d}{ext}"
    return records


def _transfer(src: Path, dst: Path, hardlink: bool) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if hardlink:
        try:
            if dst.exists():
                dst.unlink()
            os.link(str(src), str(dst))
            return "link"
        except OSError:
            # Different filesystem, or the OS refused, so fall back to copying
            pass
    shutil.copy2(str(src), str(dst))
    return "copy"


def _merge_key(item) -> str:
    try:
        return json.dumps(item, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return repr(item)


def _merge_lists(first: list, second: list) -> list:
    seen = {_merge_key(x) for x in first}
    out = list(first)
    for item in second:
        key = _merge_key(item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _merge_node(first, second):
    if isinstance(first, dict) and isinstance(second, dict):
        out = dict(first)
        for key, value in second.items():
            out[key] = _merge_node(first[key], value) if key in first else value
        return out
    if isinstance(first, list) and isinstance(second, list):
        return _merge_lists(first, second)
    return first


def merge_json_data(datas: list[dict]) -> dict:
    # Union of the exports' JSON data, deduplicated entry by entry.
    merged: dict = {}
    for data in datas:
        for name, content in data.items():
            merged[name] = _merge_node(merged[name], content) if name in merged else content

    # chat_history is exported newest-first; restore that after merging
    chat = merged.get("chat_history")
    if isinstance(chat, dict):
        for messages in chat.values():
            if isinstance(messages, list):
                messages.sort(
                    key=lambda m: m.get("Created(microseconds)", 0) if isinstance(m, dict) else 0,
                    reverse=True,
                )
    return merged


def _build_file_stats(file_index: list[dict], overlay_count: int) -> dict:
    stats = {
        "images": 0, "videos": 0, "overlays": overlay_count,
        "chat_media_img": 0, "chat_media_vid": 0, "chat_media_other": 0,
        "json_files": [], "html_files": 0, "total_size": 0,
    }
    for entry in file_index:
        size = entry.get("size") or 0
        stats["total_size"] += size
        is_chat = entry.get("source") == "chat"
        if entry["type"] == "image":
            stats["chat_media_img" if is_chat else "images"] += 1
        elif entry["type"] == "video":
            stats["chat_media_vid" if is_chat else "videos"] += 1
        else:
            stats["chat_media_other"] += 1
    return stats


def _copy_overlays(inputs: list[Path], output: Path, hardlink: bool, dry_run: bool) -> int:
    seen: set[str] = set()
    count = 0
    for input_dir in inputs:
        src_dir = input_dir / "_overlays"
        if not src_dir.is_dir():
            continue
        for f in sorted(src_dir.iterdir()):
            if not f.is_file() or f.name in seen:
                continue
            seen.add(f.name)
            count += 1
            if not dry_run:
                _transfer(f, output / "_overlays" / f.name, hardlink)
    return count


def looks_like_output_folder(path: Path) -> bool:
    # An output folder has a manifest, an index, or at least one media folder.
    if not path.is_dir():
        return False
    if (path / "_meta" / "manifest.json").is_file() or (path / "index.html").is_file():
        return True
    for sub in path.iterdir():
        if _is_media_dir(sub) and any(_file_type(f.suffix.lower()) for f in sub.iterdir() if f.is_file()):
            return True
    return False


def expand_inputs(inputs: list[Path]) -> list[Path]:
    # Accept output folders directly, or a parent folder holding them. With a dozen
    # exports that is easier than listing every single one.
    resolved: list[Path] = []
    seen: set[Path] = set()

    for path in inputs:
        candidates = [path]
        if not looks_like_output_folder(path) and path.is_dir():
            found = [p for p in sorted(path.iterdir()) if looks_like_output_folder(p)]
            if found:
                console.print(f"  {path}: expanded to {len(found)} output folders")
                candidates = found

        for candidate in candidates:
            key = candidate.resolve()
            if key not in seen:
                seen.add(key)
                resolved.append(candidate)

    return resolved


def _validate(inputs: list[Path], output: Path):
    for input_dir in inputs:
        if not input_dir.is_dir():
            raise SystemExit(f"Not a directory: {input_dir}")
    resolved_out = output.resolve()
    for input_dir in inputs:
        resolved_in = input_dir.resolve()
        if resolved_out == resolved_in:
            raise SystemExit("Output folder must differ from the input folders.")
        if resolved_out.is_relative_to(resolved_in):
            raise SystemExit(f"Output folder must not be inside an input folder ({input_dir}).")
        if resolved_in.is_relative_to(resolved_out):
            raise SystemExit(f"Input folder must not be inside the output folder ({input_dir}).")


def _verify_transferred(records: list[dict], output: Path) -> list[str]:
    # Re-hash everything in the output before any source folder is deleted.
    problems = []
    with Progress(console=console) as progress:
        task = progress.add_task("Verifying merged files...", total=len(records))
        for rec in records:
            dst = output / rec["target_folder"] / rec["new_name"]
            if not dst.is_file():
                problems.append(f"missing: {rec['target_folder']}/{rec['new_name']}")
            elif file_hash(dst) != rec["hash"]:
                problems.append(f"content mismatch: {rec['target_folder']}/{rec['new_name']}")
            progress.advance(task)
    return problems


def merge_outputs(
    inputs: list[Path],
    output: Path | None,
    hardlink: bool = False,
    delete_sources: bool = False,
    yes: bool = False,
    folder_structure: str = "year",
    conversation_format: str = "html",
    index_format: str = "html",
    verify: bool = True,
    skip_damaged: bool = False,
    dry_run: bool = False,
) -> int:
    console.rule("[bold yellow]Collect[/bold yellow]")
    if output is None:
        if not dry_run:
            console.print("[red]No output directory set (-o/--output).[/red]")
            return 0
        # Never written to, it only keeps the dry run's paths printable.
        output = Path("snapxo-dry-run")
    inputs = expand_inputs(inputs)
    if len(inputs) < 2:
        console.print("[red]Need at least two output folders to merge.[/red]")
        return 0
    console.print(f"Merging {len(inputs)} folders")
    _validate(inputs, output)

    records: list[dict] = []
    for input_dir in inputs:
        found = _collect_records(input_dir)
        console.print(f"  {input_dir.name}: {len(found)} media files")
        records.extend(found)

    if not records:
        console.print("[red]No media files found in the given folders.[/red]")
        return 0

    damaged_by_folder, baselines = _check_inputs(inputs, verify)
    _mark_damaged(records, damaged_by_folder)

    console.rule("[bold yellow]Deduplicate[/bold yellow]")
    records, dropped, freed = _deduplicate(records, baselines)
    console.print(f"Kept {len(records)} files, dropped {dropped} duplicates ({freed / (1024*1024):.1f} MB)")

    records, recovered = _recover_damaged(records)
    if recovered:
        console.print(f"[green]Recovered {recovered} damaged files from another export[/green]")

    still_damaged = [r for r in records if r.get("integrity")]
    if still_damaged and skip_damaged:
        records = [r for r in records if not r.get("integrity")]
        console.print(f"[yellow]Left out {len(still_damaged)} damaged files (--skip-damaged)[/yellow]")
    elif still_damaged:
        console.print(f"[yellow]Taking {len(still_damaged)} damaged files along, marked as damaged[/yellow]")

    console.rule("[bold yellow]Renumber[/bold yellow]")
    records = _renumber(records, folder_structure)
    console.print(f"Renumbered into {len({r['target_folder'] for r in records})} folders")

    console.rule("[bold yellow]Transfer[/bold yellow]")
    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)
    modes = {"link": 0, "copy": 0}
    if dry_run:
        for rec in records[:5]:
            console.print(f"  [dim]Would write {rec['target_folder']}/{rec['new_name']}[/dim]")
        console.print(f"  [dim]... {len(records)} files total[/dim]")
    else:
        with Progress(console=console) as progress:
            task = progress.add_task("Transferring...", total=len(records))
            for rec in records:
                mode = _transfer(rec["src"], output / rec["target_folder"] / rec["new_name"], hardlink)
                modes[mode] += 1
                progress.advance(task)
    if modes["link"]:
        console.print(f"  Hardlinked {modes['link']}, copied {modes['copy']}")
    elif hardlink and not dry_run:
        console.print("  [yellow]Hardlinking not possible (different filesystem) - copied instead[/yellow]")

    overlay_count = _copy_overlays(inputs, output, hardlink, dry_run)
    if overlay_count:
        console.print(f"  Copied {overlay_count} overlays")

    file_index = []
    for rec in records:
        dest = output / rec["target_folder"] / rec["new_name"]
        file_index.append({
            "date": rec["date"],
            "year": rec["target_folder"][:4],
            "subfolder": rec["target_folder"],
            "new_name": rec["new_name"],
            "original_name": rec["original_name"],
            "source": rec["source"],
            "type": rec["type"],
            "ext": rec["ext"],
            "uuid": rec["uuid"],
            "media_id": rec["media_id"],
            "media_ids": rec["media_ids"],
            "size": rec["src"].stat().st_size,
            "dest": str(dest),
            "integrity": rec.get("integrity"),
        })

    if not dry_run:
        rel_hashes = {f"{rec['target_folder']}/{rec['new_name']}": rec["hash"] for rec in records}
        write_checksums(output, rel_hashes)
        console.print(f"  Wrote checksums for {len(rel_hashes)} files")

        marked = [{"rel": f"{rec['target_folder']}/{rec['new_name']}", **rec["integrity"]}
                  for rec in records if rec.get("integrity")]
        if write_integrity(output, marked, generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")):
            console.print(f"  Recorded {len(marked)} damaged files in _meta/integrity.json")

    touched = apply_file_times(file_index, dry_run=dry_run)
    if touched:
        console.print(f"  Set the file date on {touched} files")

    console.rule("[bold yellow]Merge metadata[/bold yellow]")
    datas = []
    for input_dir in inputs:
        data = load_json_data(input_dir / "_meta")
        if data:
            datas.append(data)
            console.print(f"  {input_dir.name}: {len(data)} JSON files")
        else:
            console.print(f"  [yellow]{input_dir.name}: no _meta/json "
                          f"(was it run with --clean before this change?)[/yellow]")

    json_data = merge_json_data(datas) if datas else {}

    if json_data and not dry_run:
        meta_json = output / "_meta" / "json"
        meta_json.mkdir(parents=True, exist_ok=True)
        for name, content in json_data.items():
            (meta_json / f"{name}.json").write_text(
                json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8"
            )

    own_username = None
    account = json_data.get("account", {})
    if isinstance(account, dict):
        basic = account.get("Basic Information", {})
        if isinstance(basic, dict):
            own_username = basic.get("Username")

    write_manifest(
        output, file_index,
        own_username=own_username,
        sources=[str(p) for p in inputs],
        dry_run=dry_run,
    )

    console.rule("[bold yellow]Regenerate[/bold yellow]")
    thumbs = build_thumbnails(file_index, output, dry_run=dry_run)
    if json_data:
        media_map = build_media_id_map(file_index)
        conv_count = generate_conversations(
            json_data, output,
            conversation_format=conversation_format,
            media_map=media_map,
            dry_run=dry_run,
        )
        console.print(f"Generated {conv_count} conversation files")

        generate_stats_html(json_data, _build_file_stats(file_index, overlay_count), output, dry_run=dry_run)
        console.print("Generated stats.html")

        if generate_map_html(json_data, output, file_index=file_index, dry_run=dry_run):
            console.print("Generated map.html")
    else:
        console.print("[yellow]No JSON data available - skipping conversations, stats and map[/yellow]")

    generate_index_html(file_index, output, json_data=json_data, dry_run=dry_run, thumbs=thumbs)
    if index_format == "pdf":
        generate_index_pdf(file_index, output, json_data=json_data, thumbs=thumbs, dry_run=dry_run)

    if delete_sources and not dry_run:
        console.rule("[bold yellow]Delete sources[/bold yellow]")
        problems = _verify_transferred(records, output)
        if problems:
            console.print(f"[red]Verification failed for {len(problems)} files - keeping the source folders.[/red]")
            for p in problems[:10]:
                console.print(f"  [red]{p}[/red]")
            return len(file_index)

        console.print(f"[green]Verified all {len(records)} files in the merged folder.[/green]")
        if not yes:
            listing = ", ".join(str(p) for p in inputs)
            answer = console.input(f"\n[bold red]Delete {listing}? [y/N] [/bold red]")
            if answer.strip().lower() != "y":
                console.print("Keeping the source folders.")
                return len(file_index)

        for input_dir in inputs:
            shutil.rmtree(input_dir, ignore_errors=True)
            console.print(f"  Deleted {input_dir}")
    elif delete_sources and dry_run:
        console.print("[dim]Would delete the source folders after verification[/dim]")

    console.rule("[bold green]Merge done[/bold green]")
    console.print(f"Output: {output}  ({len(file_index)} files)")
    return len(file_index)
