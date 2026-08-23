import html
import json
import re
from collections import defaultdict
from pathlib import Path

from rich.console import Console

from ..facts.provenance import COVER_CSS
from ..files import format_size
from ..media.mediainfo import human_bitrate, human_duration
from ..parts.details import DETAILS_CSS, DETAILS_JS, details_overlay_html
from ..parts.shared import (
    date_format_css,
    date_format_js,
    date_format_picker_html,
    date_span,
    split_timestamp,
)

console = Console()

LOCATION_RE = re.compile(r"Latitude,\s*Longitude:\s*([-\d.]+),\s*([-\d.]+)")


def _chat_info_by_media_id(json_data: dict) -> dict[str, dict]:
    # Chat media is the only case with an exact time and sender, because the
    # message carrying the file names it.
    info: dict[str, dict] = {}
    chat = json_data.get("chat_history", {})
    if not isinstance(chat, dict):
        return info

    for contact, messages in chat.items():
        if not isinstance(messages, list):
            continue
        for entry in messages:
            if not isinstance(entry, dict):
                continue
            raw_ids = entry.get("Media IDs") or ""
            if not raw_ids.strip():
                continue
            title = entry.get("Conversation Title") or contact
            _, time_part = split_timestamp(str(entry.get("Created", "")))
            for part in raw_ids.split("|"):
                media_id = part.strip()
                if media_id and media_id not in info:
                    info[media_id] = {
                        "time": time_part,
                        "sender": entry.get("From", ""),
                        "chat": title,
                    }
    return info


def _gps_by_date(json_data: dict) -> dict[str, list[dict]]:
    by_date: dict[str, list[dict]] = defaultdict(list)
    memories = json_data.get("memories_history", {})
    if not isinstance(memories, dict):
        return by_date

    for entry in memories.get("Saved Media", []):
        if not isinstance(entry, dict):
            continue
        m = LOCATION_RE.search(entry.get("Location", "") or "")
        if not m:
            continue
        try:
            lat, lon = float(m.group(1)), float(m.group(2))
        except ValueError:
            continue
        if lat == 0 and lon == 0:
            continue
        date_raw = str(entry.get("Date", ""))
        _, time_part = split_timestamp(date_raw)
        by_date[date_raw[:10]].append({"lat": lat, "lon": lon, "time": time_part})

    return by_date


def build_file_details(file_index: list[dict], json_data: dict | None) -> dict[str, dict]:
    # A memory can only be matched to its coordinates by date, so those are
    # flagged approximate whenever the day held more than one.
    chat_info = _chat_info_by_media_id(json_data or {})
    gps = _gps_by_date(json_data or {})

    details: dict[str, dict] = {}
    for i, entry in enumerate(file_index):
        subfolder = entry.get("subfolder") or entry.get("year") or "unknown"
        item = {
            "n": entry.get("new_name", ""),
            "o": entry.get("original_name", ""),
            "t": entry.get("type", ""),
            "d": entry.get("date", ""),
            "f": subfolder,
            "s": entry.get("size"),
            "src": entry.get("source", ""),
        }

        measured = entry.get("media")
        if isinstance(measured, dict) and measured:
            if measured.get("width") and measured.get("height"):
                item["px"] = f'{measured["width"]}x{measured["height"]}'
            if measured.get("codec"):
                item["cod"] = measured["codec"]
            if measured.get("duration"):
                item["len"] = human_duration(measured["duration"])
            if measured.get("bitrate"):
                item["br"] = human_bitrate(measured["bitrate"])

        damaged = entry.get("integrity")
        if isinstance(damaged, dict) and damaged.get("reason"):
            item["bad"] = damaged["reason"]

        media_id = entry.get("media_id")
        if media_id and media_id in chat_info:
            ci = chat_info[media_id]
            if ci["time"]:
                item["tm"] = ci["time"]
            if ci["sender"]:
                item["from"] = ci["sender"]
            if ci["chat"]:
                item["chat"] = ci["chat"]

        if entry.get("source") == "memory":
            candidates = gps.get(entry.get("date", ""), [])
            if candidates:
                item["lat"] = round(candidates[0]["lat"], 5)
                item["lon"] = round(candidates[0]["lon"], 5)
                item["approx"] = len(candidates) > 1
                if len(candidates) == 1 and candidates[0]["time"]:
                    item["tm"] = candidates[0]["time"]

        details[f"f{i}"] = item

    return details


PRINT_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, 'Segoe UI', sans-serif; background: #fff; color: #1a1a1a; font-size: 10pt; }
h1 { font-size: 20pt; margin-bottom: 4mm; }
h2 { font-size: 14pt; margin: 0 0 3mm; padding-bottom: 1.5mm; border-bottom: 1pt solid #999; }
.summary { color: #555; margin-bottom: 6mm; }
.year { break-before: page; }
.year:first-of-type { break-before: avoid; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; }
.item { break-inside: avoid; border: 0.5pt solid #ccc; border-radius: 2mm; overflow: hidden; }
.thumb-box { height: 40mm; background: #f0f0f0; display: flex; align-items: center; justify-content: center; }
.thumb-box img { width: 100%; height: 100%; object-fit: cover; display: block; }
.placeholder { color: #888; font-size: 9pt; text-align: center; padding: 2mm; }
.meta { padding: 2mm 2.5mm; }
.meta .name { font-weight: 600; font-size: 8.5pt; word-break: break-all; margin-bottom: 1mm; }
.meta dl { display: grid; grid-template-columns: 16mm 1fr; gap: 0.4mm 1.5mm; font-size: 7.5pt; }
.meta dt { color: #777; }
.meta dd { color: #222; word-break: break-word; }
.note { color: #8a6d00; }
@page { size: A4; margin: 12mm 10mm; }
"""


def build_print_index(
    file_index: list[dict],
    details: dict[str, dict],
    thumbs: dict[int, str] | None = None,
    cover: str = "",
) -> str:
    # No scripts and never lazy, or the PDF comes out without images.
    thumbs = thumbs or {}

    by_year: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for i, f in enumerate(file_index):
        by_year[f.get("subfolder", f.get("year", "unknown"))].append((i, f))

    n_vid = sum(1 for f in file_index if f.get("type") == "video")
    n_img = sum(1 for f in file_index if f.get("type") == "image")
    n_aud = sum(1 for f in file_index if f.get("type") == "audio")

    parts = ['<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
             '<title>Snapchat Memories</title>\n<style>' + PRINT_CSS + COVER_CSS +
             '</style>\n</head>\n<body>\n']
    parts.append(cover)
    parts.append('<h1>Snapchat Memories</h1>\n')
    parts.append(f'<div class="summary">{len(file_index)} files, {n_img} images, '
                 f'{n_vid} videos, {n_aud} voice messages</div>\n')

    type_labels = {"image": "Image", "video": "Video", "audio": "Voice message"}
    source_labels = {"memory": "Memory", "chat": "Chat media"}

    for year in sorted(by_year.keys(), reverse=True):
        items = by_year[year]
        parts.append(f'<section class="year"><h2>{html.escape(year)} ({len(items)} files)</h2>\n<div class="grid">\n')

        for idx, f in sorted(items, key=lambda x: x[1].get("date", "")):
            d = details.get(f"f{idx}", {})
            ftype = f.get("type", "")

            if idx in thumbs:
                box = f'<img src="{html.escape(thumbs[idx])}" alt="">'
            else:
                label = {"audio": "Voice message", "video": "Video"}.get(ftype, "No preview")
                box = f'<div class="placeholder">{label}</div>'

            rows = [("Date", _date_text(d)), ("Type", type_labels.get(ftype, ftype or "File")),
                    ("Source", source_labels.get(d.get("src", ""), d.get("src", "") or "unknown")),
                    ("Size", format_size(d.get("s")))]
            for label, key in (("Length", "len"), ("Resolution", "px"),
                               ("Encoding", "cod"), ("Bitrate", "br")):
                if d.get(key):
                    rows.append((label, d[key]))
            if d.get("from"):
                rows.append(("Sender", d["from"]))
            if d.get("chat"):
                rows.append(("Chat", d["chat"]))
            if d.get("lat") is not None:
                coords = f'{d["lat"]}, {d["lon"]}'
                if d.get("approx"):
                    coords += ' <span class="note">(approx.)</span>'
                rows.append(("Location", coords))
            if d.get("bad"):
                rows.append(("Damaged", f'<span class="note">{html.escape(d["bad"])} when it was merged in</span>'))
            if d.get("o") and d.get("o") != d.get("n"):
                rows.append(("Original", d["o"]))

            raw = {"Location", "Damaged"}
            dl = "".join(f"<dt>{k}</dt><dd>{v if k in raw else html.escape(str(v))}</dd>" for k, v in rows)
            parts.append(f'<div class="item"><div class="thumb-box">{box}</div>'
                         f'<div class="meta"><div class="name">{html.escape(d.get("n", ""))}</div>'
                         f'<dl>{dl}</dl></div></div>\n')

        parts.append('</div></section>\n')

    parts.append('</body></html>')
    return "".join(parts)


def _date_text(d: dict) -> str:
    date = d.get("d", "")
    time = d.get("tm")
    return f"{date} {time}" if time else date or "unknown"


def generate_index_html(
    file_index: list[dict],
    output_dir: Path,
    json_data: dict | None = None,
    dry_run: bool = False,
    thumbs: dict[int, str] | None = None,
) -> bool:
    if dry_run:
        return True

    thumbs = thumbs or {}

    by_year: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for i, f in enumerate(file_index):
        by_year[f.get("subfolder", f.get("year", "unknown"))].append((i, f))

    n_vid = sum(1 for f in file_index if f["type"] == "video")
    n_img = sum(1 for f in file_index if f["type"] == "image")
    n_aud = sum(1 for f in file_index if f["type"] == "audio")

    details = build_file_details(file_index, json_data)
    # A username containing "</script>" would otherwise close the script block.
    details_json = json.dumps(details, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    page = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Snapchat Memories</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a1a; color: #e0e0e0; padding: 20px; }
h1 { text-align: center; margin: 20px 0 30px; color: #FFFE00; font-size: 24px; }
h2 { margin: 20px 0 10px; color: #FFFE00; border-bottom: 1px solid #333; padding-bottom: 5px; }
.stats { text-align: center; color: #888; margin-bottom: 30px; }
.page-nav { text-align: center; margin-bottom: 18px; }
.page-nav a { color: #FFFE00; text-decoration: none; margin: 0 10px; }
.page-nav a:hover { text-decoration: underline; }
.year-nav { text-align: center; margin-bottom: 20px; }
.year-nav a { color: #FFFE00; text-decoration: none; margin: 0 10px; font-size: 18px; }
.year-nav a:hover { text-decoration: underline; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-bottom: 30px; }
.item { background: #2a2a2a; border-radius: 8px; overflow: hidden; position: relative; }
.item a { display: block; text-decoration: none; color: inherit; }
.item .thumb { width: 100%; height: 150px; object-fit: cover; display: block; }
.item .info { padding: 8px; font-size: 12px; color: #aaa; display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.item .date { color: #ddd; font-weight: 600; }
.item .type-badge { position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.7); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
.video-icon::before { content: "\\25B6 "; }
.audio-icon::before { content: "\\266A "; }
.audio-item { display: flex; align-items: center; justify-content: center; height: 150px; background: #333; }
.audio-item span { font-size: 48px; }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 10px; margin-bottom: 20px; }
.filters button { background: #333; color: #e0e0e0; border: 1px solid #555; padding: 8px 16px; margin: 0 3px; border-radius: 6px; cursor: pointer; font-size: 14px; font-family: inherit; }
.filters button:hover { background: #444; }
.filters button.active { background: #FFFE00; color: #1a1a1a; border-color: #FFFE00; font-weight: 600; }
.item.hidden { display: none; }

__DETAILS_CSS__
__DATE_CSS__
</style>
</head>
<body>
<h1>Snapchat Memories</h1>
<div class="page-nav"><a href="index.html">Overview</a><a href="chats.html">Chats</a><a href="stats.html">Statistics</a><a href="map.html">Snap Map</a></div>
'''

    page += f'<div class="stats">{len(file_index)} files | {n_vid} Videos | {n_img} Images | {n_aud} Voice Messages</div>\n'
    page += '''<div class="toolbar">
<span class="filters">
<button class="active" onclick="filterAll(this)">All</button>
<button onclick="filterType('image', this)">Images</button>
<button onclick="filterType('video', this)">Videos</button>
<button onclick="filterType('audio', this)">Voice Messages</button>
</span>
''' + date_format_picker_html() + '''
</div>
'''

    page += '<div class="year-nav">'
    for year in sorted(by_year.keys()):
        page += f'<a href="#{year}">{year} ({len(by_year[year])})</a>'
    page += '</div>\n'

    for year in sorted(by_year.keys(), reverse=True):
        items = by_year[year]
        page += f'<h2 id="{year}">{year} ({len(items)} files)</h2>\n<div class="grid">\n'

        for idx, f in sorted(items, key=lambda x: x[1]["date"], reverse=True):
            subfolder = f.get("subfolder", f.get("year", "unknown"))
            filepath = html.escape(f"{subfolder}/{f['new_name']}")
            ftype = f["type"]
            date_html = date_span(f["date"], extra_class="date")
            info_btn = f'<button class="info-btn" data-id="f{idx}" title="Details">&#8505;</button>'
            info_bar = f'<div class="info">{date_html}{info_btn}</div>'

            preview = html.escape(thumbs[idx]) if idx in thumbs else None
            if isinstance(f.get("integrity"), dict):
                info_bar = f'<div class="info damaged">{date_html}<span class="damaged-badge">damaged</span>{info_btn}</div>'

            if ftype == "image":
                page += (f'<div class="item" data-type="image">'
                         f'<a href="{filepath}"><img class="thumb" src="{preview or filepath}" loading="lazy" alt=""></a>'
                         f'{info_bar}</div>\n')
            elif ftype == "video":
                media = (f'<img class="thumb" src="{preview}" loading="lazy" alt="">' if preview
                         else f'<video class="thumb" src="{filepath}" preload="metadata"></video>')
                page += (f'<div class="item" data-type="video">'
                         f'<a href="{filepath}"><span class="type-badge video-icon">Video</span>'
                         f'{media}</a>'
                         f'{info_bar}</div>\n')
            elif ftype == "audio":
                page += (f'<div class="item" data-type="audio">'
                         f'<a href="{filepath}"><span class="type-badge audio-icon">Audio</span>'
                         f'<div class="audio-item"><span>&#9835;</span></div></a>'
                         f'{info_bar}</div>\n')

        page += '</div>\n'

    page += '''
__DETAILS_OVERLAY__
<script>
function filterType(type, btn) {
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.item').forEach(item => {
        item.classList.toggle('hidden', item.dataset.type !== type);
    });
}
function filterAll(btn) {
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.item').forEach(item => item.classList.remove('hidden'));
}
window.__SEO_DETAILS = __DETAILS_JSON__;
</script>
<script>__DATE_JS__</script>
<script>__DETAILS_JS__</script>
</body></html>'''

    page = page.replace("__DATE_CSS__", date_format_css())
    page = page.replace("__DETAILS_JSON__", details_json)
    page = page.replace("__DATE_JS__", date_format_js())
    page = page.replace("__DETAILS_JS__", DETAILS_JS)
    page = page.replace("__DETAILS_CSS__", DETAILS_CSS)
    page = page.replace("__DETAILS_OVERLAY__", details_overlay_html())

    (output_dir / "gallery.html").write_text(page, encoding="utf-8")
    console.print(f"  Generated gallery.html ({len(file_index)} entries)")
    return True
