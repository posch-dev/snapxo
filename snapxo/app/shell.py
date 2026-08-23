# index.html, with Overview, Stats, Media and Chats as tabs. Assembles parts
# other modules produce and computes nothing itself.

import html
from datetime import datetime
from pathlib import Path

from rich.console import Console

from .. import __version__
from ..facts.datasets import numbers_dataset, stats_datasets
from ..facts.provenance import (
    COVER_CSS,
    PROVENANCE_CSS,
    archive_facts,
    cover_page,
    fact_rows,
    provenance_panel,
)
from ..facts.series import build_series
from ..pages.gallery import build_file_details
from ..pages.stats import (
    ACTIVITY_TOGGLE_JS,
    STATS_CSS,
    build_chart_sections,
    build_detail_tables,
    build_stats_table,
    render_cards,
    stat_card_values,
)
from ..parts.charts import CHART_CSS
from ..parts.details import DETAILS_CSS, DETAILS_JS, details_overlay_html
from ..parts.icons import ICON_CSS, icon
from ..parts.shared import (
    date_format_css,
    date_format_js,
    date_format_picker_html,
    date_span,
    split_timestamp,
)
from .chats import CHATS_CSS, CHATS_JS, chats_panel
from .data import write_chats_data, write_media_data, write_stats_data
from .downloads import EXPORT_CSS, dialogs, export_all_button, export_script
from .media import MEDIA_CSS, media_panel, media_script

console = Console()

OVERVIEW_CARDS = ["Messages", "Snaps", "Chats", "Friends", "Memories", "Chat Media"]
# Nine fit the middle column on a desktop, CSS hides all but five on a phone.
OVERVIEW_CHATS = 9
OVERVIEW_MEDIA = 6

TABS = [("overview", "Overview"), ("stats", "Stats"), ("media", "Media"), ("chats", "Chats")]

AUTHOR_URL = "https://github.com/posch-dev"
AUTHOR_NAME = "posch-dev"

# Inline so the page keeps working without a single external request.
GITHUB_MARK = ('<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="currentColor">'
               '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38'
               ' 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53'
               '.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95'
               ' 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.4 7.4 0 0 1 2-.27c.68 0 1.36.09'
               ' 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65'
               ' 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/>'
               "</svg>")


def initials(name: str) -> str:
    parts = [part for part in name.replace("_", " ").replace("-", " ").replace(".", " ").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def avatar_hue(name: str) -> int:
    return sum(ord(character) for character in name) % 360


APP_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a1a; color: #e0e0e0; }
h2 { font-size: 13px; color: #aaa; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }
a { color: #FFFE00; }
.empty { color: #888; text-align: center; padding: 40px 20px; }
/* env() keeps the bar clear of a notch or a punch hole, and falls back to the
   plain padding on everything else. */
.app-nav { position: sticky; top: 0; z-index: 20; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; background: #141414; border-bottom: 1px solid #2c2c2c;
  padding: calc(10px + env(safe-area-inset-top, 0px)) calc(20px + env(safe-area-inset-right, 0px)) 10px calc(20px + env(safe-area-inset-left, 0px)); }
.brand { color: #FFFE00; font-weight: 700; letter-spacing: 0.04em; }
.tab-buttons { display: flex; align-items: center; gap: 4px; flex: 1 1 auto; }
.tab-button { background: none; border: none; color: #999; font-family: inherit; font-size: 14px; padding: 8px 14px; border-radius: 8px; cursor: pointer; }
.tab-button:hover { color: #e0e0e0; background: #222; }
.tab-button.active { color: #1a1a1a; background: #FFFE00; font-weight: 600; }
/* the padding matches the flex gap, so the rule sits midway between the two */
.nav-author { display: inline-flex; align-items: center; gap: 6px; color: #777; font-size: 12px; text-decoration: none; padding-right: 16px; border-right: 1px solid #333; }
.nav-author:hover { color: #e0e0e0; }
.nav-extras { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.nav-freshness { color: #777; font-size: 11.5px; white-space: nowrap; }
/* Outlined rather than filled, so it reads as yellow without looking like the active tab. */
.nav-map { display: inline-flex; align-items: center; gap: 6px; margin-left: 10px; font-size: 12.5px; font-weight: 600; text-decoration: none; color: #FFFE00; border: 1px solid #756f16; background: #2a2910; border-radius: 8px; padding: 6px 11px; }
.nav-map:hover { background: #3a3814; border-color: #FFFE00; }
.app-main { max-width: 1280px; margin: 0 auto;
  padding: 20px calc(20px + env(safe-area-inset-right, 0px)) calc(20px + env(safe-area-inset-bottom, 0px)) calc(20px + env(safe-area-inset-left, 0px)); }
.tab-panel { display: none; }
.tab-panel.active { display: block; }
.dash-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr) minmax(0, 1fr); gap: 20px; }
.dash-column { background: #202020; border-radius: 12px; padding: 16px; }
.dash-column h2 { margin-bottom: 12px; }
.dash-cards { display: flex; flex-direction: column; gap: 10px; }
.dash-cards .card { min-width: 0; padding: 12px 16px; }
.dash-chats { display: flex; flex-direction: column; gap: 2px; }
.dash-chat { display: flex; align-items: center; gap: 12px; width: 100%; padding: 8px 10px; border: none; border-radius: 10px; background: none; color: inherit; font-family: inherit; text-align: left; cursor: pointer; }
.dash-chat:hover { background: #2a2a2a; }
.avatar { flex: 0 0 auto; width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; color: #fff; }
.dash-chat-main { min-width: 0; }
.dash-chat-name { display: block; font-weight: 700; color: #fff; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dash-chat-user { color: #8d8d8d; font-weight: 400; font-size: 12px; }
.avatar-group { background: #262626 !important; padding: 0; }
.avatar-group svg { width: 100%; height: 100%; display: block; }
.dash-chat-meta { display: block; color: #888; font-size: 12px; }
.dash-media { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.dash-tile { position: relative; display: block; aspect-ratio: 1; border-radius: 8px; overflow: hidden; background: #2a2a2a; text-decoration: none; }
.dash-tile img { width: 100%; height: 100%; object-fit: cover; display: block; }
.dash-noprev { display: flex; align-items: center; justify-content: center; height: 100%; font-size: 26px; color: #555; }
.dash-play { position: absolute; left: 8px; top: 6px; color: #fff; font-size: 12px; text-shadow: 0 1px 3px rgba(0,0,0,0.8); }
.dash-more { margin-top: 12px; background: none; border: 1px solid #444; border-radius: 8px; color: #bbb; font-family: inherit; font-size: 12px; padding: 7px 12px; cursor: pointer; width: 100%; }
.dash-more:hover { border-color: #FFFE00; color: #FFFE00; }
/* Long tabs on a phone are a lot of scrolling, so there is a way back up. */
.to-top { position: fixed; right: calc(18px + env(safe-area-inset-right, 0px)); bottom: calc(18px + env(safe-area-inset-bottom, 0px)); z-index: 1500; display: flex; align-items: center; justify-content: center; width: 48px; height: 48px; border-radius: 50%; border: 1px solid #444; background: #262626; color: #e0e0e0; cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,0.45); opacity: 0; visibility: hidden; transform: translateY(8px); transition: opacity 0.15s ease, transform 0.15s ease, visibility 0.15s; }
.to-top.shown { opacity: 1; visibility: visible; transform: none; }
.to-top:hover { border-color: #FFFE00; color: #FFFE00; }
@media (max-width: 980px) {
  /* On a phone the chats come first, then the media, and the numbers last. */
  .dash-grid { grid-template-columns: minmax(0, 1fr); }
  .dash-top-chats { order: 1; }
  .dash-recent { order: 2; }
  .dash-stats { order: 3; }
  .dash-chat:nth-child(n + 6) { display: none; }
  /* Name in one corner, author in the other, everything else centred below.
     A little more room on top, where a notch usually sits. */
  .app-nav { gap: 14px 12px; padding-top: calc(18px + env(safe-area-inset-top, 0px)); padding-bottom: 12px; }
  .brand { order: 1; }
  .nav-author { order: 2; margin-left: auto; padding-right: 0; border-right: none; }
  .tab-buttons { order: 3; width: 100%; flex: 1 1 100%; justify-content: center; flex-wrap: wrap; }
  .nav-extras { order: 4; width: 100%; justify-content: center; gap: 10px; }
  .nav-map { margin-left: 0; }
  .date-format-picker label { display: none; }
}
@media print {
  body { background: #fff; color: #000; }
  h1, h2, h3 { color: #000 !important; }
  a { color: #333; }
  .app-nav { display: none; }
  .tab-panel { display: block !important; }
  .dash-column { background: none; border: 1px solid #ddd; }
}
"""

TO_TOP_JS = """
(function () {
    "use strict";
    var button = document.getElementById("to-top");
    if (!button) return;
    var APPEARS_AFTER = 300;

    function update() {
        button.classList.toggle("shown", window.scrollY > APPEARS_AFTER);
    }

    button.addEventListener("click", function () {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
    window.addEventListener("scroll", update, { passive: true });
    update();
})();
"""


TAB_JS = """
(function () {
    "use strict";
    var panels = document.querySelectorAll(".tab-panel");
    var buttons = document.querySelectorAll(".tab-button");

    function show(name) {
        var found = false;
        Array.prototype.forEach.call(panels, function (panel) {
            var match = panel.id === "tab-" + name;
            panel.classList.toggle("active", match);
            found = found || match;
        });
        if (!found) return false;
        Array.prototype.forEach.call(buttons, function (button) {
            button.classList.toggle("active", button.getAttribute("data-tab") === name);
        });
        document.dispatchEvent(new CustomEvent("snapxo:tab", { detail: name }));
        return true;
    }

    Array.prototype.forEach.call(document.querySelectorAll("[data-tab]"), function (element) {
        element.addEventListener("click", function () {
            var name = element.getAttribute("data-tab");
            if (show(name)) window.location.hash = name;
        });
    });

    window.addEventListener("hashchange", function () {
        show(window.location.hash.replace("#", ""));
    });

    if (window.location.hash) show(window.location.hash.replace("#", ""));
    window.SEOTabs = { show: show };
})();
"""


def _freshness() -> str:
    # Tagged, not plain, or the date format picker would not reach it.
    now = datetime.now()
    written = date_span(now.strftime("%Y-%m-%d"), now.strftime("%H:%M"))
    return f'<span class="nav-freshness">Last updated at {written}</span>'


def _nav() -> str:
    buttons = "".join(
        f'<button class="tab-button{" active" if index == 0 else ""}" data-tab="{key}">'
        f"{html.escape(label)}</button>"
        for index, (key, label) in enumerate(TABS)
    )
    return f'''<header class="app-nav no-print">
<span class="brand">SnapXO</span>
<a class="nav-author" href="{AUTHOR_URL}" target="_blank" rel="noopener">{GITHUB_MARK}{AUTHOR_NAME}</a>
<nav class="tab-buttons">{buttons}
<a class="nav-map" href="map.html" target="_blank" rel="noopener">Map {icon("external", 12)}</a>
</nav>
<span class="nav-extras">
{_freshness()}
{date_format_picker_html("Date formatting")}
</span>
</header>'''


def _overview_cards(card_values: list[tuple[str, object]]) -> str:
    return render_cards([(label, value) for label, value in card_values
                         if label in OVERVIEW_CARDS])


def _avatar(title: str, is_group: bool) -> str:
    # As in the chat list: a person gets initials, a group gets circles.
    if not is_group:
        return (f'<span class="avatar" style="background:hsl({avatar_hue(title)},45%,42%)">'
                f"{html.escape(initials(title))}</span>")
    base = avatar_hue(title)
    spots = [(8.5, 8), (15.5, 8), (12, 15.5)]
    circles = "".join(
        f'<circle cx="{x}" cy="{y}" r="5.4" fill="hsl({(base + index * 110) % 360},55%,52%)" '
        f'stroke="#202020" stroke-width="1.4"/>'
        for index, (x, y) in enumerate(spots)
    )
    return f'<span class="avatar avatar-group"><svg viewBox="0 0 24 24">{circles}</svg></span>'


def _overview_chats(chats: list[dict]) -> str:
    # The same records the Chats tab uses, so names and grouping match.
    if not chats:
        return '<p class="empty">No conversations in this export.</p>'
    rows = []
    for chat in chats:
        title = html.escape(chat["t"])
        username = f' <span class="dash-chat-user">({html.escape(chat["u"])})</span>' if chat.get("u") else ""
        date_part, _ = split_timestamp(chat.get("d", ""))
        stamp = date_span(date_part) if date_part else ""
        rows.append(
            f'<button class="dash-chat" data-open-chat="{title}">'
            f'{_avatar(chat["t"], chat.get("g", False))}'
            f'<span class="dash-chat-main"><span class="dash-chat-name">{title}{username}</span>'
            f'<span class="dash-chat-meta">{chat["n"]} messages &middot; {stamp}</span></span>'
            f"</button>"
        )
    return "".join(rows)


def _overview_media(file_index: list[dict], thumbs: dict[int, str]) -> str:
    # Genuinely the newest files, not the newest that happen to have a preview.
    newest = sorted(range(len(file_index)),
                    key=lambda index: file_index[index].get("date", ""),
                    reverse=True)[:OVERVIEW_MEDIA]

    if not newest:
        return '<p class="empty">No media in this export.</p>'

    tiles = []
    for index in newest:
        entry = file_index[index]
        subfolder = entry.get("subfolder") or entry.get("year") or "unknown"
        target = html.escape(f"{subfolder}/{entry.get('new_name', '')}")
        badge = ""
        if entry.get("type") == "video":
            badge = '<span class="dash-play">&#9654;</span>'
        elif entry.get("type") == "audio":
            badge = '<span class="dash-play">&#9835;</span>'

        preview = thumbs.get(index)
        inner = (f'<img src="{html.escape(preview)}" loading="lazy" alt="">' if preview
                 else '<span class="dash-noprev">&#128247;</span>')
        tiles.append(f'<a class="dash-tile" href="{target}" target="_blank" rel="noopener">{inner}{badge}</a>')
    return "".join(tiles)


def _overview(chats: list[dict], file_index: list[dict], thumbs: dict[int, str],
              card_values: list[tuple[str, object]]) -> str:
    # Stats, chats, media on a desktop. CSS reorders them to chats, media, stats
    # on a phone, which is the order they get used in there.
    return f'''<section class="tab-panel active" id="tab-overview">
<div class="dash-grid">
<div class="dash-column dash-stats">
<h2>Quick stats</h2>
<div class="dash-cards">{_overview_cards(card_values)}</div>
</div>
<div class="dash-column dash-top-chats">
<h2>Top chats</h2>
<div class="dash-chats">{_overview_chats(chats)}</div>
<button class="dash-more" data-tab="chats">All chats &rarr;</button>
</div>
<div class="dash-column dash-recent">
<h2>Recent media</h2>
<div class="dash-media">{_overview_media(file_index, thumbs)}</div>
<button class="dash-more" data-tab="media">Open gallery &rarr;</button>
</div>
</div>
</section>'''


def _stats_panel(table_html: str, charts_html: str, tables_html: str, provenance_html: str) -> str:
    return f'''<section class="tab-panel" id="tab-stats">
{table_html}
{provenance_html}
{charts_html}
{tables_html}
{export_all_button()}
</section>'''


def generate_app(
    output_dir: Path,
    json_data: dict,
    file_index: list[dict],
    file_stats: dict,
    thumbs: dict[int, str] | None = None,
    media_map: dict[str, dict] | None = None,
    dry_run: bool = False,
) -> bool:
    if dry_run:
        return True

    thumbs = thumbs or {}
    chats_payload = write_chats_data(output_dir, json_data, media_map)
    busiest = sorted(chats_payload["chats"], key=lambda chat: chat["n"],
                     reverse=True)[:OVERVIEW_CHATS]
    write_media_data(output_dir, file_index, thumbs, build_file_details(file_index, json_data))
    series = build_series(json_data, file_index)
    card_values = stat_card_values(json_data, file_stats, series)
    write_stats_data(output_dir, [numbers_dataset(card_values)] + stats_datasets(series))

    facts = archive_facts(output_dir, file_index, series)
    panels = [
        _overview(busiest, file_index, thumbs, card_values),
        _stats_panel(build_stats_table(card_values), build_chart_sections(series),
                     build_detail_tables(json_data), provenance_panel(facts)),
        media_panel(),
        chats_panel(cover_page("", "", fact_rows(facts), __version__)),
    ]

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Snapchat Archive</title>
<style>
{APP_CSS}
{STATS_CSS}
{CHART_CSS}
{CHATS_CSS}
{MEDIA_CSS}
{ICON_CSS}
{PROVENANCE_CSS}
{COVER_CSS}
{EXPORT_CSS}
{DETAILS_CSS}
{date_format_css()}
</style>
</head>
<body>
{_nav()}
<main class="app-main">
{"".join(panels)}
</main>
{details_overlay_html()}
{dialogs()}
<button class="to-top no-print" id="to-top" type="button" title="Back to the top">{icon('arrow-up', 20)}</button>
<script>{date_format_js()}</script>
<script src="_meta/app-chats.js"></script>
<script src="_meta/app-media.js"></script>
<script src="_meta/app-stats.js"></script>
<script>window.__SEO_DETAILS = (window.SNAPXO_MEDIA || {{}}).details || {{}};</script>
<script>{TAB_JS}</script>
<script>{ACTIVITY_TOGGLE_JS}</script>
<script>{CHATS_JS}</script>
<script>{media_script()}</script>
<script>{DETAILS_JS}</script>
<script>{export_script(CHART_CSS)}</script>
<script>{TO_TOP_JS}</script>
</body>
</html>'''

    (output_dir / "index.html").write_text(page, encoding="utf-8")
    console.print(f"  Generated index.html ({series['total_chats']} chats, {len(file_index)} files)")
    return True
