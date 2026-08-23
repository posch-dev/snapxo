from pathlib import Path


def count_overlays(folder: Path) -> int:
    overlay_dir = folder / "_overlays"
    if not overlay_dir.is_dir():
        return 0
    return sum(1 for entry in overlay_dir.iterdir() if entry.is_file())


def summarize_file_index(file_index: list[dict], overlay_count: int = 0) -> dict:
    summary = {
        "images": 0, "videos": 0, "overlays": overlay_count,
        "chat_media_img": 0, "chat_media_vid": 0, "chat_media_other": 0,
        "json_files": [], "html_files": 0, "total_size": 0,
    }
    for entry in file_index:
        summary["total_size"] += entry.get("size") or 0
        is_chat_media = entry.get("source") == "chat"
        if entry["type"] == "image":
            summary["chat_media_img" if is_chat_media else "images"] += 1
        elif entry["type"] == "video":
            summary["chat_media_vid" if is_chat_media else "videos"] += 1
        else:
            summary["chat_media_other"] += 1
    return summary


def summarize_folder(folder: Path, file_index: list[dict]) -> dict:
    return summarize_file_index(file_index, count_overlays(folder))
