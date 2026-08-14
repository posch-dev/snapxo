# chats.html: the chat list next to index.html, with a search across every message.

import html
import json
from pathlib import Path

from rich.console import Console

from .webassets import date_format_css, date_format_js, date_format_picker_html, split_timestamp

console = Console()

PREVIEW_CHARS = 90
SEARCH_CHARS = 300


def message_anchor(index: int) -> str:
    return f"m{index}"


def _initials(name: str) -> str:
    parts = [p for p in name.replace("_", " ").replace("-", " ").replace(".", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def _hue(name: str) -> int:
    return sum(ord(c) for c in name) % 360


def build_chats_html(records: list[dict]) -> str:
    # `records` come from the conversation step, one per written chat file.
    for r in records:
        r.setdefault("messages", 0)
    ordered = sorted(records, key=lambda r: r.get("last", ""), reverse=True)

    search_data = []
    for i, r in enumerate(ordered):
        for hit in r.get("index", []):
            search_data.append({"c": i, **hit})

    chats_meta = [{"t": r["title"], "f": r["file"], "n": r["messages"]} for r in ordered]
    payload = json.dumps({"chats": chats_meta, "msgs": search_data},
                         ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    rows = []
    for i, r in enumerate(ordered):
        title = html.escape(r["title"])
        date_part, time_part = split_timestamp(r.get("last", ""))
        stamp = (f'<span data-date="{html.escape(date_part)}" data-time="{html.escape(time_part)}">'
                 f'{html.escape(date_part)}</span>') if date_part else ""
        preview = html.escape(r.get("preview", ""))
        badge = ' <span class="group-badge">Group</span>' if r.get("is_group") else ""
        rows.append(
            f'<a class="chat" href="{html.escape(r["file"])}" data-chat="{i}" data-name="{title.lower()}">'
            f'<span class="avatar" style="background:hsl({_hue(r["title"])},45%,42%)">{html.escape(_initials(r["title"]))}</span>'
            f'<span class="chat-main"><span class="chat-top"><span class="chat-name">{title}{badge}</span>'
            f'<span class="chat-date">{stamp}</span></span>'
            f'<span class="chat-preview">{preview}</span></span>'
            f'<span class="chat-count">{r["messages"]}</span></a>'
        )

    # A PDF viewer cannot be sent to an anchor, so a hit only opens the file there.
    is_pdf = bool(ordered) and ordered[0]["file"].endswith(".pdf")
    note = ('<div class="note">The chats are PDFs, so a search hit opens the file '
            'without jumping to the message.</div>') if is_pdf else ""

    page = PAGE_TEMPLATE
    page = page.replace("__NOTE__", note)
    page = page.replace("__DATE_CSS__", date_format_css())
    page = page.replace("__PICKER__", date_format_picker_html())
    page = page.replace("__ROWS__", "\n".join(rows))
    page = page.replace("__TOTAL__", str(len(ordered)))
    page = page.replace("__MESSAGES__", str(sum(r["messages"] for r in ordered)))
    page = page.replace("__DATA__", payload)
    page = page.replace("__DATE_JS__", date_format_js())
    page = page.replace("__SEARCH_JS__", SEARCH_JS)
    return page


def generate_chats_html(records: list[dict], output_dir: Path, dry_run: bool = False) -> bool:
    if dry_run or not records:
        return False
    (output_dir / "chats.html").write_text(build_chats_html(records), encoding="utf-8")
    console.print(f"  Generated chats.html ({len(records)} chats)")
    return True


PAGE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Snapchat Chats</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a1a; color: #e0e0e0; padding: 20px; }
h1 { text-align: center; margin: 20px 0 10px; color: #FFFE00; font-size: 24px; }
.stats { text-align: center; color: #888; margin-bottom: 20px; }
.nav { text-align: center; margin-bottom: 18px; }
.nav a { color: #FFFE00; text-decoration: none; margin: 0 10px; }
.nav a:hover { text-decoration: underline; }
.wrap { max-width: 760px; margin: 0 auto; }
.toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 14px; }
#q { flex: 1 1 260px; background: #262626; border: 1px solid #444; border-radius: 8px; color: #e0e0e0; padding: 10px 12px; font-size: 15px; font-family: inherit; }
#q:focus { outline: none; border-color: #FFFE00; }
.sort { background: #333; color: #e0e0e0; border: 1px solid #555; border-radius: 8px; padding: 9px 14px; cursor: pointer; font-family: inherit; font-size: 13px; }
.sort:hover { background: #3d3d3d; }
.chat { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 10px; text-decoration: none; color: inherit; }
.chat:hover { background: #262626; }
.avatar { flex: 0 0 auto; width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px; color: #fff; }
.chat-main { flex: 1 1 auto; min-width: 0; }
.chat-top { display: flex; justify-content: space-between; gap: 10px; }
.chat-name { font-weight: 600; color: #eee; }
.group-badge { font-size: 10px; color: #1a1a1a; background: #FFFE00; border-radius: 4px; padding: 1px 5px; margin-left: 6px; vertical-align: middle; }
.chat-date, .chat-count { color: #888; font-size: 12px; white-space: nowrap; }
.chat-preview { display: block; color: #999; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat.hidden, .hit.hidden { display: none; }
#results { margin-top: 6px; }
.hit { display: block; padding: 9px 12px; border-radius: 8px; text-decoration: none; color: inherit; border-bottom: 1px solid #262626; }
.hit:hover { background: #262626; }
.hit-head { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; color: #888; }
.hit-chat { color: #FFFE00; }
.hit-text { display: block; font-size: 13.5px; color: #ddd; margin-top: 3px; }
.hit-text mark { background: #FFFE00; color: #1a1a1a; border-radius: 2px; }
.empty { color: #888; text-align: center; padding: 24px; }
.section-label { color: #777; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; margin: 16px 0 6px; }
.note { color: #c9a227; font-size: 12px; margin-bottom: 12px; }
__DATE_CSS__
</style>
</head>
<body>
<h1>Snapchat Chats</h1>
<div class="stats">__TOTAL__ chats | __MESSAGES__ messages</div>
<div class="nav"><a href="index.html">Media gallery</a><a href="stats.html">Statistics</a><a href="map.html">Snap Map</a></div>
<div class="wrap">
__NOTE__
<div class="toolbar">
<input id="q" type="search" placeholder="Search all messages" autocomplete="off">
<button class="sort" id="sort">Sort: recent</button>
__PICKER__
</div>
<div class="section-label" id="chat-label" hidden>Chats</div>
<div id="chatlist">
__ROWS__
</div>
<div id="results"></div>
</div>
<script>window.__SEO_CHATS = __DATA__;</script>
<script>__DATE_JS__</script>
<script>__SEARCH_JS__</script>
</body></html>'''


SEARCH_JS = r"""
(function () {
    "use strict";
    var DATA = window.__SEO_CHATS || { chats: [], msgs: [] };
    var input = document.getElementById("q");
    var list = document.getElementById("chatlist");
    var results = document.getElementById("results");
    var sortBtn = document.getElementById("sort");
    var chatLabel = document.getElementById("chat-label");
    var rows = Array.prototype.slice.call(list.querySelectorAll(".chat"));
    var byRecent = true;

    function esc(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function highlight(text, query) {
        var at = text.toLowerCase().indexOf(query);
        if (at < 0) return esc(text);
        var start = Math.max(0, at - 40);
        var lead = start > 0 ? "..." : "";
        return lead + esc(text.slice(start, at)) + "<mark>" + esc(text.slice(at, at + query.length)) +
               "</mark>" + esc(text.slice(at + query.length, at + query.length + 90));
    }

    function search(query) {
        var hits = [];
        for (var i = 0; i < DATA.msgs.length && hits.length < 300; i++) {
            var m = DATA.msgs[i];
            if (m.x && m.x.toLowerCase().indexOf(query) >= 0) hits.push(m);
        }
        if (!hits.length) {
            results.innerHTML = '<div class="empty">No message matches "' + esc(query) + '"</div>';
            return;
        }
        var html = '<div class="section-label">' + hits.length + ' message' + (hits.length === 1 ? "" : "s") + '</div>';
        hits.forEach(function (m) {
            var chat = DATA.chats[m.c] || { t: "", f: "#" };
            html += '<a class="hit" href="' + esc(chat.f) + '#' + esc(m.a) + '">' +
                    '<span class="hit-head"><span class="hit-chat">' + esc(chat.t) + '</span>' +
                    '<span>' + esc(m.s) + ' &middot; <span data-date="' + esc((m.t || "").slice(0, 10)) +
                    '" data-time="' + esc((m.t || "").slice(11, 16)) + '">' + esc((m.t || "").slice(0, 10)) +
                    '</span></span></span>' +
                    '<span class="hit-text">' + highlight(m.x, query) + "</span></a>";
        });
        results.innerHTML = html;
        if (window.SEODate) window.SEODate.apply(results);
    }

    function apply() {
        var query = input.value.trim().toLowerCase();
        if (!query) {
            rows.forEach(function (r) { r.classList.remove("hidden"); });
            list.classList.remove("hidden");
            chatLabel.hidden = true;
            results.innerHTML = "";
            return;
        }
        var matching = 0;
        rows.forEach(function (r) {
            var hit = r.getAttribute("data-name").indexOf(query) >= 0;
            r.classList.toggle("hidden", !hit);
            if (hit) matching++;
        });
        list.classList.toggle("hidden", !matching);
        chatLabel.hidden = !matching;
        search(query);
    }

    input.addEventListener("input", apply);
    sortBtn.addEventListener("click", function () {
        byRecent = !byRecent;
        sortBtn.textContent = byRecent ? "Sort: recent" : "Sort: name";
        var sorted = rows.slice();
        if (!byRecent) {
            sorted.sort(function (a, b) {
                return a.getAttribute("data-name").localeCompare(b.getAttribute("data-name"));
            });
        }
        sorted.forEach(function (r) { list.appendChild(r); });
    });
})();
"""
