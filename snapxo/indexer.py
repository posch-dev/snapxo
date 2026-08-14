import html
import json
import re
from collections import defaultdict
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


def _chat_info_by_media_id(json_data: dict) -> dict[str, dict]:
    # Map Media ID to {time, sender, chat}. Chat media is the only case with an exact
    # timestamp and sender, because the message carrying the file names it.
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
    # Map date to memories_history entries that carry coordinates.
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
    # Per-file metadata for the details panel, keyed by index position. Chat media has
    # an exact time and sender via its Media ID, memories can only be matched to GPS
    # by date, so those coordinates are flagged approximate when the day is ambiguous.
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
                # More than one memory that day means we cannot tell which is which
                item["approx"] = len(candidates) > 1
                if len(candidates) == 1 and candidates[0]["time"]:
                    item["tm"] = candidates[0]["time"]

        details[f"f{i}"] = item

    return details


def _details_script() -> str:
    # Details panel: metadata plus copy to clipboard for folder and file path.
    return r"""
(function () {
    "use strict";
    var DETAILS = window.__SEO_DETAILS || {};
    var overlay = document.getElementById("detail-overlay");
    var panel = document.getElementById("detail-panel");

    // Derive the absolute path from the page's own URL rather than baking it in
    // at generation time, so it stays correct after moving the output folder --
    // and so it looks right on both Windows and Linux.
    function localRoot() {
        var href = location.href.split("#")[0].split("?")[0];
        if (href.indexOf("file:///") !== 0) return null;
        var dir = decodeURIComponent(href.substring(8, href.lastIndexOf("/")));
        if (/^[A-Za-z]:/.test(dir)) return { sep: "\\", base: dir.replace(/\//g, "\\") };
        return { sep: "/", base: "/" + dir };
    }

    function absolutePath(relParts) {
        var root = localRoot();
        if (!root) return null;
        return root.base + root.sep + relParts.join(root.sep);
    }

    function formatSize(bytes) {
        if (bytes === null || bytes === undefined) return "unknown";
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
        if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB";
        return (bytes / 1073741824).toFixed(2) + " GB";
    }

    function copyToClipboard(text, btn) {
        var original = btn.textContent;
        function ok() {
            btn.textContent = "Copied";
            btn.classList.add("copied");
            setTimeout(function () {
                btn.textContent = original;
                btn.classList.remove("copied");
            }, 1400);
        }
        function legacy() {
            var ta = document.createElement("textarea");
            ta.value = text;
            ta.setAttribute("readonly", "");
            ta.style.position = "fixed";
            ta.style.top = "-1000px";
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand("copy"); ok(); } catch (e) { btn.textContent = "Copy failed"; }
            document.body.removeChild(ta);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(ok, legacy);
        } else {
            legacy();
        }
    }

    function row(label, valueHtml) {
        return '<div class="detail-row"><span class="detail-label">' + label +
               '</span><span class="detail-value">' + valueHtml + "</span></div>";
    }

    function esc(s) {
        return String(s === null || s === undefined ? "" : s)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function open(id) {
        var d = DETAILS[id];
        if (!d) return;

        var typeLabel = { image: "Image", video: "Video", audio: "Voice message" }[d.t] || d.t || "File";
        var sourceLabel = { memory: "Memory", chat: "Chat media" }[d.src] || d.src || "unknown";

        var body = "";
        body += row("Name", esc(d.n));
        body += row("Type", esc(typeLabel));
        body += row("Source", esc(sourceLabel));
        body += row("Size", formatSize(d.s));

        var dateHtml = '<span data-date="' + esc(d.d) + '"' +
                       (d.tm ? ' data-time="' + esc(d.tm) + '"' : "") + ">" + esc(d.d) + "</span>";
        body += row(d.tm ? "Date &amp; time" : "Date", dateHtml);

        if (d.from) body += row("Sender", esc(d.from));
        if (d.chat) body += row("Chat", esc(d.chat));

        if (d.lat !== undefined) {
            var coords = d.lat + ", " + d.lon;
            var note = d.approx ? ' <span class="detail-note">approx. &mdash; matched by date only</span>' : "";
            var mapLink = '<a href="https://www.openstreetmap.org/?mlat=' + d.lat + '&amp;mlon=' + d.lon +
                          '#map=16/' + d.lat + '/' + d.lon + '" target="_blank" rel="noopener">' + coords + "</a>";
            body += row("Location", mapLink + note);
        }

        if (d.o && d.o !== d.n) body += row("Original name", '<span class="detail-mono">' + esc(d.o) + "</span>");

        var relFile = d.f + "/" + d.n;
        var absFolder = absolutePath([d.f]);
        var absFile = absolutePath([d.f, d.n]);

        body += '<div class="detail-paths">';
        body += '<div class="detail-path-row"><span class="detail-mono">' + esc(absFolder || d.f) +
                '</span><button class="copy-btn" data-copy="' + esc(absFolder || d.f) + '">Copy folder</button></div>';
        body += '<div class="detail-path-row"><span class="detail-mono">' + esc(absFile || relFile) +
                '</span><button class="copy-btn" data-copy="' + esc(absFile || relFile) + '">Copy file</button></div>';
        if (!absFile) {
            body += '<div class="detail-note">Paths are relative &mdash; open index.html directly from disk to get full paths.</div>';
        }
        body += "</div>";

        panel.innerHTML =
            '<div class="detail-head"><h3>' + esc(d.n) + '</h3>' +
            '<button class="detail-close" aria-label="Close">&times;</button></div>' +
            '<div class="detail-body">' + body + "</div>";

        overlay.classList.add("visible");
        if (window.SEODate) window.SEODate.apply(panel);
    }

    function close() { overlay.classList.remove("visible"); }

    document.addEventListener("click", function (e) {
        var info = e.target.closest ? e.target.closest(".info-btn") : null;
        if (info) {
            e.preventDefault();
            e.stopPropagation();
            open(info.getAttribute("data-id"));
            return;
        }
        var copy = e.target.closest ? e.target.closest(".copy-btn") : null;
        if (copy) {
            e.preventDefault();
            copyToClipboard(copy.getAttribute("data-copy"), copy);
            return;
        }
        if (e.target.closest && e.target.closest(".detail-close")) { close(); return; }
        if (e.target === overlay) close();
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") close();
    });
})();
"""


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


def _format_size(size) -> str:
    if not isinstance(size, int):
        return "unknown"
    if size < 1024:
        return f"{size} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"
    if size < 1024 ** 3:
        return f"{size / 1024 ** 2:.1f} MB"
    return f"{size / 1024 ** 3:.2f} GB"


def build_print_index(
    file_index: list[dict],
    details: dict[str, dict],
    thumbs: dict[int, str] | None = None,
) -> str:
    # Print variant: no scripts, and never lazy, or the PDF comes out without images.
    thumbs = thumbs or {}

    by_year: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for i, f in enumerate(file_index):
        by_year[f.get("subfolder", f.get("year", "unknown"))].append((i, f))

    n_vid = sum(1 for f in file_index if f.get("type") == "video")
    n_img = sum(1 for f in file_index if f.get("type") == "image")
    n_aud = sum(1 for f in file_index if f.get("type") == "audio")

    parts = ['<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
             '<title>Snapchat Memories</title>\n<style>' + PRINT_CSS + '</style>\n</head>\n<body>\n']
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
                    ("Size", _format_size(d.get("s")))]
            if d.get("from"):
                rows.append(("Sender", d["from"]))
            if d.get("chat"):
                rows.append(("Chat", d["chat"]))
            if d.get("lat") is not None:
                coords = f'{d["lat"]}, {d["lon"]}'
                if d.get("approx"):
                    coords += ' <span class="note">(approx.)</span>'
                rows.append(("Location", coords))
            if d.get("o") and d.get("o") != d.get("n"):
                rows.append(("Original", d["o"]))

            dl = "".join(f"<dt>{k}</dt><dd>{v if k == 'Location' else html.escape(str(v))}</dd>" for k, v in rows)
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


def generate_index_pdf(
    file_index: list[dict],
    output_dir: Path,
    json_data: dict | None = None,
    thumbs: dict[int, str] | None = None,
    dry_run: bool = False,
) -> bool:
    if dry_run:
        return True

    from .pdf import render_single

    details = build_file_details(file_index, json_data)
    page = build_print_index(file_index, details, thumbs)

    # Must sit in the output root, the media paths are relative to it.
    source = output_dir / "index_print.tmp.html"
    source.write_text(page, encoding="utf-8")
    try:
        ok = render_single(source, output_dir / "index.pdf")
    finally:
        source.unlink(missing_ok=True)
    return ok


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
    # A username containing "</script>" would otherwise close the script block
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
.info-btn { background: none; border: 1px solid #555; color: #aaa; border-radius: 50%; width: 22px; height: 22px; font-size: 12px; line-height: 1; cursor: pointer; flex: 0 0 auto; font-family: inherit; }
.info-btn:hover { border-color: #FFFE00; color: #FFFE00; }
.video-icon::before { content: "\\25B6 "; }
.audio-icon::before { content: "\\266A "; }
.audio-item { display: flex; align-items: center; justify-content: center; height: 150px; background: #333; }
.audio-item span { font-size: 48px; }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 10px; margin-bottom: 20px; }
.filters button { background: #333; color: #e0e0e0; border: 1px solid #555; padding: 8px 16px; margin: 0 3px; border-radius: 6px; cursor: pointer; font-size: 14px; font-family: inherit; }
.filters button:hover { background: #444; }
.filters button.active { background: #FFFE00; color: #1a1a1a; border-color: #FFFE00; font-weight: 600; }
.item.hidden { display: none; }

/* Details panel */
#detail-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 2000; align-items: center; justify-content: center; padding: 20px; }
#detail-overlay.visible { display: flex; }
#detail-panel { background: #242424; border: 1px solid #3a3a3a; border-radius: 12px; max-width: 560px; width: 100%; max-height: 85vh; overflow-y: auto; box-shadow: 0 12px 40px rgba(0,0,0,0.6); }
.detail-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px; border-bottom: 1px solid #333; position: sticky; top: 0; background: #242424; }
.detail-head h3 { color: #FFFE00; font-size: 15px; font-weight: 600; word-break: break-all; }
.detail-close { background: none; border: none; color: #888; font-size: 26px; line-height: 1; cursor: pointer; padding: 0 4px; }
.detail-close:hover { color: #fff; }
.detail-body { padding: 12px 20px 20px; }
.detail-row { display: flex; gap: 12px; padding: 7px 0; border-bottom: 1px solid #2e2e2e; font-size: 13px; }
.detail-label { color: #888; flex: 0 0 120px; }
.detail-value { color: #e0e0e0; word-break: break-word; }
.detail-value a { color: #FFFE00; }
.detail-note { color: #c9a227; font-size: 11px; }
.detail-mono { font-family: ui-monospace, 'Cascadia Code', Consolas, monospace; font-size: 11.5px; word-break: break-all; color: #bbb; }
.detail-paths { margin-top: 16px; padding-top: 12px; border-top: 1px solid #333; display: flex; flex-direction: column; gap: 8px; }
.detail-path-row { display: flex; align-items: center; gap: 10px; justify-content: space-between; }
.copy-btn { background: #333; color: #ddd; border: 1px solid #555; border-radius: 6px; padding: 5px 10px; font-size: 11px; cursor: pointer; white-space: nowrap; flex: 0 0 auto; font-family: inherit; }
.copy-btn:hover { background: #444; border-color: #888; }
.copy-btn.copied { background: #FFFE00; color: #1a1a1a; border-color: #FFFE00; }
__DATE_CSS__
</style>
</head>
<body>
<h1>Snapchat Memories</h1>
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
<div id="detail-overlay"><div id="detail-panel"></div></div>
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
    page = page.replace("__DETAILS_JS__", _details_script())

    (output_dir / "index.html").write_text(page, encoding="utf-8")
    console.print(f"  Generated index.html ({len(file_index)} entries)")
    return True
