import hashlib
import html

from ..media.mediainfo import human_bitrate, human_duration
from ..parts.shared import date_span, message_anchor, split_timestamp
from ..snapchat import CALL_TYPES, SNAP_TYPES, STATUS_TYPES

GROUP_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
    "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
    "#BB8FCE", "#85C1E9",
]

OWN_COLOR = "#FF0000"
OTHER_COLOR = "#00BFFF"

COLLAPSIBLE_TYPES = SNAP_TYPES | CALL_TYPES


def _user_color(username: str, is_group: bool) -> str:
    if not is_group:
        return OTHER_COLOR
    h = int(hashlib.md5(username.encode()).hexdigest(), 16)
    return GROUP_COLORS[h % len(GROUP_COLORS)]


def darken(color: str, factor: float = 0.45) -> str:
    # Paper is white, so the screen colours would wash out. Same hue, less light.
    raw = color.lstrip("#")
    channels = (int(raw[i:i + 2], 16) for i in (0, 2, 4))
    return "#" + "".join(f"{int(value * factor):02x}" for value in channels)


def _ts_html(ts_str: str, css_class: str = "ts") -> str:
    date_part, time_part = split_timestamp(ts_str)
    if not date_part:
        return f'<span class="{css_class}">{html.escape(ts_str)}</span>'
    return date_span(date_part, time_part, extra_class=css_class)


def resolve_media(msg: dict, media_map: dict[str, dict]) -> list[dict]:
    # A Media ID is the chat_media filename minus date prefix and extension, so
    # this is exact. Several attachments are separated by " | ".
    raw = msg.get("media_ids") or ""
    entries = []
    for part in raw.split("|"):
        media_id = part.strip()
        if not media_id:
            continue
        entry = media_map.get(media_id)
        if entry:
            entries.append(entry)
    return entries


def _media_rel_path(entry: dict) -> str:
    subfolder = entry.get("subfolder") or entry.get("year") or "unknown"
    return f"{subfolder}/{entry.get('new_name', '')}"


def _damaged_note(entry: dict) -> str:
    bad = entry.get("integrity")
    if not isinstance(bad, dict) or not bad.get("reason"):
        return ""
    return f'<div class="damaged-note">This file arrived damaged ({html.escape(bad["reason"])})</div>'


def _attachment_facts(entry: dict) -> list[tuple[str, str]]:
    rows = [("File", _media_rel_path(entry))]
    measured = entry.get("media") or {}
    if measured.get("width") and measured.get("height"):
        rows.append(("Resolution", f'{measured["width"]}x{measured["height"]}'))
    if measured.get("duration"):
        rows.append(("Length", human_duration(measured["duration"])))
    if measured.get("codec"):
        rows.append(("Encoding", str(measured["codec"])))
    if measured.get("bitrate"):
        rows.append(("Bitrate", human_bitrate(measured["bitrate"])))
    if entry.get("size"):
        rows.append(("Size", _attachment_size(entry["size"])))
    return [(label, value) for label, value in rows if value]


def _attachment_size(size) -> str:
    if not isinstance(size, int):
        return ""
    if size < 1024 ** 2:
        return f"{size / 1024:.0f} KB"
    return f"{size / 1024 ** 2:.1f} MB"


def _attachment_box(entry: dict) -> str:
    rows = "".join(
        f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>"
        for label, value in _attachment_facts(entry)
    )
    return f'<aside class="media-facts"><dl>{rows}</dl></aside>'


def _media_html(entry: dict, pdf_mode: bool = False, path_prefix: str = "../") -> str:
    # path_prefix reaches the output root: "../" from conversations/, empty from
    # the app. A PDF cannot play media, so video and audio print as a still.
    rel = _media_rel_path(entry)
    href = html.escape(f"{path_prefix}{rel}")
    label = html.escape(rel)
    ftype = entry.get("type", "")
    note = _damaged_note(entry)
    facts = _attachment_box(entry) if pdf_mode else ""

    if ftype == "image":
        # Lazy in a PDF would leave everything below the viewport unloaded.
        lazy = "" if pdf_mode else ' loading="lazy"'
        # 320 px on screen, 1280 px in print, the original behind the link.
        preview = entry.get("medium") if pdf_mode else entry.get("thumb")
        src = html.escape(f"{path_prefix}{preview}") if preview else href
        return (f'<div class="msg-media"><a href="{href}" target="_blank">'
                f'<img src="{src}"{lazy} alt="{label}"></a>{facts}{note}</div>')

    if pdf_mode:
        preview = entry.get("thumb")
        if ftype == "video" and preview:
            still = (f'<span class="media-still"><img src="{html.escape(path_prefix + preview)}" '
                     f'alt="{label}"><span class="play-mark">&#9654;</span></span>')
        else:
            mark = "&#9835;" if ftype == "audio" else "&#127916;"
            still = f'<span class="media-still empty">{mark}</span>'
        return f'<div class="msg-media">{still}{facts}{note}</div>'

    if ftype == "video":
        return f'<div class="msg-media"><video src="{href}" controls preload="metadata"></video>{note}</div>'
    if ftype == "audio":
        return f'<div class="msg-media"><audio src="{href}" controls preload="metadata"></audio>{note}</div>'
    return f'<div class="msg-media-link"><a href="{href}" target="_blank">{label}</a>{note}</div>'


def _should_collapse(messages: list[dict], start: int) -> int:
    if start >= len(messages):
        return 0
    mt = messages[start]["media_type"].upper()
    if mt not in COLLAPSIBLE_TYPES:
        return 0
    count = 1
    while start + count < len(messages):
        next_mt = messages[start + count]["media_type"].upper()
        if next_mt not in COLLAPSIBLE_TYPES:
            break
        count += 1
    return count if count >= 2 else 0


def _render_collapsed(messages: list[dict], start: int, count: int) -> str:
    group = messages[start:start + count]
    first_raw = group[0]["timestamp"]
    last_raw = group[-1]["timestamp"]

    snap_count = sum(1 for m in group if m["media_type"].upper() in SNAP_TYPES)
    call_count = sum(1 for m in group if m["media_type"].upper() in CALL_TYPES)

    parts = []
    if snap_count:
        parts.append(f"&#128248; {snap_count} Snaps")
    if call_count:
        parts.append(f"&#128222; {call_count} Calls")

    label = " + ".join(parts)
    first_ts = _ts_html(first_raw, "ts-inline")
    if first_raw == last_raw:
        time_range = first_ts
    else:
        time_range = f"{first_ts} - {_ts_html(last_raw, 'ts-inline')}"

    return f'''<div class="collapsed" onclick="this.classList.toggle('open')">
        <span class="collapsed-label">{label} ({time_range})</span>
        <span class="collapsed-toggle">[expand]</span>
    </div>'''


def build_conversation_body(
    messages: list[dict],
    own_username: str | None = None,
    is_group: bool = False,
    media_map: dict[str, dict] | None = None,
    pdf_mode: bool = False,
    path_prefix: str = "../",
) -> str:
    # No page around them, so a chat file and the app's pane render identically.
    own_name = own_username or "Me"
    media_map = media_map or {}

    body_parts = []
    last_sender = None
    i = 0

    while i < len(messages):
        msg = messages[i]
        media_type = msg["media_type"].upper()

        collapse_count = _should_collapse(messages, i)
        if collapse_count > 0:
            body_parts.append(_render_collapsed(messages, i, collapse_count))
            i += collapse_count
            last_sender = None
            continue

        if media_type in STATUS_TYPES:
            text = msg["text"] or media_type.replace("STATUS", "").replace("ERASED", "deleted").replace("SAVETOCAMERAROLL", "saved")
            ts = _ts_html(msg["timestamp"])
            body_parts.append(f'<div class="system-msg">{html.escape(text)} {ts}</div>')
            last_sender = None
            i += 1
            continue

        sender = msg["sender"]
        if sender != last_sender:
            if msg["is_own"]:
                color = OWN_COLOR
                display = f"Me ({own_name})"
            else:
                color = _user_color(sender, is_group)
                display = sender
            # A custom property, so one markup is dark on screen and legible on
            # paper without a second render.
            tint = f"--sender:{color}; --sender-print:{darken(color)}"
            body_parts.append(
                f'<div class="sender" style="{tint}; color:var(--sender)">'
                f'{html.escape(display)}</div>'
                f'<hr style="{tint}; border-color:var(--sender); opacity:0.3">'
            )
            last_sender = sender

        ts = _ts_html(msg["timestamp"])
        text = msg["text"]
        at = f' id="{message_anchor(i)}"'

        if media_type == "TEXT" and text:
            body_parts.append(f'<div{at} class="msg">{html.escape(text)} {ts}</div>')
        elif media_type == "TEXT" and not text:
            body_parts.append(f'<div{at} class="msg" style="color:#666">[Message not saved] {ts}</div>')
        elif media_type in ("MEDIA", "NOTE"):
            attachments = resolve_media(msg, media_map)
            if attachments:
                body_parts.append(f'<div{at} class="msg">{ts}</div>')
                for entry in attachments:
                    body_parts.append(_media_html(entry, pdf_mode, path_prefix))
            else:
                placeholder = "[Voice Note]" if media_type == "NOTE" else "[Media]"
                body_parts.append(f'<div{at} class="msg media">{placeholder} {ts}</div>')
        elif media_type == "STICKER":
            body_parts.append(f'<div{at} class="msg">[Sticker] {ts}</div>')
        elif media_type in ("SHARE", "SHARESAVEDSTORY"):
            body_parts.append(f'<div{at} class="msg">[Shared] {html.escape(text)} {ts}</div>')
        elif media_type in SNAP_TYPES:
            body_parts.append(f'<div{at} class="msg snap">[Snap] {ts}</div>')
        else:
            display_text = html.escape(text) if text else f"[{media_type}]"
            body_parts.append(f'<div{at} class="msg">{display_text} {ts}</div>')

        i += 1

    return "\n".join(body_parts)
