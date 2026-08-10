import html
import re
from pathlib import Path

from rich.console import Console

from .webassets import (
    date_format_css,
    date_format_js,
    date_format_picker_html,
    date_span,
    split_timestamp,
)

console = Console()

LOCATION_RE = re.compile(r"Latitude,\s*Longitude:\s*([-\d.]+),\s*([-\d.]+)")

_CARD_EMOJIS: dict[str, str] = {
    "Friends": "\U0001f465",
    "Blocked": "\U0001f6ab",
    "Deleted": "\U0001f5d1\ufe0f",
    "Calls": "\U0001f4de",
    "Locations": "\U0001f4cd",
    "Snap Map Places": "\U0001f5fa\ufe0f",
    "Searches": "\U0001f50d",
    "Sticker": "\u2b50",
    "Account": "\U0001f464",
    "Snapscore": "\U0001f3c6",
    "Memories": "\U0001f4f8",
    "Chat Media": "\U0001f4ac",
    "Overlays": "\U0001f3a8",
}


def _card(label: str, value) -> str:
    emoji = _CARD_EMOJIS.get(label, "")
    prefix = f"{emoji} " if emoji else ""
    return f'<div class="card"><div class="card-value">{value}</div><div class="card-label">{prefix}{html.escape(label)}</div></div>'


def _cell(value) -> str:
    # Render a table cell, tagging timestamps so the date picker can rewrite them.
    text = str(value)
    date_part, time_part = split_timestamp(text)
    if date_part:
        return f"<td>{date_span(date_part, time_part)}</td>"
    return f"<td>{html.escape(text)}</td>"


def _detail_table(title: str, headers: list[str], rows: list[list[str]], id_: str) -> str:
    thead = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    tbody = ""
    for row in rows:
        cells = "".join(_cell(c) for c in row)
        tbody += f"<tr>{cells}</tr>\n"

    return f'''
<details id="{id_}">
<summary>{html.escape(title)} ({len(rows)})</summary>
<div style="overflow-x:auto"><table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>
</details>'''


def generate_stats_html(
    json_data: dict,
    file_stats: dict,
    output_dir: Path,
    categories: list[str] | None = None,
    dry_run: bool = False,
) -> bool:
    if dry_run:
        return True

    cards = []
    details = []

    cards.append(_card("Memories", file_stats.get("images", 0) + file_stats.get("videos", 0)))
    cards.append(_card("Chat Media", file_stats.get("chat_media_img", 0) + file_stats.get("chat_media_vid", 0)))
    cards.append(_card("Overlays", file_stats.get("overlays", 0)))

    friends_data = json_data.get("friends", {})
    if isinstance(friends_data, dict) and (not categories or "friends" in categories):
        friend_list = friends_data.get("Friends", [])
        cards.append(_card("Friends", len(friend_list)))

        rows = []
        for f in friend_list:
            if isinstance(f, dict):
                rows.append([
                    f.get("Username", ""),
                    f.get("Display Name", ""),
                    f.get("Source", ""),
                    f.get("Creation Timestamp", "")[:10] if f.get("Creation Timestamp") else "",
                ])
        if rows:
            details.append(_detail_table("Friends", ["Username", "Display Name", "Source", "Date"], rows, "friends"))

        blocked = friends_data.get("Blocked Users", [])
        cards.append(_card("Blocked", len(blocked)))
        if blocked:
            rows = []
            for b in blocked:
                if isinstance(b, dict):
                    rows.append([b.get("Username", ""), b.get("Creation Timestamp", "")[:10] if b.get("Creation Timestamp") else ""])
            if rows:
                details.append(_detail_table("Blocked", ["Username", "Date"], rows, "blocked"))

        deleted = friends_data.get("Deleted Friends", [])
        cards.append(_card("Deleted", len(deleted)))
        if deleted:
            rows = []
            for d in deleted:
                if isinstance(d, dict):
                    rows.append([d.get("Username", ""), d.get("Creation Timestamp", "")[:10] if d.get("Creation Timestamp") else ""])
            if rows:
                details.append(_detail_table("Deleted", ["Username", "Date"], rows, "deleted"))

    # Calls: Outgoing, Incoming, Completed
    talk = json_data.get("talk_history", {})
    if isinstance(talk, dict) and (not categories or "calls" in categories):
        all_calls = []
        for key in ("Outgoing Calls", "Incoming Calls", "Completed Calls"):
            calls = talk.get(key, [])
            if isinstance(calls, list):
                for c in calls:
                    if isinstance(c, dict):
                        all_calls.append((key, c))

        cards.append(_card("Calls", len(all_calls)))
        if all_calls:
            rows = []
            for _call_type, c in all_calls:
                rows.append([
                    c.get("Date & Time", "")[:16],
                    c.get("Type", ""),
                    str(c.get("Length (sec)", "")),
                    f"{c.get('City', '')}, {c.get('Country', '')}".strip(", "),
                    c.get("Network", ""),
                ])
            details.append(_detail_table("Calls", ["Date", "Typ", "Duration (s)", "Location", "Network"], rows, "calls"))

    location = json_data.get("location_history", {})
    if isinstance(location, dict) and (not categories or "locations" in categories):
        loc_list = location.get("Location History", [])
        loc_count = len(loc_list) if isinstance(loc_list, list) else 0
        cards.append(_card("Locations", loc_count))

        if isinstance(loc_list, list) and loc_list:
            rows = []
            for entry in loc_list[:200]:  # Limit for display
                if isinstance(entry, list) and len(entry) == 2:
                    rows.append([entry[0][:16], entry[1]])
            if rows:
                details.append(_detail_table("Locations", ["Date", "Coordinates"], rows, "locations"))

    snap_map = json_data.get("snap_map_places_history", {})
    if isinstance(snap_map, dict) and (not categories or "locations" in categories):
        places = snap_map.get("Snap Map Places History", [])
        cards.append(_card("Snap Map Places", len(places) if isinstance(places, list) else 0))
        if isinstance(places, list) and places:
            rows = []
            for p in places:
                if isinstance(p, dict):
                    rows.append([
                        p.get("Date", "")[:16] if p.get("Date") else "",
                        p.get("Place", ""),
                        p.get("Place Location", ""),
                    ])
            if rows:
                details.append(_detail_table("Snap Map Places", ["Date", "Place", "Location"], rows, "snapmap"))

    # Search: the key is the empty string ""
    search = json_data.get("search_history", {})
    if isinstance(search, dict) and (not categories or "search" in categories):
        entries = search.get("", [])
        cards.append(_card("Searches", len(entries) if isinstance(entries, list) else 0))
        if isinstance(entries, list) and entries:
            rows = []
            for s in entries:
                if isinstance(s, dict):
                    rows.append([
                        s.get("Date and time (hourly)", "")[:16],
                        s.get("Search Term", ""),
                        s.get("Location", ""),
                    ])
            if rows:
                details.append(_detail_table("Search History", ["Date", "Search Term", "Location"], rows, "search"))

    stickers = json_data.get("custom_sticker", {})
    if isinstance(stickers, dict) and (not categories or "stickers" in categories):
        sticker_list = stickers.get("My Custom Stickers", [])
        cards.append(_card("Sticker", len(sticker_list) if isinstance(sticker_list, list) else 0))

    account = json_data.get("account", {})
    if isinstance(account, dict) and (not categories or "account" in categories):
        basic = account.get("Basic Information", {})
        if isinstance(basic, dict):
            username = basic.get("Username", "")
            if username:
                cards.append(_card("Account", username))

    ranking = json_data.get("ranking", {})
    if isinstance(ranking, dict) and (not categories or "engagement" in categories):
        stats_data = ranking.get("Statistics", {})
        if isinstance(stats_data, dict):
            snapscore = stats_data.get("Snapscore", "")
            if snapscore:
                # Clean up "128258.0" -> "128258"
                try:
                    snapscore = str(int(float(snapscore)))
                except (ValueError, TypeError):
                    pass
                cards.append(_card("Snapscore", snapscore))

    cards_html = "\n".join(cards)
    details_html = "\n".join(details)
    picker_css = date_format_css()
    picker_html = date_format_picker_html()
    picker_js = date_format_js()

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Snapchat Export Stats</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a1a; color: #e0e0e0; padding: 20px; border-top: 4px solid #FFFE00; }}
h1 {{ text-align: center; margin: 20px 0 30px; color: #FFFE00; font-size: 24px; text-shadow: 0 0 20px rgba(255, 254, 0, 0.3); }}
.header-bar {{ display: flex; justify-content: flex-end; align-items: center; gap: 12px; margin-bottom: 8px; }}
.btn-print {{ background: #FFFE00; color: #1a1a1a; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; font-size: 13px; cursor: pointer; }}
.btn-print:hover {{ background: #e6e500; }}
.cards {{ display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; margin-bottom: 30px; }}
.card {{ background: #2a2a2a; border-radius: 10px; padding: 16px 24px; text-align: center; min-width: 130px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
.card-value {{ font-size: 28px; font-weight: 700; color: #FFFE00; }}
.card-label {{ font-size: 13px; color: #aaa; margin-top: 4px; }}
details {{ background: #222; border-radius: 8px; margin: 10px 0; }}
summary {{ padding: 12px 16px; cursor: pointer; font-weight: 600; color: #ddd; }}
summary:hover {{ color: #FFFE00; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 8px 12px; background: #333; color: #aaa; border-bottom: 1px solid #444; }}
td {{ padding: 6px 12px; border-bottom: 1px solid #2a2a2a; }}
tr:hover {{ background: #2a2a2a; }}
@media (max-width: 600px) {{
  .cards {{ gap: 8px; }}
  .card {{ flex: 1 1 calc(50% - 8px); min-width: 0; padding: 12px 10px; }}
  .card-value {{ font-size: 22px; }}
  summary {{ padding: 16px; }}
  table {{ font-size: 12px; }}
}}
@media print {{
  body {{ background: #fff; color: #000; border-top: none; }}
  .card {{ border: 1px solid #ccc; box-shadow: none; }}
  .card-value {{ color: #000; }}
  summary {{ color: #000; }}
  details {{ break-inside: avoid; }}
  .no-print {{ display: none; }}
}}
{picker_css}
</style>
</head>
<body>
<div class="header-bar no-print">{picker_html}<button class="btn-print" onclick="window.print()">Export PDF</button></div>
<h1>Snapchat Export Stats</h1>
<div class="cards">{cards_html}</div>
{details_html}
<script>{picker_js}</script>
</body>
</html>'''

    (output_dir / "stats.html").write_text(page, encoding="utf-8")
    return True
