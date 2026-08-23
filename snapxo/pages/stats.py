# The number cards, the charts and the detail tables, assembled into stats.html
# and reused piece by piece by the app.

import html
from pathlib import Path

from rich.console import Console

from ..app.downloads import buttons
from ..facts.provenance import COVER_CSS
from ..facts.series import HOUR_LABELS, WEEKDAY_LABELS, build_series
from ..parts.charts import CHART_CSS, bar_chart, donut_chart, line_chart
from ..parts.icons import ICON_CSS, icon
from ..parts.shared import (
    date_format_css,
    date_format_js,
    date_format_picker_html,
    date_span,
    split_timestamp,
)

console = Console()

_CARD_ICONS: dict[str, str] = {
    "Messages": "message",
    "Chats": "chats",
    "Snaps": "ghost",
    "Memories": "image",
    "Chat Media": "paperclip",
    "Overlays": "layers",
    "Friends": "users",
    "Blocked": "ban",
    "Deleted": "trash",
    "Calls": "phone",
    "Locations": "pin",
    "Snap Map Places": "map",
    "Searches": "search",
    "Sticker": "star",
    "Snapscore": "trophy",
    "Account": "user",
}


def _card(label: str, value) -> str:
    return (f'<div class="card"><div class="card-value">{value}</div>'
            f'<div class="card-label">{icon(_CARD_ICONS.get(label, ""), 14)} '
            f'{html.escape(label)}</div></div>')


def _cell(value) -> str:
    text = str(value)
    date_part, time_part = split_timestamp(text)
    if date_part:
        return f"<td>{date_span(date_part, time_part)}</td>"
    return f"<td>{html.escape(text)}</td>"


def _detail_table(title: str, headers: list[str], rows: list[list[str]], id_: str,
                  expanded: bool = False) -> str:
    thead = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    tbody = ""
    for row in rows:
        cells = "".join(_cell(c) for c in row)
        tbody += f"<tr>{cells}</tr>\n"

    # Chromium prints a closed <details> as its heading alone and no stylesheet
    # can talk it out of that, so the PDF asks for them open.
    return f'''
<details id="{id_}"{' open' if expanded else ''}>
<summary>{html.escape(title)} ({len(rows)})</summary>
<div style="overflow-x:auto"><table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>
</details>'''


def _wanted(categories: list[str] | None, name: str) -> bool:
    return not categories or name in categories


def _snapscore(json_data: dict) -> str:
    ranking = json_data.get("ranking", {})
    if not isinstance(ranking, dict):
        return ""
    statistics = ranking.get("Statistics", {})
    if not isinstance(statistics, dict):
        return ""
    raw = statistics.get("Snapscore", "")
    if not raw:
        return ""
    try:
        return str(int(float(raw)))
    except (ValueError, TypeError):
        return str(raw)


def stat_card_values(json_data: dict, file_stats: dict, series: dict,
                     categories: list[str] | None = None) -> list[tuple[str, object]]:
    # Label and value only, so the dashboard can render a subset of them.
    cards = [
        ("Memories", file_stats.get("images", 0) + file_stats.get("videos", 0)),
        ("Chat Media", file_stats.get("chat_media_img", 0) + file_stats.get("chat_media_vid", 0)),
        ("Overlays", file_stats.get("overlays", 0)),
    ]

    if series.get("total_messages"):
        cards.append(("Messages", series["total_messages"]))
        cards.append(("Chats", series["total_chats"]))
    if series.get("total_snaps"):
        cards.append(("Snaps", series["total_snaps"]))

    friends = json_data.get("friends", {})
    if isinstance(friends, dict) and _wanted(categories, "friends"):
        cards.append(("Friends", len(friends.get("Friends", []))))
        cards.append(("Blocked", len(friends.get("Blocked Users", []))))
        cards.append(("Deleted", len(friends.get("Deleted Friends", []))))

    talk = json_data.get("talk_history", {})
    if isinstance(talk, dict) and _wanted(categories, "calls"):
        cards.append(("Calls", len(_all_calls(talk))))

    location = json_data.get("location_history", {})
    if isinstance(location, dict) and _wanted(categories, "locations"):
        entries = location.get("Location History", [])
        cards.append(("Locations", len(entries) if isinstance(entries, list) else 0))

    snap_map = json_data.get("snap_map_places_history", {})
    if isinstance(snap_map, dict) and _wanted(categories, "locations"):
        places = snap_map.get("Snap Map Places History", [])
        cards.append(("Snap Map Places", len(places) if isinstance(places, list) else 0))

    search = json_data.get("search_history", {})
    if isinstance(search, dict) and _wanted(categories, "search"):
        entries = search.get("", [])
        cards.append(("Searches", len(entries) if isinstance(entries, list) else 0))

    stickers = json_data.get("custom_sticker", {})
    if isinstance(stickers, dict) and _wanted(categories, "stickers"):
        owned = stickers.get("My Custom Stickers", [])
        cards.append(("Sticker", len(owned) if isinstance(owned, list) else 0))

    account = json_data.get("account", {})
    if isinstance(account, dict) and _wanted(categories, "account"):
        basic = account.get("Basic Information", {})
        username = basic.get("Username", "") if isinstance(basic, dict) else ""
        if username:
            cards.append(("Account", html.escape(username)))

    if _wanted(categories, "engagement"):
        snapscore = _snapscore(json_data)
        if snapscore:
            cards.append(("Snapscore", snapscore))

    return cards


def render_cards(values: list[tuple[str, object]]) -> str:
    return "\n".join(_card(label, value) for label, value in values)


# Split into the two columns by hand, so Account ends up beside Snapscore.
STAT_COLUMNS = [
    [
        ("Messages", ["Messages", "Chats", "Snaps"]),
        ("People", ["Friends", "Blocked", "Deleted"]),
        ("Account", ["Account"]),
    ],
    [
        ("Media", ["Memories", "Chat Media", "Overlays"]),
        ("Activity", ["Calls", "Locations", "Snap Map Places", "Searches", "Sticker", "Snapscore"]),
    ],
]


def _stat_block(heading: str, rows: list[tuple[str, object]], at_bottom: bool) -> str:
    cells = "".join(
        f'<tr><th scope="row">{icon(_CARD_ICONS.get(label, ""))}'
        f"<span>{html.escape(label)}</span></th><td>{value}</td></tr>"
        for label, value in rows
    )
    css_class = "stat-block bottom" if at_bottom else "stat-block"
    return (f'<section class="{css_class}"><h3>{html.escape(heading)}</h3>'
            f"<table><tbody>{cells}</tbody></table></section>")


def build_stats_table(values: list[tuple[str, object]]) -> str:
    known = dict(values)
    columns = []
    for groups in STAT_COLUMNS:
        blocks = []
        for heading, labels in groups:
            rows = [(label, known[label]) for label in labels if label in known]
            if rows:
                blocks.append(_stat_block(heading, rows, at_bottom=heading == "Account"))
        columns.append(f'<div class="stat-column">{"".join(blocks)}</div>')
    return f'<div class="stat-table">{"".join(columns)}</div>'


def build_stat_cards(json_data: dict, file_stats: dict, series: dict,
                     categories: list[str] | None = None) -> str:
    return render_cards(stat_card_values(json_data, file_stats, series, categories))


def _all_calls(talk: dict) -> list[dict]:
    calls = []
    for key in ("Outgoing Calls", "Incoming Calls", "Completed Calls"):
        entries = talk.get(key, [])
        if isinstance(entries, list):
            calls.extend(entry for entry in entries if isinstance(entry, dict))
    return calls


def build_chart_sections(series: dict) -> str:
    if not series.get("months"):
        return ""

    ticks = series["year_ticks"]
    sections = [
        _chart_card("Messages over time",
                    line_chart([("Messages", series["messages_per_month"])], ticks),
                    key="messages-over-time", has_chart=True),
        _activity_card(series),
        _chart_card("Snaps over time", line_chart(
            [("Sent", series["snaps_sent_per_month"]),
             ("Received", series["snaps_received_per_month"])], ticks),
            key="snaps-over-time", has_chart=True),
        _chart_card("Friends over time",
                    line_chart([("Friends", series["friends_per_month"])], ticks),
                    key="friends-over-time", has_chart=True),
        _chart_card("Chat media over time",
                    line_chart([("Chat media", series["chat_media_per_month"])], ticks),
                    key="chat-media-over-time", has_chart=True),
    ]

    if any(series["story_views_per_month"]):
        sections.append(_chart_card(
            "Story views over time",
            line_chart([("Views", series["story_views_per_month"])], ticks),
            key="story-views-over-time", has_chart=True))

    sections.append(_top_list_card("Who writes you most", series["top_senders"],
                                   key="who-writes-you-most",
                                   own_total=series.get("own_messages", 0)))
    sections.append(_top_list_card("Most interacted with", series["most_interacted"],
                                   key="most-interacted-with"))
    # Last and across both columns, so it reads as the summary of the rest.
    sections.append(_chart_card(
        "Type distribution",
        f'<div class="donut-wrap">{donut_chart(series["type_distribution"])}</div>',
        full_width=True, key="type-distribution", has_chart=True))

    return ('<details class="charts-fold" open><summary><span class="chart-title">Charts</span>'
            '</summary><div class="chart-grid-layout">' + "".join(sections) + "</div></details>")


def _chart_card(title: str, body: str, full_width: bool = False, head_extra: str = "",
                key: str = "", has_chart: bool = False) -> str:
    css_class = "chart-card full" if full_width else "chart-card"
    actions = buttons(key, has_chart) if key else ""
    return (f'<section class="{css_class}"><div class="chart-head">'
            f'<span class="chart-title">{html.escape(title)}</span>{head_extra}{actions}</div>'
            f"{body}</section>")


def _activity_card(series: dict) -> str:
    # Both are rendered and the toggle only decides which is visible, so print
    # gets them stacked instead of losing one.
    toggle = ('<span class="chart-toggle no-print">'
              '<button class="active" data-activity="hour">Time of day</button>'
              '<button data-activity="weekday">Weekday</button></span>')
    panels = (f'<div data-activity-panel="hour">{bar_chart(HOUR_LABELS, series["messages_by_hour"])}</div>'
              f'<div data-activity-panel="weekday" hidden>'
              f'{bar_chart(WEEKDAY_LABELS, series["messages_by_weekday"])}</div>')
    return _chart_card("Activity", panels, head_extra=toggle,
                       key="activity-by-hour", has_chart=True)


def _rank_row(name: str, username: str, count: int) -> str:
    # The username follows small, so two people with one name stay apart.
    trailing = f'<span class="rank-user">({html.escape(username)})</span>' if username else ""
    return (f'<li><span class="rank-name">{html.escape(name)}{trailing}</span>'
            f'<span class="rank-count">{count}</span></li>')


def _top_list_card(title: str, entries: list[tuple[str, str, int]], key: str = "",
                   own_total: int = 0) -> str:
    if not entries:
        return ""
    rows = "".join(_rank_row(name, username, count) for name, username, count in entries)
    body = f'<ol class="rank-list">{rows}</ol>'
    if own_total:
        # Below the rule, for comparison with the other direction.
        body += (f'<div class="rank-own"><span class="rank-name">You, to everyone</span>'
                 f'<span class="rank-count">{own_total}</span></div>')
    return _chart_card(title, body, key=key)


def build_detail_tables(json_data: dict, categories: list[str] | None = None,
                        expanded: bool = False) -> str:
    tables = []

    friends = json_data.get("friends", {})
    if isinstance(friends, dict) and _wanted(categories, "friends"):
        rows = [[f.get("Username", ""), f.get("Display Name", ""), f.get("Source", ""),
                 (f.get("Creation Timestamp") or "")[:10]]
                for f in friends.get("Friends", []) if isinstance(f, dict)]
        if rows:
            tables.append(_detail_table("Friends", ["Username", "Display Name", "Source", "Date"],
                                        rows, "friends", expanded))

        for label, key in (("Blocked", "Blocked Users"), ("Deleted", "Deleted Friends")):
            rows = [[e.get("Username", ""), (e.get("Creation Timestamp") or "")[:10]]
                    for e in friends.get(key, []) if isinstance(e, dict)]
            if rows:
                tables.append(_detail_table(label, ["Username", "Date"], rows, label.lower(), expanded))

    talk = json_data.get("talk_history", {})
    if isinstance(talk, dict) and _wanted(categories, "calls"):
        rows = [[c.get("Date & Time", "")[:16], c.get("Type", ""), str(c.get("Length (sec)", "")),
                 f"{c.get('City', '')}, {c.get('Country', '')}".strip(", "), c.get("Network", "")]
                for c in _all_calls(talk)]
        if rows:
            tables.append(_detail_table("Calls", ["Date", "Typ", "Duration (s)", "Location", "Network"],
                                        rows, "calls", expanded))

    location = json_data.get("location_history", {})
    if isinstance(location, dict) and _wanted(categories, "locations"):
        entries = location.get("Location History", [])
        rows = [[e[0][:16], e[1]] for e in entries[:200]
                if isinstance(e, list) and len(e) == 2] if isinstance(entries, list) else []
        if rows:
            tables.append(_detail_table("Locations", ["Date", "Coordinates"], rows, "locations", expanded))

    snap_map = json_data.get("snap_map_places_history", {})
    if isinstance(snap_map, dict) and _wanted(categories, "locations"):
        places = snap_map.get("Snap Map Places History", [])
        rows = [[(p.get("Date") or "")[:16], p.get("Place", ""), p.get("Place Location", "")]
                for p in places if isinstance(p, dict)] if isinstance(places, list) else []
        if rows:
            tables.append(_detail_table("Snap Map Places", ["Date", "Place", "Location"], rows, "snapmap", expanded))

    search = json_data.get("search_history", {})
    if isinstance(search, dict) and _wanted(categories, "search"):
        entries = search.get("", [])
        rows = [[s.get("Date and time (hourly)", "")[:16], s.get("Search Term", ""), s.get("Location", "")]
                for s in entries if isinstance(s, dict)] if isinstance(entries, list) else []
        if rows:
            tables.append(_detail_table("Search History", ["Date", "Search Term", "Location"], rows, "search", expanded))

    return "\n".join(tables)


ACTIVITY_TOGGLE_JS = """
(function () {
    "use strict";
    var buttons = document.querySelectorAll("[data-activity]");
    Array.prototype.forEach.call(buttons, function (button) {
        button.addEventListener("click", function () {
            var wanted = button.getAttribute("data-activity");
            Array.prototype.forEach.call(buttons, function (other) {
                other.classList.toggle("active", other === button);
            });
            Array.prototype.forEach.call(document.querySelectorAll("[data-activity-panel]"), function (panel) {
                panel.hidden = panel.getAttribute("data-activity-panel") !== wanted;
            });
        });
    });
})();
"""

STATS_CSS = """
.cards { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; margin-bottom: 30px; }
.card { background: #2a2a2a; border-radius: 10px; padding: 16px 24px; text-align: center; min-width: 130px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.card-value { font-size: 28px; font-weight: 700; color: #FFFE00; }
.card-label { font-size: 13px; color: #aaa; margin-top: 4px; }
.stat-table { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 28px; margin-bottom: 26px; }
.stat-column { display: flex; flex-direction: column; gap: 14px; }
.stat-block.bottom { margin-top: auto; }
.stat-block th { display: flex; align-items: center; gap: 8px; }
.stat-block .icon { color: #777; }
.stat-block h3 { font-size: 11px; color: #777; text-transform: uppercase; letter-spacing: 0.09em; font-weight: 600; padding-bottom: 4px; border-bottom: 1px solid #333; }
.stat-block table { width: 100%; border-collapse: collapse; font-size: 14px; }
.stat-block th { text-align: left; font-weight: 400; color: #bbb; padding: 6px 0; background: none; border-bottom: 1px solid #262626; }
.stat-block td { text-align: right; color: #FFFE00; font-weight: 600; font-variant-numeric: tabular-nums; padding: 6px 0; border-bottom: 1px solid #262626; }
.chart-grid-layout { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.chart-card { background: #222; border-radius: 10px; padding: 16px; grid-column: span 1; margin: 0; }
.chart-card.full { grid-column: span 2; }
.chart-head { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 12px; }
.chart-title { font-size: 13px; color: #aaa; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }
/* A donut carries no time axis, so stretching it to the full card width only
   makes it enormous. */
.donut-wrap { max-width: 210px; margin: 0 auto; }
.charts-fold { background: none; border-radius: 0; margin: 0 0 24px; }
.charts-fold > summary { display: flex; align-items: center; gap: 10px; padding: 10px 0; color: inherit; list-style: none; }
.charts-fold > summary::-webkit-details-marker { display: none; }
.charts-fold > summary::after { content: "Hide all"; color: #777; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
.charts-fold:not([open]) > summary::after { content: "Show all"; }
.charts-fold > summary:hover .chart-title, .charts-fold > summary:hover::after { color: #FFFE00; }
.rank-own { display: flex; justify-content: space-between; gap: 12px; padding: 8px 0 0; margin-top: 6px; border-top: 1px solid #444; font-size: 13px; }
.chart-toggle { display: inline-flex; gap: 4px; }
.chart-toggle button { background: #2f2f2f; color: #bbb; border: 1px solid #444; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-family: inherit; cursor: pointer; }
.chart-toggle button.active { background: #FFFE00; color: #1a1a1a; border-color: #FFFE00; font-weight: 600; }
.rank-list { list-style: none; counter-reset: rank; }
.rank-list li { counter-increment: rank; display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-bottom: 1px solid #2a2a2a; font-size: 13px; }
.rank-list li::before { content: counter(rank) "."; color: #666; width: 22px; flex: 0 0 auto; }
.rank-name { flex: 1 1 auto; color: #ddd; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-user { color: #8d8d8d; font-size: 11.5px; margin-left: 5px; }
.rank-count { color: #FFFE00; font-variant-numeric: tabular-nums; }
details { background: #222; border-radius: 8px; margin: 10px 0; }
summary { padding: 12px 16px; cursor: pointer; font-weight: 600; color: #ddd; }
summary:hover { color: #FFFE00; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 12px; background: #333; color: #aaa; border-bottom: 1px solid #444; }
td { padding: 6px 12px; border-bottom: 1px solid #2a2a2a; }
tr:hover { background: #2a2a2a; }
@media (max-width: 760px) {
  .chart-grid-layout, .stat-table { grid-template-columns: minmax(0, 1fr); }
  .chart-card, .chart-card.full { grid-column: span 1; }
  .cards { gap: 8px; }
  .card { flex: 1 1 calc(50% - 8px); min-width: 0; padding: 12px 10px; }
  .card-value { font-size: 22px; }
  table { font-size: 12px; }
}
@media print {
  /* Nothing yellow survives on white paper, so every accent goes dark. */
  h1, h2, h3 { color: #000 !important; text-shadow: none !important; }
  a { color: #333; }
  mark { background: #eee; color: #000; }
  .card { border: 1px solid #ccc; box-shadow: none; }
  .card-value { color: #000; }
  .stat-block td { color: #000; }
  .stat-block th { color: #333; }
  .chart-card { background: none; border: 1px solid #ddd; break-inside: avoid; }
  .charts-fold > summary::after { content: ""; }
  .chart-title { color: #000; }
  .rank-name { color: #000; }
  .rank-user { color: #666; }
  .rank-count { color: #000; }
  .rank-list li { border-bottom: 1px solid #e0e0e0; }
  .rank-own { border-top: 1px solid #999; }
  /* The detail tables are folded shut on screen. On paper there is nothing to
     click, so they are opened and lightened for white. */
  details { background: none; border: 1px solid #ddd; break-inside: avoid; }
  details > *:not(summary) { display: block !important; }
  summary { color: #000; }
  summary::marker { content: ""; }
  th { background: #f0f0f0; color: #333; border-bottom: 1px solid #bbb; }
  td { color: #222; border-bottom: 1px solid #e5e5e5; }
  tr:hover { background: none; }
  [data-activity-panel] { display: block !important; }
  /* folded charts would print as a heading alone, so paper always gets all of them */
  .charts-fold > *:not(summary) { display: block !important; }
  .no-print { display: none; }
}
"""


def generate_stats_html(
    json_data: dict,
    file_stats: dict,
    output_dir: Path,
    categories: list[str] | None = None,
    dry_run: bool = False,
    file_index: list[dict] | None = None,
    filename: str = "stats.html",
    cover: str = "",
    expanded: bool = False,
) -> bool:
    if dry_run:
        return True

    series = build_series(json_data, file_index)
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
@media print {{ body {{ background: #fff; color: #000; border-top: none; }} }}
{STATS_CSS}
{CHART_CSS}
{ICON_CSS}
{COVER_CSS}
{date_format_css()}
</style>
</head>
<body>
{cover}
<div class="header-bar no-print">{date_format_picker_html()}<button class="btn-print" onclick="window.print()">Export PDF</button></div>
<h1>Snapchat Export Stats</h1>
{build_stats_table(stat_card_values(json_data, file_stats, series, categories))}
{build_chart_sections(series)}
{build_detail_tables(json_data, categories, expanded)}
<script>{date_format_js()}</script>
<script>{ACTIVITY_TOGGLE_JS}</script>
</body>
</html>'''

    (output_dir / filename).write_text(page, encoding="utf-8")
    return True
