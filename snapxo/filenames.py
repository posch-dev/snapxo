import re

UUID_RE = re.compile(r"[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}")
DATE_PREFIX_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_(.+)")


def extract_date_from_filename(name: str) -> str | None:
    match = DATE_PREFIX_RE.match(name)
    return match.group(1) if match else None


def extract_uuid_from_name(name: str) -> str | None:
    match = UUID_RE.search(name)
    return match.group(0) if match else None


def extract_media_id(name: str) -> str | None:
    # Named <date>_<media id><ext>, the id chat_history.json lists as "Media IDs".
    stem = name.rsplit(".", 1)[0] if "." in name else name
    match = DATE_PREFIX_RE.match(stem)
    return match.group(2) if match else None


def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', name)
