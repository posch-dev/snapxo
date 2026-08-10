import json
import zipfile
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .utils import IMAGE_EXTS, VIDEO_EXTS

console = Console()


def find_export_inputs(inputs: list[Path]) -> tuple[list[Path], Path | None]:
    # Returns (zip_files, extracted_dir).
    zips = []
    extracted = None

    for inp in inputs:
        if inp.is_file() and inp.suffix.lower() == ".zip":
            # Named explicitly, so take it as given and let validation complain later
            zips.append(inp)
        elif inp.is_dir():
            # Scanning a directory (e.g. Downloads) may turn up unrelated ZIPs,
            # so only keep the ones that actually look like Snapchat exports.
            dir_zips = sorted(f for f in inp.iterdir() if f.is_file() and f.suffix.lower() == ".zip")
            valid_zips = [z for z in dir_zips if validate_zip(z)]
            skipped = len(dir_zips) - len(valid_zips)
            if skipped:
                console.print(f"[dim]{inp}: ignored {skipped} ZIP(s) that are not Snapchat exports[/dim]")
            if valid_zips:
                zips.extend(valid_zips)
            elif (inp / "json").is_dir() or (inp / "memories").is_dir() or (inp / "chat_media").is_dir():
                extracted = inp
            elif any(inp.glob("*.json")):
                # Directory with JSON files directly (e.g. _meta/json/)
                extracted = inp
            else:
                console.print(f"[yellow]Warning: {inp} has no ZIPs or export data[/yellow]")

    return zips, extracted


def validate_zip(zip_path: Path) -> bool:
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            has_memories = any("memories/" in n for n in names)
            has_json = any("json/" in n for n in names)
            has_chat_media = any("chat_media/" in n for n in names)
            return has_memories or has_json or has_chat_media
    except zipfile.BadZipFile:
        return False


def inspect_zip(zip_path: Path) -> dict:
    stats = {
        "images": 0, "videos": 0, "overlays": 0,
        "chat_media_img": 0, "chat_media_vid": 0, "chat_media_other": 0,
        "json_files": [], "html_files": 0,
        "total_size": 0,
    }

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            ext = Path(name).suffix.lower()
            stats["total_size"] += info.file_size

            if "/memories/" in name or name.startswith("memories/"):
                if "overlay" in name.lower():
                    stats["overlays"] += 1
                elif ext in IMAGE_EXTS:
                    stats["images"] += 1
                elif ext in VIDEO_EXTS:
                    stats["videos"] += 1
            elif "/chat_media/" in name or name.startswith("chat_media/"):
                if ext in IMAGE_EXTS:
                    stats["chat_media_img"] += 1
                elif ext in VIDEO_EXTS:
                    stats["chat_media_vid"] += 1
                else:
                    stats["chat_media_other"] += 1
            elif ("/json/" in name or name.startswith("json/")) and ext == ".json":
                stats["json_files"].append(Path(name).name)

    return stats


def inspect_directory(export_dir: Path) -> dict:
    stats = {
        "images": 0, "videos": 0, "overlays": 0,
        "chat_media_img": 0, "chat_media_vid": 0, "chat_media_other": 0,
        "json_files": [], "html_files": 0,
        "total_size": 0,
    }

    memories_dir = export_dir / "memories"
    if memories_dir.is_dir():
        for f in memories_dir.iterdir():
            if f.is_file():
                ext = f.suffix.lower()
                stats["total_size"] += f.stat().st_size
                if "overlay" in f.name.lower():
                    stats["overlays"] += 1
                elif ext in IMAGE_EXTS:
                    stats["images"] += 1
                elif ext in VIDEO_EXTS:
                    stats["videos"] += 1

    chat_dir = export_dir / "chat_media"
    if chat_dir.is_dir():
        for f in chat_dir.iterdir():
            if f.is_file():
                ext = f.suffix.lower()
                stats["total_size"] += f.stat().st_size
                if ext in IMAGE_EXTS:
                    stats["chat_media_img"] += 1
                elif ext in VIDEO_EXTS:
                    stats["chat_media_vid"] += 1
                else:
                    stats["chat_media_other"] += 1

    json_dir = export_dir / "json"
    if json_dir.is_dir():
        for f in json_dir.iterdir():
            if f.suffix.lower() == ".json":
                stats["json_files"].append(f.name)

    return stats


def load_json_data(export_dir: Path) -> dict:
    data = {}
    json_dir = export_dir / "json"
    if json_dir.is_dir():
        search_dir = json_dir
    elif any(export_dir.glob("*.json")):
        # JSON files directly in the directory (e.g. _meta/json/)
        search_dir = export_dir
    else:
        return data

    for f in search_dir.iterdir():
        if f.suffix.lower() == ".json":
            try:
                with open(f, encoding="utf-8") as fh:
                    data[f.stem] = json.load(fh)
            except (json.JSONDecodeError, UnicodeDecodeError):
                console.print(f"[yellow]Warning: Could not parse {f.name}[/yellow]")

    return data


def count_json_stats(json_data: dict) -> dict:
    # Counts for the summary. Export format as of August 2026:
    #   chat_history            {username: [messages]}, keys are usernames or group UUIDs
    #   friends                 {Friends, Blocked Users, Deleted Friends}
    #   talk_history            {Outgoing Calls, Incoming Calls, Completed Calls}
    #   location_history        {Location History: [["timestamp", "lat, lon"]]}
    #   memories_history        {Saved Media: [{Date, Media Type, Location}]}
    #   snap_map_places_history {Snap Map Places History: [{Date, Place, Place Location}]}
    #   search_history          {"": [{Date and time (hourly), Search Term, Location}]}
    #   custom_sticker          {My Custom Stickers: [{Created, Sticker ID, Content}]}
    #   ranking                 {Statistics: {Snapscore}}
    stats = {}

    # Chat history: keys are usernames, values are message lists
    chat = json_data.get("chat_history", {})
    if isinstance(chat, dict):
        msg_count = 0
        text_count = 0
        for messages in chat.values():
            if isinstance(messages, list):
                msg_count += len(messages)
                for m in messages:
                    if isinstance(m, dict) and m.get("Content"):
                        text_count += 1
        stats["conversations"] = len(chat)
        stats["messages"] = msg_count
        stats["messages_with_text"] = text_count

    # Friends
    friends = json_data.get("friends", {})
    if isinstance(friends, dict):
        stats["friends"] = len(friends.get("Friends", []))
        stats["blocked"] = len(friends.get("Blocked Users", []))
        stats["deleted"] = len(friends.get("Deleted Friends", []))

    # Location
    location = json_data.get("location_history", {})
    if isinstance(location, dict):
        loc_entries = location.get("Location History", [])
        stats["locations"] = len(loc_entries) if isinstance(loc_entries, list) else 0

    # Snap Map
    snap_map = json_data.get("snap_map_places_history", {})
    if isinstance(snap_map, dict):
        places = snap_map.get("Snap Map Places History", [])
        stats["snap_map_places"] = len(places) if isinstance(places, list) else 0

    # Calls: combine all call types
    talk = json_data.get("talk_history", {})
    if isinstance(talk, dict):
        total_calls = 0
        for key in ("Outgoing Calls", "Incoming Calls", "Completed Calls"):
            calls = talk.get(key, [])
            if isinstance(calls, list):
                total_calls += len(calls)
        stats["calls"] = total_calls

    # Search: the key is the empty string ""
    search = json_data.get("search_history", {})
    if isinstance(search, dict):
        entries = search.get("", [])
        stats["search"] = len(entries) if isinstance(entries, list) else 0

    # Stickers
    stickers = json_data.get("custom_sticker", {})
    if isinstance(stickers, dict):
        sticker_list = stickers.get("My Custom Stickers", [])
        stats["stickers"] = len(sticker_list) if isinstance(sticker_list, list) else 0

    # Memories metadata
    memories = json_data.get("memories_history", {})
    if isinstance(memories, dict):
        saved = memories.get("Saved Media", [])
        stats["memories_entries"] = len(saved) if isinstance(saved, list) else 0

    return stats


def display_summary(file_stats: dict, json_stats: dict, zip_names: list[str] | None = None):
    title = "Snapchat Export"
    if zip_names:
        title = " + ".join(zip_names) + " (Snapchat Export)"

    lines = []
    lines.append("[bold]Media:[/bold]")
    lines.append(f"  {file_stats['images']} Images (JPG/PNG/WEBP)")
    lines.append(f"  {file_stats['videos']} Videos (MP4/MOV)")
    lines.append(f"  {file_stats['overlays']} Overlays")

    chat_total = file_stats["chat_media_img"] + file_stats["chat_media_vid"] + file_stats["chat_media_other"]
    if chat_total:
        lines.append(f"  {chat_total} Chat Media ({file_stats['chat_media_img']} IMG, "
                     f"{file_stats['chat_media_vid']} VID, {file_stats['chat_media_other']} other)")

    from .utils import format_size
    lines.append(f"  Total: ~{format_size(file_stats['total_size'])}")

    lines.append("")
    lines.append("[bold]Data:[/bold]")

    if "conversations" in json_stats:
        text_pct = 0
        if json_stats.get("messages", 0) > 0:
            text_pct = int(json_stats["messages_with_text"] / json_stats["messages"] * 100)
        lines.append(f"  {json_stats['conversations']} Conversations "
                     f"({json_stats['messages']} messages, {text_pct}% with text)")

    friends_parts = []
    if "friends" in json_stats:
        friends_parts.append(f"{json_stats['friends']} Friends")
    if "blocked" in json_stats:
        friends_parts.append(f"{json_stats['blocked']} Blocked")
    if "deleted" in json_stats:
        friends_parts.append(f"{json_stats['deleted']} Deleted")
    if friends_parts:
        lines.append(f"  {', '.join(friends_parts)}")

    loc_parts = []
    if "locations" in json_stats:
        loc_parts.append(f"{json_stats['locations']} Location entries")
    if "snap_map_places" in json_stats:
        loc_parts.append(f"{json_stats['snap_map_places']} Snap Map places")
    if loc_parts:
        lines.append(f"  {', '.join(loc_parts)}")

    if "calls" in json_stats:
        lines.append(f"  {json_stats['calls']} Calls")
    if "search" in json_stats:
        lines.append(f"  {json_stats['search']} Search entries")
    if "stickers" in json_stats:
        lines.append(f"  {json_stats['stickers']} Custom Stickers")

    lines.append("  Account, Stories, Spotlight, Bitmoji, Ads, AI")

    text = Text.from_markup("\n".join(lines))
    console.print(Panel(text, title=title, border_style="yellow"))
