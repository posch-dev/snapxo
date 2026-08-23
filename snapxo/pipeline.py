import shutil
import tempfile
from pathlib import Path

from rich.console import Console

from .app.shell import generate_app
from .archive.checkpoint import Checkpoint, config_fingerprint
from .archive.cleanup import cleanup_tmp_files
from .archive.manifest import (
    attach_media_ids,
    build_media_id_map,
    load_manifest,
    manifest_to_file_index,
    write_manifest,
)
from .archive.verify import verify_folder, write_checksums
from .clock import load_zone, localize
from .config import Config
from .media.dedup import remove_duplicates
from .media.encoder import encode_videos
from .media.mediainfo import attach as attach_media_info
from .media.metadata import apply_file_times, apply_gps_metadata
from .media.organizer import organize_into_folders
from .media.overlay import burn_overlays, copy_unmatched_overlays, match_overlays
from .media.thumbs import build_thumbnails
from .media.voice import convert_voice_messages, detect_voice_messages
from .pages.snapmap import generate_map_html
from .read.fixtypes import fix_unknown_files
from .read.inspector import (
    count_json_stats,
    display_summary,
    find_export_inputs,
    inspect_directory,
    inspect_zip,
    load_json_data,
    validate_zip,
)
from .read.scanner import scan_export
from .read.zips import GIB, SPACE_MARGIN, free_space, looks_like_zip_bomb, safe_extract, zip_payload
from .selection import SOURCES, TYPES
from .tools.deps import require_ffmpeg
from .tools.ffmpeg import FFmpeg

console = Console()


def _check_external_tools(config: Config, ff: FFmpeg) -> None:
    if config.should_encode() or config.should_overlay():
        require_ffmpeg(ff)

    selection = config.selection
    if not selection.needs_voice_detection or ff.check():
        return

    # has_video_stream() answers True whenever ffprobe cannot be run, so without
    # it every voice message counts as a real video and nothing is found.
    if not selection.wants_type("videos"):
        console.print("[red]--types voice needs ffprobe to tell a voice message apart "
                      "from a video. Without it nothing would be found.[/red]")
        require_ffmpeg(ff)

    console.print("[yellow]Without ffprobe the voice messages cannot be told apart from "
                  "videos, so they stay MP4 video files instead of becoming MP3.[/yellow]")


def _check_zip_sizes(zips: list[Path], config: Config) -> None:
    total_uncompressed = 0
    for z in zips:
        uncompressed, compressed = zip_payload(z)
        total_uncompressed += uncompressed
        if looks_like_zip_bomb(uncompressed, compressed):
            ratio = uncompressed / compressed if compressed else 0
            console.print(f"[red]{z.name} unpacks to {uncompressed / GIB:.1f} GB from "
                          f"{compressed / GIB:.2f} GB ({ratio:.0f}x).[/red]")
            console.print("[red]That is not what a Snapchat export looks like. Refusing to extract.[/red]")
            raise SystemExit(1)

    needed = int(total_uncompressed * SPACE_MARGIN)
    targets = {Path(tempfile.gettempdir())}
    if config.output:
        targets.add(config.output)
    for target in targets:
        available = free_space(target)
        if 0 <= available < needed:
            console.print(f"[red]Not enough space on {target}: {available / GIB:.1f} GB free, "
                          f"about {needed / GIB:.1f} GB needed.[/red]")
            raise SystemExit(1)


def _done_already(checkpoint, step: str) -> bool:
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


OPTIONAL_STEPS = [
    ("encode",  "Encode videos to H.265"),
    ("overlay", "Burn overlays onto the media"),
    ("exif",    "Write EXIF and GPS into the images"),
    ("dedup",   "Remove duplicates"),
    ("meta",    "Copy the raw export to _meta/ (rebuild and merge need it)"),
]


def _voice_wanted(path: Path, selection) -> bool:
    # A voice message keeps the source it was found in, so --media still applies.
    source = "memories" if "memories" in str(path).lower() else "chat"
    return selection.wants_source(source)


SOURCE_LABELS = {"memories": "Memories, the ones you saved yourself",
                 "chat": "Chat media, everything sent in a conversation"}
TYPE_LABELS = {"photos": "Photos", "videos": "Videos", "voice": "Voice messages"}


def _ask_for_numbers(console: Console, question: str, labels: list[str]) -> set[int]:
    console.print(f"\n[bold]{question}[/bold]")
    for number, label in enumerate(labels, 1):
        console.print(f"  [yellow]{number:2d}[/yellow] {label}")
    console.print("  [dim]Enter for all of them[/dim]")

    response = console.input("\n[bold]Numbers, comma separated: [/bold]").strip()
    if not response:
        return set(range(1, len(labels) + 1))

    try:
        picked = {int(part.strip()) for part in response.split(",") if part.strip()}
    except ValueError:
        console.print("[red]Those are not numbers.[/red]")
        raise SystemExit(1) from None

    if not picked & set(range(1, len(labels) + 1)):
        console.print("[red]Nothing picked.[/red]")
        raise SystemExit(1)
    return picked


def _pick_names(console: Console, question: str, names: tuple[str, ...],
                labels: dict[str, str]) -> list[str]:
    wanted = _ask_for_numbers(console, question, [labels[name] for name in names])
    picked = [name for number, name in enumerate(names, 1) if number in wanted]
    return [] if len(picked) == len(names) else picked


def _interactive_select(config: Config, console: Console):
    # Media first: answering "photos only" makes the encoding question pointless.
    config.media_sources = _pick_names(console, "Which media should be copied?",
                                       SOURCES, SOURCE_LABELS)
    config.media_types = _pick_names(console, "Which kinds?", TYPES, TYPE_LABELS)

    running = _ask_for_numbers(console, "Which steps should run?",
                               [label for _key, label in OPTIONAL_STEPS])
    chosen = {key for number, (key, _) in enumerate(OPTIONAL_STEPS, 1) if number in running}

    config.no_encode = "encode" not in chosen
    config.no_overlay = "overlay" not in chosen
    config.no_exif = "exif" not in chosen
    config.no_dedup = "dedup" not in chosen
    config.no_meta = "meta" not in chosen

    console.print(f"\n[green]Copying {config.selection.describe()}[/green]\n")


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

    if not config.output and not (config.info or config.dry_run):
        console.print("[red]No output directory set (-o/--output).[/red]")
        raise SystemExit(1)

    # --info and --dry-run run without -o, against a folder never written to.
    output_dir = config.output or Path("snapxo-dry-run")
    console.print(f"Output: {output_dir}" if config.output else "Output: none (nothing is written)")

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

    # Before extraction, so a missing ffmpeg is reported without unpacking 6 GB first.
    ff = FFmpeg(
        ffmpeg_path=config.ffmpeg_path,
        ffprobe_path=config.ffprobe_path,
        software_encoding=config.software_encoding,
        crf=config.crf,
    )
    # Only when flags already settle the run; interactive may still deselect steps.
    if config.yes and not config.info:
        _check_external_tools(config, ff)

    extract_problems: list[dict] = []
    if extracted_dir:
        export_dir = extracted_dir
    elif zips:
        _check_zip_sizes(zips, config)
        export_dir = Path(tempfile.mkdtemp(prefix="snapexport_"))
        console.rule("[bold yellow]Step 4: Extract[/bold yellow]")
        for z in zips:
            console.print(f"Extracting {z.name}...")
            written, problems = safe_extract(z, export_dir, verbose=config.verbose)
            extract_problems.extend(problems)
            console.print(f"  Extracted {written} files")
        if extract_problems:
            console.print(f"[yellow]Skipped {len(extract_problems)} unsafe or unreadable entries:[/yellow]")
            for p in extract_problems[:10]:
                console.print(f"  [yellow]{p['entry']}: {p['reason']}[/yellow]")
            if len(extract_problems) > 10:
                console.print(f"  [yellow]... and {len(extract_problems) - 10} more[/yellow]")
    else:
        raise SystemExit(1)

    if extracted_dir:
        file_stats = inspect_directory(extracted_dir)

    json_data = load_json_data(export_dir)
    zone = load_zone(config.timezone)
    if zone is not None:
        json_data = localize(json_data, zone)
        console.print(f"Timestamps converted to {config.timezone}")
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

    # Before encoding, so duplicates are never encoded twice.
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

    selection = config.selection

    # Also before encoding: voice messages become MP3, not H.265. They arrive as
    # MP4 without a picture, so every video has to be opened to tell them apart.
    voice_files: list[Path] = []
    if selection.needs_voice_detection:
        console.rule("[bold yellow]Step 9: Voice Check[/bold yellow]")
        video_paths = [mf.path for mf in scan.all_media if mf.is_video]
        voice_files = detect_voice_messages(video_paths, ff)
        console.print(f"Detected {len(voice_files)} voice messages")
        # Out of the scan either way, so they are never encoded as video.
        voice_set = set(voice_files)
        scan.memories = [mf for mf in scan.memories if mf.path not in voice_set]
        scan.chat_media = [mf for mf in scan.chat_media if mf.path not in voice_set]
    voice_files = [f for f in voice_files if _voice_wanted(f, selection)]

    console.rule("[bold yellow]Step 10: Organize[/bold yellow]")

    files_to_organize = []
    if selection.wants_source("memories"):
        files_to_organize.extend(scan.memories)
    if selection.wants_source("chat"):
        files_to_organize.extend(scan.chat_media)

    if not selection.wants_type("photos"):
        files_to_organize = [f for f in files_to_organize if not f.is_image]
    if not selection.wants_type("videos"):
        files_to_organize = [f for f in files_to_organize if not f.is_video]

    if config.since or config.until:
        before = len(files_to_organize)
        files_to_organize = [f for f in files_to_organize if config.in_date_range(f.date)]
        console.print(f"Date range keeps {len(files_to_organize)} of {before} files")

    file_index = organize_into_folders(
        files_to_organize, output_dir,
        folder_structure=config.folder_structure,
        dry_run=config.dry_run,
        checkpoint=checkpoint,
    )
    console.print(f"Organized {len(file_index)} files")
    checkpoint.flush()

    if voice_files:
        console.rule("[bold yellow]Step 11: Voice Convert[/bold yellow]")
        from .read.scanner import MediaFile
        voice_media = []
        for vf in voice_files:
            from .filenames import extract_date_from_filename
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

    if file_index:
        console.rule("[bold yellow]Step 15: File dates[/bold yellow]")
        if not _done_already(checkpoint, "filetimes"):
            touched = apply_file_times(file_index, dry_run=config.dry_run)
            console.print(f"Set the file date on {touched} files")
            checkpoint.complete_step("filetimes")

    own_username = _own_username(json_data)
    if file_index:
        media_map = build_media_id_map(file_index, dup_alias)
        # Persisted, so a later narrowed run keeps the media dedup pointed elsewhere.
        attach_media_ids(file_index, media_map)
        write_manifest(
            output_dir, file_index,
            own_username=own_username,
            sources=[z.name for z in zips] if zips else [],
            timezone_name=config.timezone,
            dry_run=config.dry_run,
        )
    else:
        # Nothing copied this run, so an earlier manifest still resolves the media.
        existing = load_manifest(output_dir)
        if existing:
            file_index = manifest_to_file_index(existing, output_dir)
            if file_index:
                console.print(f"Loaded {len(file_index)} files from existing manifest")
        media_map = build_media_id_map(file_index, dup_alias)

    # The app embeds these, so they come before the pages.
    thumbs: dict[int, str] = {}
    if file_index:
        console.rule("[bold yellow]Step 16: Thumbnails[/bold yellow]")
        attach_media_info(file_index, ff=ff if ff.check() else None, verbose=config.verbose)
        thumbs = build_thumbnails(file_index, output_dir, ff=ff if ff.check() else None,
                                  dry_run=config.dry_run, verbose=config.verbose)

    console.rule("[bold yellow]Step 17: Snap Map[/bold yellow]")
    if not _done_already(checkpoint, "map"):
        if generate_map_html(json_data, output_dir, file_index=file_index or None,
                             dry_run=config.dry_run):
            console.print("Generated map.html")
        checkpoint.complete_step("map")

    console.rule("[bold yellow]Step 18: Pages[/bold yellow]")
    if not _done_already(checkpoint, "index"):
        generate_app(output_dir, json_data, file_index, file_stats,
                     thumbs=thumbs, media_map=media_map, dry_run=config.dry_run)
        checkpoint.complete_step("index")

    if config.should_process_meta():
        console.rule("[bold yellow]Step 21: Meta[/bold yellow]")
        if not _done_already(checkpoint, "meta"):
            meta_dir = output_dir / "_meta"
            if not config.dry_run:
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

    if not config.no_checksums and not config.dry_run and file_index:
        console.rule("[bold yellow]Step 22: Checksums[/bold yellow]")
        _, computed = verify_folder(output_dir, hashes=True)
        if write_checksums(output_dir, computed):
            console.print(f"Fingerprinted {len(computed)} files for later `snapxo verify` runs")

    console.rule("[bold yellow]Step 23: Cleanup[/bold yellow]")
    removed = cleanup_tmp_files(output_dir, verbose=config.verbose)
    console.print(f"Cleaned {removed} tmp files")

    # Reached only when every step went through, so nothing is left to resume.
    if not config.dry_run:
        checkpoint.remove()

    if zips and export_dir and "snapexport_" in str(export_dir):
        shutil.rmtree(export_dir, ignore_errors=True)

    # A second rendering of what the JSONs already hold, read by nothing here and
    # the bulky part. The manifest and the raw JSONs always stay.
    if not config.keep_raw_html and not config.dry_run:
        meta_html = output_dir / "_meta" / "html"
        if meta_html.exists():
            freed = sum(f.stat().st_size for f in meta_html.rglob("*") if f.is_file())
            shutil.rmtree(meta_html, ignore_errors=True)
            console.print(f"Cleaned _meta/html/ ({freed / (1024*1024):.1f} MB) - kept manifest and JSON data")

    console.rule("[bold green]Done![/bold green]")
    console.print(f"Output: {output_dir}")
