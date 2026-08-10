import shutil
import tempfile
import zipfile
from pathlib import Path

from rich.console import Console

from .checkpoint import Checkpoint, config_fingerprint
from .cleanup import cleanup_tmp_files
from .config import Config
from .conversations import generate_conversations
from .dedup import remove_duplicates
from .deps import require_ffmpeg, require_playwright
from .encoder import encode_videos
from .ffmpeg import FFmpeg
from .fixtypes import fix_unknown_files
from .indexer import generate_index_html
from .inspector import (
    count_json_stats,
    display_summary,
    find_export_inputs,
    inspect_directory,
    inspect_zip,
    load_json_data,
    validate_zip,
)
from .manifest import (
    attach_media_ids,
    build_media_id_map,
    load_manifest,
    manifest_to_file_index,
    write_manifest,
)
from .metadata import apply_gps_metadata
from .organizer import organize_into_folders
from .overlay import burn_overlays, copy_unmatched_overlays, match_overlays
from .pdf import render_single
from .scanner import scan_export
from .snapmap import generate_map_html
from .stats import generate_stats_html
from .voice import convert_voice_messages, detect_voice_messages

console = Console()


def _check_external_tools(config: Config, ff: FFmpeg) -> None:
    # Fail early, with install instructions, if a needed external tool is absent.
    if config.should_encode():
        require_ffmpeg(ff)
    if config.conversation_format == "pdf" and not config.dry_run:
        require_playwright()


def _done_already(checkpoint, step: str) -> bool:
    # Only for steps that are finished or not; the per-file loops track themselves.
    if checkpoint.is_step_done(step):
        console.print("Already done, skipping")
        return True
    return False


def _own_username(json_data: dict) -> str | None:
    account = json_data.get("account", {})
    if isinstance(account, dict):
        basic = account.get("Basic Information", {})
        if isinstance(basic, dict):
            return basic.get("Username")
    return None


CATEGORIES = [
    ("media",         "Media (Memories + Chat Media + Voice)"),
    ("encode",        "Encode videos to H.265"),
    ("overlay",       "Burn overlays onto media"),
    ("exif",          "Write EXIF/GPS metadata"),
    ("dedup",         "Remove duplicates"),
    ("conversations", "Generate conversations"),
    ("stats",         "Generate stats HTML"),
    ("map",           "Generate Snap Map"),
    ("stickers",      "Export stickers"),
    ("index",         "Generate media gallery HTML"),
    ("meta",          "Copy raw metadata"),
]


def _interactive_select(config: Config, console: Console):
    # Let the user pick which categories to process.
    console.print("\n[bold]What should be processed?[/bold]")
    for i, (_key, label) in enumerate(CATEGORIES, 1):
        console.print(f"  [yellow]{i:2d}[/yellow] {label}")
    console.print("  [yellow] 0[/yellow] Cancel")

    response = console.input("\n[bold]Enter numbers (comma-separated, e.g. 1,6,7): [/bold]")
    if response.strip() == "0":
        raise SystemExit(0)

    try:
        selected = {int(x.strip()) for x in response.split(",") if x.strip()}
    except ValueError:
        console.print("[red]Invalid input.[/red]")
        raise SystemExit(1) from None

    selected_keys = set()
    for i, (key, _) in enumerate(CATEGORIES, 1):
        if i in selected:
            selected_keys.add(key)

    if not selected_keys:
        console.print("[red]Nothing selected.[/red]")
        raise SystemExit(1)

    if "media" not in selected_keys:
        config.only_conversations = True
    if "encode" not in selected_keys:
        config.no_encode = True
    if "overlay" not in selected_keys:
        config.no_overlay = True
    if "exif" not in selected_keys:
        config.no_exif = True
    if "dedup" not in selected_keys:
        config.no_dedup = True
    if "conversations" not in selected_keys:
        config.no_conversations = True
    if "stats" not in selected_keys:
        config.no_stats = True
    if "map" not in selected_keys:
        config.no_map = True
    if "stickers" not in selected_keys:
        config.no_stickers = True
    if "index" not in selected_keys:
        config.no_index = True
    if "meta" not in selected_keys:
        config.no_meta = True

    if "media" in selected_keys:
        config.only_conversations = False

    chosen = ", ".join(label for key, label in CATEGORIES if key in selected_keys)
    console.print(f"\n[green]Selected: {chosen}[/green]\n")


def run_pipeline(config: Config):
    console.rule("[bold yellow]Step 1: Input[/bold yellow]")
    zips, extracted_dir = find_export_inputs(config.inputs)

    if not zips and not extracted_dir:
        console.print("[red]No valid Snapchat export found.[/red]")
        raise SystemExit(1)

    if zips:
        for z in zips:
            if not validate_zip(z):
                console.print(f"[red]{z.name} is not a valid Snapchat export ZIP[/red]")
                raise SystemExit(1)
        console.print(f"Found {len(zips)} ZIP(s): {', '.join(z.name for z in zips)}")

    if not config.output:
        console.print("[red]No output directory set (-o/--output).[/red]")
        raise SystemExit(1)

    # Created further down, so --info and --dry-run leave no empty folder behind.
    output_dir = config.output
    console.print(f"Output: {output_dir}")

    console.rule("[bold yellow]Step 2: Inspect[/bold yellow]")
    file_stats = {"images": 0, "videos": 0, "overlays": 0,
                  "chat_media_img": 0, "chat_media_vid": 0, "chat_media_other": 0,
                  "json_files": [], "html_files": 0, "total_size": 0}

    if zips:
        for z in zips:
            zs = inspect_zip(z)
            for key in file_stats:
                if isinstance(file_stats[key], int):
                    file_stats[key] += zs[key]
                elif isinstance(file_stats[key], list):
                    file_stats[key].extend(zs[key])

    # Initialize ffmpeg early so external tools can be checked before the
    # expensive extraction step: nobody wants to unpack 6 GB only to be told
    # that ffmpeg is missing.
    ff = FFmpeg(
        ffmpeg_path=config.ffmpeg_path,
        ffprobe_path=config.ffprobe_path,
        no_hwaccel=config.no_hwaccel,
        crf=config.crf,
    )
    # Only up front when the run is already fully determined by flags; in
    # interactive mode the user may still deselect the steps that need them.
    if config.yes and not config.info:
        _check_external_tools(config, ff)

    if extracted_dir:
        export_dir = extracted_dir
    elif zips:
        export_dir = Path(tempfile.mkdtemp(prefix="snapexport_"))
        console.rule("[bold yellow]Step 4: Extract[/bold yellow]")
        for z in zips:
            console.print(f"Extracting {z.name}...")
            with zipfile.ZipFile(z, "r") as zf:
                zf.extractall(export_dir)
    else:
        raise SystemExit(1)

    if extracted_dir:
        file_stats = inspect_directory(extracted_dir)

    json_data = load_json_data(export_dir)
    json_stats = count_json_stats(json_data)

    zip_names = [z.name for z in zips] if zips else None
    display_summary(file_stats, json_stats, zip_names)

    if config.info:
        return

    if not config.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    if not config.yes and not config.dry_run:
        response = console.input("\n[bold]Organize everything? [Y/n] [/bold]")
        if response.strip().lower() == "n":
            _interactive_select(config, console)

    # Re-check after the interactive selection, which may have changed what runs
    _check_external_tools(config, ff)

    # The fingerprint makes a run with different filters start from scratch.
    checkpoint = Checkpoint(
        output_dir,
        fingerprint=config_fingerprint(config),
        enabled=not config.dry_run,
    )
    if config.resume and checkpoint.load():
        console.print(f"[green]Resuming from checkpoint ({checkpoint.summary()})[/green]")

    console.rule("[bold yellow]Step 5: Scan[/bold yellow]")
    scan = scan_export(export_dir)
    console.print(f"Scanned: {len(scan.memories)} memories, {len(scan.overlays)} overlays, "
                  f"{len(scan.chat_media)} chat media, {len(scan.unknown_files)} unknown")

    if scan.unknown_files:
        console.rule("[bold yellow]Step 7: Fix Types[/bold yellow]")
        renamed = fix_unknown_files(scan.unknown_files, verbose=config.verbose)
        console.print(f"Fixed {len(renamed)} unknown files")
        scan = scan_export(export_dir)

    # Runs before encoding so duplicates are never encoded twice
    dup_alias: dict[str, str] = {}
    if config.should_dedup():
        console.rule("[bold yellow]Step 8: Dedup[/bold yellow]")
        if checkpoint.is_step_done("dedup"):
            # The duplicates are gone, so hashing again would drop their aliases.
            dup_alias = checkpoint.dup_alias
            console.print(f"Already done ({len(dup_alias)} duplicates removed earlier)")
        else:
            all_paths = [mf.path for mf in scan.all_media]
            removed, freed, dup_alias = remove_duplicates(all_paths, dry_run=config.dry_run, verbose=config.verbose)
            if removed:
                console.print(f"Removed {removed} duplicates ({freed / (1024*1024):.1f} MB freed)")
                scan = scan_export(export_dir)
            else:
                console.print("No duplicates found")
            checkpoint.store_dup_alias(dup_alias)
            checkpoint.complete_step("dedup")

    # Also before encoding: voice messages become MP3, not H.265
    voice_files: list[Path] = []
    if config.should_process_media():
        console.rule("[bold yellow]Step 9: Voice Check[/bold yellow]")
        video_paths = [mf.path for mf in scan.all_media if mf.is_video]
        voice_files = detect_voice_messages(video_paths, ff)
        console.print(f"Detected {len(voice_files)} voice messages")
        # Remove voice messages from scan so they don't get encoded
        voice_set = set(voice_files)
        scan.memories = [mf for mf in scan.memories if mf.path not in voice_set]
        scan.chat_media = [mf for mf in scan.chat_media if mf.path not in voice_set]

    file_index: list[dict] = []
    if config.should_process_media():
        console.rule("[bold yellow]Step 10: Organize[/bold yellow]")

        files_to_organize = []
        if not config.has_only_filter or config.only_media or config.only_memories:
            files_to_organize.extend(scan.memories)
        if not config.has_only_filter or config.only_media or config.only_chat_media:
            files_to_organize.extend(scan.chat_media)

        if config.only_photos:
            files_to_organize = [f for f in files_to_organize if f.is_image]
        elif config.only_videos:
            files_to_organize = [f for f in files_to_organize if f.is_video]

        file_index = organize_into_folders(
            files_to_organize, output_dir,
            folder_structure=config.folder_structure,
            dry_run=config.dry_run,
            checkpoint=checkpoint,
        )
        console.print(f"Organized {len(file_index)} files")
        checkpoint.flush()

    if voice_files and config.should_process_media():
        console.rule("[bold yellow]Step 11: Voice Convert[/bold yellow]")
        from .scanner import MediaFile
        voice_media = []
        for vf in voice_files:
            from .utils import extract_date_from_filename
            date = extract_date_from_filename(vf.name) or "unknown"
            voice_media.append(MediaFile(
                path=vf, date=date, uuid=None, ext=".mp4",
                source="memory" if "memories" in str(vf) else "chat",
                original_name=vf.name,
            ))
        voice_index = organize_into_folders(
            voice_media, output_dir,
            folder_structure=config.folder_structure,
            dry_run=config.dry_run,
            checkpoint=checkpoint,
            step="organize-voice",
        )
        voice_dest_paths = [Path(e["dest"]) for e in voice_index]
        converted = convert_voice_messages(voice_dest_paths, ff, dry_run=config.dry_run, verbose=config.verbose,
                                           checkpoint=checkpoint)
        console.print(f"Converted {converted} voice messages to MP3")
        checkpoint.flush()

        for entry in voice_index:
            entry["type"] = "audio"
            entry["ext"] = ".mp3"
            mp3_name = Path(entry["new_name"]).stem + ".mp3"
            entry["new_name"] = mp3_name
            entry["dest"] = str(Path(entry["dest"]).with_suffix(".mp3"))
        file_index.extend(voice_index)

    overlay_burned_names: set[str] = set()
    if config.should_overlay() and scan.overlays:
        console.rule("[bold yellow]Step 12: Overlay[/bold yellow]")
        matched, unmatched = match_overlays(scan.memories, scan.overlays)
        console.print(f"Matched: {len(matched)}, Unmatched: {len(unmatched)}")

        burned = burn_overlays(matched, file_index, output_dir, ff, dry_run=config.dry_run, verbose=config.verbose,
                               checkpoint=checkpoint)
        console.print(f"Burned {burned} overlays")
        checkpoint.flush()
        overlay_burned_names = {m.original_name for m, _ in matched}

        copy_unmatched_overlays(unmatched, output_dir, dry_run=config.dry_run)

    if config.should_encode():
        console.rule("[bold yellow]Step 13: Encode H.265[/bold yellow]")
        encoded = encode_videos(file_index, ff, overlay_burned_names, dry_run=config.dry_run, verbose=config.verbose,
                                checkpoint=checkpoint)
        console.print(f"Encoded {encoded} videos to H.265")
        checkpoint.flush()

    if config.should_exif():
        console.rule("[bold yellow]Step 14: EXIF/GPS[/bold yellow]")
        if not _done_already(checkpoint, "exif"):
            memories_history = json_data.get("memories_history", {}).get("Saved Media", [])
            if memories_history:
                written = apply_gps_metadata(file_index, memories_history, dry_run=config.dry_run)
                console.print(f"Wrote GPS to {written} images")
            checkpoint.complete_step("exif")

    # Step 15a: Manifest, records what ended up in the output folder so later
    # runs and `merge` can still tell where each file came from.
    own_username = _own_username(json_data)
    if file_index:
        media_map = build_media_id_map(file_index, dup_alias)
        # Persist the resolved IDs so a later --only-conversations run keeps the
        # media that dedup pointed at a different copy
        attach_media_ids(file_index, media_map)
        write_manifest(
            output_dir, file_index,
            own_username=own_username,
            sources=[z.name for z in zips] if zips else [],
            dry_run=config.dry_run,
        )
    else:
        # Media was skipped this run (e.g. --only-conversations): fall back to
        # the manifest of a previous run so media can still be resolved.
        existing = load_manifest(output_dir)
        if existing:
            file_index = manifest_to_file_index(existing, output_dir)
            if file_index:
                console.print(f"Loaded {len(file_index)} files from existing manifest")
        media_map = build_media_id_map(file_index, dup_alias)

    if config.should_process_stickers():
        console.rule("[bold yellow]Step 15: Stickers[/bold yellow]")
        if not _done_already(checkpoint, "stickers"):
            stickers_data = json_data.get("custom_sticker", {})
            sticker_list = stickers_data.get("My Custom Stickers", []) if isinstance(stickers_data, dict) else []
            sticker_files = []
            for s in sticker_list:
                if isinstance(s, dict) and s.get("Content"):
                    fname = s["Content"]
                    # Try json/ dir first, then root
                    for base in [export_dir / "json", export_dir]:
                        candidate = base / fname
                        if candidate.is_file():
                            sticker_files.append(candidate)
                            break
            if sticker_files and not config.dry_run:
                sticker_dir = output_dir / "_stickers"
                sticker_dir.mkdir(exist_ok=True)
                for sf in sticker_files:
                    shutil.copy2(str(sf), str(sticker_dir / sf.name))
            total = len(sticker_list)
            found = len(sticker_files)
            if found == 0 and total > 0:
                console.print(f"0 of {total} sticker files found in export (files not included by Snapchat)")
            else:
                console.print(f"Copied {found}/{total} stickers")
            checkpoint.complete_step("stickers")

    if config.should_process_conversations():
        console.rule("[bold yellow]Step 16: Conversations[/bold yellow]")
        if not _done_already(checkpoint, "conversations"):
            conv_count = generate_conversations(
                json_data, output_dir,
                conversation_format=config.conversation_format,
                conversations_for=config.conversations_for or None,
                min_messages=config.conversations_min_messages,
                media_map=media_map,
                dry_run=config.dry_run,
                verbose=config.verbose,
            )
            console.print(f"Generated {conv_count} conversation files")
            checkpoint.complete_step("conversations")

    if config.should_process_stats():
        console.rule("[bold yellow]Step 17: Stats[/bold yellow]")
        if not _done_already(checkpoint, "stats"):
            generate_stats_html(
                json_data, file_stats, output_dir,
                categories=config.stats_only_categories or None,
                dry_run=config.dry_run,
            )
            console.print("Generated stats.html")
            if config.conversation_format == "pdf" and not config.dry_run:
                render_single(output_dir / "stats.html")
            checkpoint.complete_step("stats")

    if config.should_process_map():
        console.rule("[bold yellow]Step 18: Snap Map[/bold yellow]")
        if not _done_already(checkpoint, "map"):
            if generate_map_html(json_data, output_dir, file_index=file_index or None, dry_run=config.dry_run):
                console.print("Generated map.html")
            checkpoint.complete_step("map")

    if config.should_index() and file_index:
        console.rule("[bold yellow]Step 19: Index[/bold yellow]")
        if not _done_already(checkpoint, "index"):
            generate_index_html(file_index, output_dir, json_data=json_data, dry_run=config.dry_run)
            checkpoint.complete_step("index")

    if config.should_process_meta():
        console.rule("[bold yellow]Step 20: Meta[/bold yellow]")
        if not _done_already(checkpoint, "meta"):
            meta_dir = output_dir / "_meta"
            if not config.dry_run:
                # includes sticker PNGs and everything else Snapchat put there
                json_src = export_dir / "json"
                if json_src.is_dir():
                    meta_json = meta_dir / "json"
                    meta_json.mkdir(parents=True, exist_ok=True)
                    for f in json_src.iterdir():
                        if f.is_file():
                            shutil.copy2(str(f), str(meta_json / f.name))

                html_src = export_dir / "html"
                if html_src.is_dir():
                    meta_html = meta_dir / "html"
                    if meta_html.exists():
                        shutil.rmtree(meta_html)
                    shutil.copytree(str(html_src), str(meta_html))

            if config.dry_run:
                console.print("Would copy raw metadata to _meta/")
            else:
                console.print("Copied raw metadata to _meta/")
            checkpoint.complete_step("meta")

    console.rule("[bold yellow]Step 21: Cleanup[/bold yellow]")
    removed = cleanup_tmp_files(output_dir, verbose=config.verbose)
    console.print(f"Cleaned {removed} tmp files")

    # Reached only when every step went through, so nothing is left to resume.
    if not config.dry_run:
        checkpoint.remove()

    if zips and export_dir and "snapexport_" in str(export_dir):
        shutil.rmtree(export_dir, ignore_errors=True)

    # Clean flag: drop the bulky raw HTML export but keep the manifest and the
    # raw JSONs, without those a later `merge` cannot rebuild conversations,
    # stats or the map.
    if config.clean and not config.dry_run:
        meta_html = output_dir / "_meta" / "html"
        if meta_html.exists():
            freed = sum(f.stat().st_size for f in meta_html.rglob("*") if f.is_file())
            shutil.rmtree(meta_html, ignore_errors=True)
            console.print(f"Cleaned _meta/html/ ({freed / (1024*1024):.1f} MB) - kept manifest and JSON data")

    console.rule("[bold green]Done![/bold green]")
    console.print(f"Output: {output_dir}")
