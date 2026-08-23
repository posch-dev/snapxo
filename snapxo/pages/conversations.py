import html
from pathlib import Path

from rich.console import Console

from ..facts.people import display_names, group_name, name_for, participants_of
from ..facts.provenance import COVER_CSS
from ..parts.messages import build_conversation_body, resolve_media
from ..parts.shared import (
    PREVIEW_CHARS,
    SEARCH_CHARS,
    date_format_css,
    date_format_js,
    date_format_picker_html,
    message_anchor,
)
from ..snapchat import SNAP_TYPES, STATUS_TYPES
from .chatlist import generate_chats_html

console = Console()





def _has_real_content(messages: list[dict]) -> bool:
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
    # Both bounds inclusive.
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






def generate_conversation_html(
    contact: str,
    messages: list[dict],
    own_username: str | None = None,
    is_group: bool = False,
    conversation_title: str | None = None,
    media_map: dict[str, dict] | None = None,
    pdf_mode: bool = False,
    cover: str = "",
) -> str:
    display_contact = conversation_title or contact
    if is_group and not conversation_title:
        for m in messages:
            if m.get("conversation_title"):
                display_contact = m["conversation_title"]
                break

    body_html = build_conversation_body(messages, own_username, is_group, media_map, pdf_mode)
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
.media-facts {{ display: none; }}
.media-still {{ display: none; }}
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
    body {{ background: #fff; color: #000; max-width: none; padding: 0; }}
    .sender {{ color: var(--sender-print) !important; }}
    hr {{ border-color: var(--sender-print) !important; opacity: 0.55 !important; }}
    .ts {{ color: #666; }}
    .system-msg {{ color: #666; }}
    a {{ color: #333; }}
    /* Media on the left, its details in a box beside it. */
    .msg-media {{ break-inside: avoid; display: flex; align-items: flex-start; gap: 5mm; margin: 3mm 0; }}
    .msg-media a, .media-still {{ flex: 0 1 auto; max-width: 62%; }}
    .msg-media img {{ max-height: 90mm; width: auto; border-radius: 2mm; }}
    .media-still {{ display: inline-block; position: relative; }}
    .media-still.empty {{ display: flex; align-items: center; justify-content: center; width: 34mm; height: 26mm; background: #f0f0f0; border: 0.5pt solid #ccc; border-radius: 2mm; font-size: 16pt; color: #888; }}
    .play-mark {{ position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 11mm; height: 11mm; border-radius: 50%; background: rgba(0,0,0,0.55); color: #fff; font-size: 12pt; display: flex; align-items: center; justify-content: center; }}
    .media-facts {{ display: block; flex: 1 1 auto; border-left: 0.5pt solid #ccc; padding-left: 4mm; }}
    .media-facts dl {{ display: grid; grid-template-columns: 20mm 1fr; gap: 0.6mm 2mm; font-size: 7.5pt; }}
    .media-facts dt {{ color: #777; }}
    .media-facts dd {{ color: #222; word-break: break-word; }}
    .no-print {{ display: none; }}
}}
{picker_css}
{COVER_CSS}
</style>
</head>
<body>
<div class="top-bar no-print">
<span class="back-link"><a href="../index.html">&larr; Back</a></span>
{picker_html}
</div>
{cover}
<h1 class="no-print">Chat: {title}</h1>
<p class="subtitle no-print">{real_count} messages</p>
{body_html}
<script>{picker_js}</script>
</body>
</html>'''


def generate_conversations(
    json_data: dict,
    output_dir: Path,
    conversations_for: list[str] | None = None,
    min_messages: int = 1,
    media_map: dict[str, dict] | None = None,
    since: str | None = None,
    until: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    own_username = own_username_of(json_data)
    prepared, skipped_empty = prepare_conversations(
        json_data, conversations_for, min_messages, since, until,
    )

    conv_dir = output_dir / "conversations"
    if not dry_run:
        conv_dir.mkdir(exist_ok=True)

    generated, embedded, records = _render_all(
        prepared, conv_dir, own_username, media_map, dry_run, verbose,
    )

    if skipped_empty:
        console.print(f"  Skipped {skipped_empty} empty conversations (no real content)")
    if embedded:
        console.print(f"  Embedded {embedded} media files matched by Media ID")

    generate_chats_html(records, output_dir, dry_run=dry_run)

    return generated


def own_username_of(json_data: dict) -> str | None:
    account = json_data.get("account", {})
    if not isinstance(account, dict):
        return None
    basic = account.get("Basic Information", {})
    return basic.get("Username") if isinstance(basic, dict) else None


def _is_group(contact: str, messages: list[dict], conversation_title: str | None) -> bool:
    # Several senders only count as a group together with a title: someone who
    # renamed themselves is two senders in a one to one chat as well.
    if len(contact) == 36 and contact.count("-") == 4:
        return True
    senders = {m["sender"] for m in messages if not m["is_own"]}
    return len(senders) > 1 and bool(conversation_title)


def _conversation_title_of(messages: list[dict]) -> str | None:
    for message in messages:
        if message.get("conversation_title"):
            return message["conversation_title"]
    return None


def _safe_name(contact: str, is_group: bool, conversation_title: str | None) -> str:
    if is_group and conversation_title:
        raw = "group_" + conversation_title.lower().replace(" ", "-").replace("/", "_").replace("\\", "_")
    elif is_group:
        raw = f"group_{contact}"
    else:
        raw = contact
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in raw)


def prepare_conversations(
    json_data: dict,
    conversations_for: list[str] | None = None,
    min_messages: int = 1,
    since: str | None = None,
    until: str | None = None,
) -> tuple[list[dict], int]:
    own_username = own_username_of(json_data)
    names = display_names(json_data)
    conversations = _parse_conversations(json_data, own_username)
    if since or until:
        conversations = _filter_by_date(conversations, since, until)

    prepared = []
    skipped_empty = 0
    for contact, messages in sorted(conversations.items()):
        if len(messages) < min_messages:
            continue
        if conversations_for and contact not in conversations_for:
            continue
        if not _has_real_content(messages):
            skipped_empty += 1
            continue

        conversation_title = _conversation_title_of(messages)
        is_group = _is_group(contact, messages, conversation_title)
        members = participants_of(messages, own_username) if is_group else []

        if is_group:
            title = conversation_title or group_name(members, names)
            secondary = f"{len(members)} people" if members else "Group"
        else:
            title = name_for(contact, names)
            secondary = contact if title != contact else ""

        prepared.append({
            "contact": contact,
            "title": title,
            "secondary": secondary,
            "conversation_title": conversation_title,
            "is_group": is_group,
            "participants": members,
            "messages": messages,
            "safe_name": _safe_name(contact, is_group, conversation_title),
        })
    return prepared, skipped_empty


def _render_all(
    prepared: list[dict],
    conv_dir: Path,
    own_username: str | None,
    media_map: dict[str, dict] | None,
    dry_run: bool,
    verbose: bool,
) -> tuple[int, int, list[dict]]:
    generated = 0
    embedded = 0
    records: list[dict] = []

    for chat in prepared:
        messages = chat["messages"]
        filename = f"{chat['safe_name']}.html"

        if dry_run:
            generated += 1
            if verbose:
                console.print(f"  [dim]Would generate {filename} ({len(messages)} msgs) - {chat['title']}[/dim]")
            continue

        embedded += sum(len(resolve_media(m, media_map or {})) for m in messages)

        content = generate_conversation_html(
            chat["contact"], messages, own_username, chat["is_group"],
            chat["conversation_title"], media_map=media_map,
        )

        (conv_dir / filename).write_text(content, encoding="utf-8")

        records.append(build_chat_record(
            chat["title"], chat["is_group"], messages, f"conversations/{filename}",
            secondary=chat["secondary"],
        ))

        generated += 1
        if verbose:
            real_count = sum(1 for m in messages if m["media_type"].upper() not in STATUS_TYPES)
            console.print(f"  [cyan][{generated}][/cyan] {filename}")
            console.print(f"    [dim]{real_count} messages - {chat['title']}[/dim]")

    return generated, embedded, records


def build_chat_record(title: str, is_group: bool, messages: list[dict], rel_file: str,
                      secondary: str = "") -> dict:
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
        "secondary": secondary,
        "file": rel_file,
        "is_group": is_group,
        "messages": len(real),
        "last": real[-1]["timestamp"] if real else "",
        "preview": preview,
        "index": index,
    }
