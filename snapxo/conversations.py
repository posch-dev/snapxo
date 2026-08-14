import hashlib
import html
from contextlib import nullcontext
from pathlib import Path

from rich.console import Console

from .chats import PREVIEW_CHARS, SEARCH_CHARS, generate_chats_html, message_anchor
from .pdf import PdfRenderer
from .webassets import (
    date_format_css,
    date_format_js,
    date_format_picker_html,
    date_span,
    split_timestamp,
)

console = Console()

GROUP_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
    "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
    "#BB8FCE", "#85C1E9",
]

OWN_COLOR = "#FF0000"
OTHER_COLOR = "#00BFFF"

STATUS_TYPES = {
    "STATUS", "STATUSCALLMISSEDAUDIO", "STATUSCALLMISSEDVIDEO",
    "STATUSCALLENDEDAUDIO", "STATUSCALLENDEDVIDEO",
    "STATUSERASEDMESSAGE", "STATUSSAVETOCAMERAROLL",
}

SNAP_TYPES = {"SNAP", "SNAPSAVED"}
CALL_TYPES = {
    "STATUSCALLMISSEDAUDIO", "STATUSCALLMISSEDVIDEO",
    "STATUSCALLENDEDAUDIO", "STATUSCALLENDEDVIDEO",
}

COLLAPSIBLE_TYPES = SNAP_TYPES | CALL_TYPES


def _user_color(username: str, is_group: bool) -> str:
    if not is_group:
        return OTHER_COLOR
    h = int(hashlib.md5(username.encode()).hexdigest(), 16)
    return GROUP_COLORS[h % len(GROUP_COLORS)]


def _ts_html(ts_str: str, css_class: str = "ts") -> str:
    # Render "2026-07-20 14:32:05 UTC" so the date format picker can rewrite it.
    date_part, time_part = split_timestamp(ts_str)
    if not date_part:
        return f'<span class="{css_class}">{html.escape(ts_str)}</span>'
    return date_span(date_part, time_part, extra_class=css_class)


def _has_real_content(messages: list[dict]) -> bool:
    # True if the chat has anything beyond system messages and unsaved placeholders.
    for msg in messages:
        mt = msg.get("media_type", "TEXT").upper()
        if mt in STATUS_TYPES:
            continue
        if mt == "TEXT" and msg.get("text"):
            return True
        if mt in ("MEDIA", "STICKER", "NOTE", "SHARE", "SHARESAVEDSTORY"):
            return True
        if mt in SNAP_TYPES:
            return True
    return False


def _parse_conversations(json_data: dict, own_username: str | None = None) -> dict[str, list[dict]]:
    # Parse chat_history.json into {contact: [messages]}.
    chat = json_data.get("chat_history", {})
    conversations: dict[str, list[dict]] = {}

    if not isinstance(chat, dict):
        return conversations

    for contact, messages in chat.items():
        if not isinstance(messages, list):
            continue

        parsed = []
        for entry in messages:
            if not isinstance(entry, dict):
                continue
            sender = entry.get("From", "")
            is_own = bool(entry.get("IsSender", False))
            parsed.append({
                "sender": sender,
                "is_own": is_own,
                "text": entry.get("Content") or "",
                "media_type": entry.get("Media Type", "TEXT"),
                "timestamp": entry.get("Created", ""),
                "conversation_title": entry.get("Conversation Title"),
                "media_ids": entry.get("Media IDs", ""),
            })

        parsed.sort(key=lambda m: m["timestamp"])
        conversations[contact] = parsed

    return conversations


def _filter_by_date(conversations: dict[str, list[dict]], since: str | None, until: str | None) -> dict[str, list[dict]]:
    # Timestamps read "2026-07-20 14:32:05 UTC", both bounds inclusive.
    filtered = {}
    for contact, messages in conversations.items():
        kept = []
        for msg in messages:
            day = str(msg.get("timestamp", ""))[:10]
            if len(day) == 10:
                if since and day < since:
                    continue
                if until and day > until:
                    continue
            kept.append(msg)
        if kept:
            filtered[contact] = kept
    return filtered


def _resolve_media(msg: dict, media_map: dict[str, dict]) -> list[dict]:
    # Look up the files a message refers to. A Media ID is the chat_media filename
    # minus date prefix and extension, so this is exact, no date guessing.
    # Several attachments are separated by " | ".
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
    # Path relative to the output root, e.g. "2026/2026-07-20_0142.mp4".
    subfolder = entry.get("subfolder") or entry.get("year") or "unknown"
    return f"{subfolder}/{entry.get('new_name', '')}"


def _damaged_note(entry: dict) -> str:
    bad = entry.get("integrity")
    if not isinstance(bad, dict) or not bad.get("reason"):
        return ""
    return f'<div class="damaged-note">This file arrived damaged ({html.escape(bad["reason"])})</div>'


def _media_html(entry: dict, pdf_mode: bool = False) -> str:
    # Render one attachment. Conversations live in conversations/, so links go one
    # level up. PDFs get images embedded and video or audio as a link, since a PDF
    # cannot play media.
    rel = _media_rel_path(entry)
    href = html.escape(f"../{rel}")
    label = html.escape(rel)
    ftype = entry.get("type", "")
    note = _damaged_note(entry)

    if ftype == "image":
        # Lazy loading is right for the browser but wrong for PDF: images below
        # the viewport would never load and end up missing from the document.
        lazy = "" if pdf_mode else ' loading="lazy"'
        return (f'<div class="msg-media"><a href="{href}" target="_blank">'
                f'<img src="{href}"{lazy} alt="{label}"></a>{note}</div>')

    if pdf_mode:
        icon = "&#127916;" if ftype == "video" else "&#127908;"
        return f'<div class="msg-media-link">{icon} <a href="{href}">{label}</a>{note}</div>'

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


def generate_conversation_html(
    contact: str,
    messages: list[dict],
    own_username: str | None = None,
    is_group: bool = False,
    conversation_title: str | None = None,
    media_map: dict[str, dict] | None = None,
    pdf_mode: bool = False,
) -> str:
    own_name = own_username or "Me"

    display_contact = conversation_title or contact
    if is_group and not conversation_title:
        for m in messages:
            if m.get("conversation_title"):
                display_contact = m["conversation_title"]
                break

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
            body_parts.append(f'<div class="sender" style="color:{color}">{html.escape(display)}</div><hr style="border-color:{color}; opacity:0.3">')
            last_sender = sender

        ts = _ts_html(msg["timestamp"])
        text = msg["text"]
        # Anchor so a search hit in chats.html can jump straight to the message
        at = f' id="{message_anchor(i)}"'

        if media_type == "TEXT" and text:
            body_parts.append(f'<div{at} class="msg">{html.escape(text)} {ts}</div>')
        elif media_type == "TEXT" and not text:
            body_parts.append(f'<div{at} class="msg" style="color:#666">[Message not saved] {ts}</div>')
        elif media_type in ("MEDIA", "NOTE"):
            attachments = _resolve_media(msg, media_map)
            if attachments:
                body_parts.append(f'<div{at} class="msg">{ts}</div>')
                for entry in attachments:
                    body_parts.append(_media_html(entry, pdf_mode))
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

    body_html = "\n".join(body_parts)
    title = html.escape(display_contact)

    real_count = sum(1 for m in messages if m["media_type"].upper() not in STATUS_TYPES)

    picker_css = date_format_css()
    picker_html = date_format_picker_html()
    picker_js = date_format_js()

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chat: {title}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #000; color: #fff; padding: 20px; max-width: 700px; margin: 0 auto; }}
h1 {{ text-align: center; margin: 20px 0 10px; color: #FFFE00; font-size: 20px; }}
.subtitle {{ text-align: center; color: #888; margin-bottom: 20px; font-size: 14px; }}
.sender {{ font-weight: 700; font-size: 14px; margin-top: 16px; padding-top: 8px; }}
hr {{ border: none; border-top: 1px solid; margin: 2px 0 6px; }}
.msg {{ padding: 4px 0; font-size: 15px; line-height: 1.4; }}
.ts {{ color: #888; font-size: 11px; margin-left: 8px; }}
.ts-inline {{ color: inherit; font-size: inherit; }}
.msg-media-link {{ margin: 6px 0; font-size: 13px; word-break: break-all; }}
.damaged-note {{ color: #c9a227; font-size: 11px; margin-top: 2px; }}
.top-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 12px; }}
.system-msg {{ text-align: center; color: #888; font-size: 13px; padding: 8px 0; font-style: italic; }}
.media {{ color: #aaa; }}
.snap {{ color: #aaa; }}
.msg-media {{ margin: 6px 0; }}
.msg-media img {{ max-width: 100%; max-height: 400px; border-radius: 8px; display: block; }}
.msg-media video {{ max-width: 100%; max-height: 400px; border-radius: 8px; display: block; }}
.msg-media audio {{ width: 100%; margin: 4px 0; }}
.collapsed {{ background: #111; border-radius: 8px; padding: 10px 14px; margin: 8px 0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
.collapsed:hover {{ background: #1a1a1a; }}
.collapsed-label {{ color: #ccc; font-size: 13px; }}
.collapsed-toggle {{ color: #888; font-size: 12px; }}
a {{ color: #FFFE00; }}
.back-link {{ text-align: center; margin-bottom: 20px; }}
@media print {{
    body {{ background: #fff; color: #000; }}
    .sender {{ color: #333 !important; }}
    hr {{ border-color: #ccc !important; }}
    .ts {{ color: #666; }}
    .system-msg {{ color: #666; }}
    .no-print {{ display: none; }}
}}
{picker_css}
</style>
</head>
<body>
<div class="top-bar no-print">
<span class="back-link"><a href="../index.html">&larr; Back</a></span>
{picker_html}
</div>
<h1>Chat: {title}</h1>
<p class="subtitle">{real_count} messages</p>
{body_html}
<script>{picker_js}</script>
</body>
</html>'''


def generate_conversations(
    json_data: dict,
    output_dir: Path,
    conversation_format: str = "html",
    conversations_for: list[str] | None = None,
    min_messages: int = 1,
    media_map: dict[str, dict] | None = None,
    since: str | None = None,
    until: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    account = json_data.get("account", {})
    own_username = None
    if isinstance(account, dict):
        basic = account.get("Basic Information", {})
        if isinstance(basic, dict):
            own_username = basic.get("Username")

    conversations = _parse_conversations(json_data, own_username)
    if since or until:
        conversations = _filter_by_date(conversations, since, until)

    conv_dir = output_dir / "conversations"
    if not dry_run:
        conv_dir.mkdir(exist_ok=True)

    want_pdf = conversation_format == "pdf" and not dry_run
    # One browser for all conversations instead of one process per file
    with (PdfRenderer() if want_pdf else nullcontext()) as renderer:
        generated, skipped_empty, embedded, records = _render_all(
            conversations, conv_dir, output_dir, own_username,
            conversation_format, conversations_for, min_messages,
            media_map, dry_run, renderer, verbose,
        )

    if skipped_empty:
        console.print(f"  Skipped {skipped_empty} empty conversations (no real content)")
    if embedded:
        console.print(f"  Embedded {embedded} media files matched by Media ID")

    generate_chats_html(records, output_dir, dry_run=dry_run)

    return generated


def _render_all(
    conversations: dict[str, list[dict]],
    conv_dir: Path,
    output_dir: Path,
    own_username: str | None,
    conversation_format: str,
    conversations_for: list[str] | None,
    min_messages: int,
    media_map: dict[str, dict] | None,
    dry_run: bool,
    renderer,
    verbose: bool,
) -> tuple[int, int, int, list[dict]]:
    generated = 0
    skipped_empty = 0
    embedded = 0
    records: list[dict] = []
    for contact, messages in sorted(conversations.items()):
        if len(messages) < min_messages:
            continue
        if conversations_for and contact not in conversations_for:
            continue

        if not _has_real_content(messages):
            skipped_empty += 1
            continue

        # Detect groups: UUID-style contact names or multiple non-own senders
        is_group = bool(len(contact) == 36 and contact.count("-") == 4)
        if not is_group:
            senders = {m["sender"] for m in messages if not m["is_own"]}
            is_group = len(senders) > 1

        conv_title = None
        for m in messages:
            if m.get("conversation_title"):
                conv_title = m["conversation_title"]
                break

        if is_group and conv_title:
            safe_name = "group_" + conv_title.lower().replace(" ", "-").replace("/", "_").replace("\\", "_")
        elif is_group:
            safe_name = f"group_{contact}"
        else:
            safe_name = contact

        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in safe_name)
        filename = f"{safe_name}.html"

        if dry_run:
            generated += 1
            if verbose:
                display = conv_title or contact
                console.print(f"  [dim]Would generate {filename} ({len(messages)} msgs) - {display}[/dim]")
            continue

        embedded += sum(len(_resolve_media(m, media_map or {})) for m in messages)

        content = generate_conversation_html(
            contact, messages, own_username, is_group, conv_title,
            media_map=media_map, pdf_mode=(conversation_format == "pdf"),
        )

        if renderer is not None:
            _write_pdf(content, conv_dir / safe_name, renderer)
        else:
            (conv_dir / filename).write_text(content, encoding="utf-8")

        records.append(_chat_record(
            conv_title or contact, is_group, messages,
            f"conversations/{safe_name}.pdf" if renderer is not None else f"conversations/{filename}",
        ))

        generated += 1
        if verbose:
            display = conv_title or contact
            real_count = sum(1 for m in messages if m["media_type"].upper() not in STATUS_TYPES)
            console.print(f"  [cyan][{generated}][/cyan] {filename}")
            console.print(f"    [dim]{real_count} messages - {display}[/dim]")

    return generated, skipped_empty, embedded, records


def _chat_record(title: str, is_group: bool, messages: list[dict], rel_file: str) -> dict:
    # One entry for chats.html: the list row plus the searchable text of the chat.
    real = [m for m in messages if m["media_type"].upper() not in STATUS_TYPES]
    index = []
    for i, msg in enumerate(messages):
        text = (msg.get("text") or "").strip()
        if not text or msg["media_type"].upper() in STATUS_TYPES:
            continue
        index.append({"a": message_anchor(i), "s": msg["sender"], "t": msg["timestamp"],
                      "x": text[:SEARCH_CHARS]})

    preview = ""
    for msg in reversed(real):
        if msg.get("text"):
            preview = msg["text"][:PREVIEW_CHARS]
            break
        preview = {"MEDIA": "[Media]", "NOTE": "[Voice note]"}.get(msg["media_type"].upper(), "[Snap]")
        break

    return {
        "title": title,
        "file": rel_file,
        "is_group": is_group,
        "messages": len(real),
        "last": real[-1]["timestamp"] if real else "",
        "preview": preview,
        "index": index,
    }


def _write_pdf(html_content: str, base_path: Path, renderer):
    # Write the HTML next to the PDF and render it. Builds the name as parent + name
    # instead of `.with_suffix()`, which eats everything after a dot in `john.doe`.
    html_path = base_path.parent / (base_path.name + ".html")
    html_path.write_text(html_content, encoding="utf-8")

    pdf_path = base_path.parent / (base_path.name + ".pdf")
    renderer.render(html_path, pdf_path)
