# JavaScript rather than JSON, because a page opened from disk cannot fetch.

import json
from pathlib import Path

from rich.console import Console

from ..pages.conversations import build_chat_record, own_username_of, prepare_conversations
from ..parts.messages import build_conversation_body

console = Console()

DATA_DIR = "_meta"
CHATS_DATA_FILE = "app-chats.js"
MEDIA_DATA_FILE = "app-media.js"
STATS_DATA_FILE = "app-stats.js"


def _as_script(variable: str, payload: dict) -> str:
    # </ inside a string literal would end the surrounding script tag early.
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"window.{variable}={encoded};\n"


def _write_data_file(output_dir: Path, name: str, variable: str, payload: dict) -> int:
    target = output_dir / DATA_DIR / name
    target.parent.mkdir(parents=True, exist_ok=True)
    script = _as_script(variable, payload)
    target.write_text(script, encoding="utf-8")
    return len(script.encode("utf-8"))


def build_chats_payload(json_data: dict, media_map: dict[str, dict] | None = None) -> dict:
    own_username = own_username_of(json_data)
    prepared, _ = prepare_conversations(json_data)

    chats = []
    for chat in prepared:
        record = build_chat_record(chat["title"], chat["is_group"], chat["messages"], "",
                                   secondary=chat["secondary"])
        chats.append({
            "t": record["title"],
            "u": record["secondary"],
            "n": record["messages"],
            "d": record["last"],
            "p": record["preview"],
            "g": record["is_group"],
            "b": build_conversation_body(
                chat["messages"], own_username, chat["is_group"],
                media_map=media_map, path_prefix="",
            ),
            "x": record["index"],
        })

    chats.sort(key=lambda chat: chat["d"], reverse=True)
    return {"chats": chats}


def write_chats_data(output_dir: Path, json_data: dict, media_map: dict[str, dict] | None = None,
                     dry_run: bool = False) -> dict:
    if dry_run:
        return {"chats": []}
    payload = build_chats_payload(json_data, media_map)
    written = _write_data_file(output_dir, CHATS_DATA_FILE, "SNAPXO_CHATS", payload)
    if payload["chats"]:
        console.print(f"  Generated {DATA_DIR}/{CHATS_DATA_FILE} "
                      f"({len(payload['chats'])} chats, {written // 1024} KB)")
    return payload


def build_media_payload(file_index: list[dict], thumbs: dict[int, str],
                        details: dict[str, dict] | None = None) -> dict:
    # Newest first, so the Media tab can append while scrolling.
    details = details or {}
    items = []
    for position, entry in enumerate(file_index):
        subfolder = entry.get("subfolder") or entry.get("year") or "unknown"
        name = entry.get("new_name", "")
        if not name:
            continue
        items.append({
            "f": f"{subfolder}/{name}",
            "y": str(subfolder)[:4],
            "k": entry.get("type", ""),
            "d": entry.get("date", ""),
            "t": thumbs.get(position, ""),
            "i": f"f{position}",
            "b": bool(isinstance(entry.get("integrity"), dict)),
        })

    items.sort(key=lambda item: item["d"], reverse=True)
    return {"items": items, "details": details}


def write_media_data(output_dir: Path, file_index: list[dict], thumbs: dict[int, str] | None = None,
                     details: dict[str, dict] | None = None, dry_run: bool = False) -> int:
    if dry_run:
        return 0
    payload = build_media_payload(file_index, thumbs or {}, details)
    written = _write_data_file(output_dir, MEDIA_DATA_FILE, "SNAPXO_MEDIA", payload)
    if payload["items"]:
        console.print(f"  Generated {DATA_DIR}/{MEDIA_DATA_FILE} "
                      f"({len(payload['items'])} files, {written // 1024} KB)")
    return len(payload["items"])


def write_stats_data(output_dir: Path, datasets: list[dict], dry_run: bool = False) -> int:
    if dry_run:
        return 0
    _write_data_file(output_dir, STATS_DATA_FILE, "SNAPXO_STATS", {"datasets": datasets})
    return len(datasets)
