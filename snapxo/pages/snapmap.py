# Locations plays back where you were, Memories shows where things were saved.

import json
from pathlib import Path

from rich.console import Console

from ..facts.mapdata import centre_of, location_points, memory_points
from ..parts.icons import ICON_CSS, icon
from ..parts.shared import date_format_css, date_format_js, date_format_picker_html

console = Console()

LEAFLET_CSS = ('<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" '
               'integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" '
               'crossorigin="anonymous" />\n'
               '<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" '
               'integrity="sha384-pmjIAcz2bAn0xukfxADbZIb3t8oRT9Sv0rvO+BR5Csr6Dhqq+nZs59P0pPKQJkEV" '
               'crossorigin="anonymous" />\n'
               '<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" '
               'integrity="sha384-wgw+aLYNQ7dlhK47ZPK7FRACiq7ROZwgFNg0m04avm4CaXS+Z9Y7nMu8yNjBKYC+" '
               'crossorigin="anonymous" />\n'
               '<link rel="stylesheet" href="https://unpkg.com/nouislider@15.7.1/dist/nouislider.min.css" '
               'integrity="sha384-PSZaVsyG9jDu8hFaSJev5s/9poIJlX7cuxSGdqCgXRHpo2DzIaZAyCd2rG/DJJmV" '
               'crossorigin="anonymous" />')

LEAFLET_JS = ('<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" '
              'integrity="sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH" '
              'crossorigin="anonymous"></script>\n'
              '<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js" '
              'integrity="sha384-eXVCORTRlv4FUUgS/xmOyr66XBVraen8ATNLMESp92FKXLAMiKkerixTiBvXriZr" '
              'crossorigin="anonymous"></script>\n'
              '<script src="https://unpkg.com/nouislider@15.7.1/dist/nouislider.min.js" '
              'integrity="sha384-/gBUOLHADjY2rp6bHB0IyW9AC28q4OsnirJScje4l1crgYW7Qarx3dH8zcqcUgmy" '
              'crossorigin="anonymous"></script>')


def _as_script(name: str, payload) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"window.{name}={encoded};"


def generate_map_html(
    json_data: dict,
    output_dir: Path,
    file_index: list[dict] | None = None,
    dry_run: bool = False,
) -> bool:
    if dry_run:
        return True

    locations = location_points(json_data)
    memories = memory_points(json_data, file_index)
    if not locations and not memories:
        console.print("[yellow]No GPS data found for map[/yellow]")
        return False

    lat, lon = centre_of(locations or memories)
    page = MAP_PAGE.format(
        latitude=lat,
        longitude=lon,
        leaflet_css=LEAFLET_CSS,
        leaflet_js=LEAFLET_JS,
        picker_css=date_format_css(),
        picker_html=date_format_picker_html("Dates"),
        picker_js=date_format_js(),
        icon_css=ICON_CSS,
        play_icon=icon("play", 15),
        map_css=MAP_CSS,
        map_js=MAP_JS,
        data=_as_script("SNAPXO_LOCATIONS", locations) + _as_script("SNAPXO_MEMORIES", memories),
    )
    (output_dir / "map.html").write_text(page, encoding="utf-8")
    console.print(f"Map generated with {len(locations)} locations and {len(memories)} memories")
    return True


MAP_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a1a; color: #e0e0e0; overflow: hidden; }
.map-shell { display: flex; flex-direction: column; height: 100vh; height: 100dvh; }
/* Clear of a notch on top, clear of the home bar at the bottom. */
.map-top { display: flex; flex: 0 0 auto; align-items: center; gap: 14px; flex-wrap: wrap; background: #141414; border-bottom: 1px solid #2c2c2c; z-index: 500;
  padding: calc(10px + env(safe-area-inset-top, 0px)) calc(16px + env(safe-area-inset-right, 0px)) 10px calc(16px + env(safe-area-inset-left, 0px)); }
.brand { color: #FFFE00; font-weight: 700; }
.mode-switch { display: flex; gap: 4px; }
.mode-switch button { background: none; border: none; color: #999; font-family: inherit; font-size: 14px; padding: 8px 14px; border-radius: 8px; cursor: pointer; }
.mode-switch button:hover { color: #e0e0e0; background: #222; }
.mode-switch button.active { background: #FFFE00; color: #1a1a1a; font-weight: 600; }
.map-count { color: #888; font-size: 12.5px; margin-left: auto; }
.map-body { position: relative; flex: 1 1 auto; display: flex; min-height: 0; }
#map { flex: 1 1 auto; height: 100%; background: #111; }
.leaflet-tile { filter: brightness(0.85) contrast(1.1) saturate(0.8); }
.leaflet-control-zoom a { background: #222 !important; color: #e0e0e0 !important; border-color: #444 !important; }
.leaflet-popup-content-wrapper, .leaflet-popup-tip { background: #1a1a1a; color: #e0e0e0; border: 1px solid #333; }
.marker-cluster { background: rgba(255,252,0,0.25) !important; }
.marker-cluster div { background: rgba(255,252,0,0.75) !important; color: #111 !important; font-weight: 600; }

/* The strip of media for a place. A column on the right, a sheet from the top
   on a phone, where a side panel would leave the map a sliver. */
.strip { flex: 0 0 320px; background: #1c1c1c; border-left: 1px solid #2c2c2c; display: flex; flex-direction: column; }
.strip[hidden] { display: none; }
.strip-head { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-bottom: 1px solid #2c2c2c; }
.strip-title { font-size: 13px; font-weight: 600; color: #eee; }
.strip-sub { font-size: 11.5px; color: #888; }
.strip-close { margin-left: auto; background: none; border: 1px solid #3a3a3a; color: #aaa; border-radius: 6px; font-family: inherit; font-size: 16px; line-height: 1; padding: 3px 9px; cursor: pointer; }
.strip-close:hover { color: #fff; border-color: #666; }
.strip-handle { display: none; }
.strip-list { flex: 1 1 auto; min-height: 0; overflow-y: auto; -webkit-overflow-scrolling: touch; overscroll-behavior: contain; padding: 10px; display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; align-content: start; grid-auto-rows: max-content; }
.strip-item { background: #232323; border-radius: 8px; overflow: hidden; text-decoration: none; color: inherit; display: block; }
.strip-item:hover { background: #2c2c2c; }
.strip-item img { width: 100%; height: 150px; object-fit: cover; display: block; background: #2a2a2a; }
.strip-item .placeholder { display: flex; align-items: center; justify-content: center; height: 150px; background: #2a2a2a; color: #666; font-size: 26px; }
.strip-meta { padding: 7px 9px 9px; font-size: 11px; color: #bbb; }
.strip-meta .when { display: block; color: #ddd; font-size: 12px; }
.strip-meta .at { display: block; margin-top: 1px; }
.strip-guess { display: block; margin-top: 6px; padding-top: 5px; border-top: 1px solid #333; color: #c9a227; font-size: 10px; }
.strip-note { grid-column: 1 / -1; color: #888; font-size: 12px; line-height: 1.5; padding: 4px 2px 10px; }

/* The time bar sits at the bottom on every screen, because that is where a
   thumb already is. */
.time-bar { display: flex; flex: 0 0 auto; align-items: center; gap: 12px; flex-wrap: wrap; background: #141414; border-top: 1px solid #2c2c2c; z-index: 500;
  padding: 10px calc(16px + env(safe-area-inset-right, 0px)) calc(10px + env(safe-area-inset-bottom, 0px)) calc(16px + env(safe-area-inset-left, 0px)); }
.time-fields { display: flex; align-items: center; gap: 8px; }
.time-fields label { color: #777; font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; }
.month-pick, .month-input { background: #262626; color: #e0e0e0; border: 1px solid #4a4a4a; border-radius: 8px; padding: 10px 12px; font-family: inherit; font-size: 14px; min-width: 118px; cursor: pointer; }
.month-pick:hover, .month-pick:focus, .month-input:hover, .month-input:focus { border-color: #FFFE00; outline: none; }
/* The month picker where the browser has one, the list of months where it does
   not. Only ever one of the two is on the page. */
.month-input { color-scheme: dark; }
.time-fields .month-input { display: none; }
.time-fields.calendar .month-input { display: inline-block; }
.time-fields.calendar .month-pick { display: none; }
.step-btn, .play-btn { display: inline-flex; align-items: center; justify-content: center; gap: 7px; background: #2c2c2c; border: 1px solid #4a4a4a; color: #e0e0e0; border-radius: 8px; font-family: inherit; font-size: 14px; min-height: 42px; padding: 0 14px; cursor: pointer; }
.step-btn { min-width: 46px; font-size: 17px; }
.play-btn { background: #FFFE00; border-color: #FFFE00; color: #1a1a1a; font-weight: 700; min-width: 108px; }
.play-btn:hover { background: #e6e500; }
.step-btn:hover { border-color: #FFFE00; color: #FFFE00; }
.speeds { display: flex; gap: 4px; }
.play-btn[hidden], .speeds[hidden] { display: none; }
.speeds button { background: #262626; border: 1px solid #444; color: #aaa; border-radius: 6px; font-family: inherit; font-size: 12px; padding: 7px 10px; cursor: pointer; }
.speeds button.active { background: #FFFE00; border-color: #FFFE00; color: #1a1a1a; font-weight: 600; }
.time-slider { flex: 1 1 240px; min-width: 180px; }
.playhead { color: #FFFE00; font-size: 12.5px; font-variant-numeric: tabular-nums; min-width: 96px; }
.noUi-target { background: #262626; border: 1px solid #444; box-shadow: none; height: 8px; }
.noUi-connect { background: #FFFE00; }
.noUi-handle { background: #FFFE00; border: 1px solid #FFFE00; border-radius: 50%; box-shadow: none; width: 20px !important; height: 20px !important; right: -10px !important; top: -7px !important; cursor: grab; }
.noUi-handle::before, .noUi-handle::after { display: none; }

@media (max-width: 820px) {
  /* The sheet comes down from the top with a handle to pull it away again. */
  .map-body { flex-direction: column; }
  .strip { position: absolute; inset: 0 0 auto 0; z-index: 800; flex: 0 0 auto; max-height: 62%; border-left: none; border-bottom: 1px solid #2c2c2c; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
  .strip.collapsed { max-height: none; }
  .strip.collapsed .strip-list, .strip.collapsed .strip-head { display: none; }
  .strip-handle { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 8px; background: none; border: none; width: 100%; color: #888; font-family: inherit; font-size: 12px; cursor: pointer; }
  .strip-handle::before { content: ""; width: 42px; height: 4px; border-radius: 2px; background: #555; }
  .strip.collapsed .strip-handle::before { background: #FFFE00; }
  .time-slider { display: none; }
  .speeds { flex: 1 1 100%; justify-content: center; }
  .speeds button { flex: 1 1 auto; font-size: 13px; padding: 9px 0; }
  .map-top { gap: 10px; padding-top: calc(20px + env(safe-area-inset-top, 0px)); }
  .time-bar { gap: 8px; padding: 10px 12px calc(10px + env(safe-area-inset-bottom, 0px)); }
  .time-fields { flex: 1 1 100%; justify-content: space-between; }
  .month-pick, .month-input { flex: 1 1 0; min-width: 0; padding: 9px 8px; font-size: 13px; }
  .play-btn { order: 1; flex: 1 1 auto; min-width: 0; }
  .step-btn { order: 2; }
  .time-fields { order: 3; }
  .speeds { order: 4; }
  .date-format-picker { order: 5; }
  .map-count { flex: 1 1 100%; margin-left: 0; }
}
"""

MAP_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>Snap Map</title>
{leaflet_css}
<style>
{map_css}
{icon_css}
{picker_css}
</style>
</head>
<body>
<div class="map-shell">
<header class="map-top">
<span class="brand">Snap Map</span>
<nav class="mode-switch">
<button class="active" data-mode="locations">Locations</button>
<button data-mode="memories">Memories</button>
</nav>
<span class="map-count" id="map-count"></span>
</header>

<div class="map-body">
<div id="map"></div>
<aside class="strip" id="strip" hidden>
<button class="strip-handle" id="strip-handle" type="button">Hide</button>
<div class="strip-head">
<span><span class="strip-title" id="strip-title"></span>
<span class="strip-sub" id="strip-sub"></span></span>
<button class="strip-close" id="strip-close" type="button" title="Close">&times;</button>
</div>
<div class="strip-list" id="strip-list"></div>
</aside>
</div>

<footer class="time-bar">
<button class="play-btn" id="play">{play_icon} Play</button>
<div class="time-fields">
<label for="from-month">From</label>
<input class="month-input" id="from-month-input" type="month">
<select class="month-pick" id="from-month"></select>
<label for="to-month">To</label>
<input class="month-input" id="to-month-input" type="month">
<select class="month-pick" id="to-month"></select>
</div>
<button class="step-btn" id="step-back" title="Previous month">&#8249;</button>
<button class="step-btn" id="step-forward" title="Next month">&#8250;</button>
<div class="time-slider" id="time-slider"></div>
<div class="speeds">
<button class="active" data-speed="1">1x</button>
<button data-speed="2">2x</button>
<button data-speed="5">5x</button>
<button data-speed="10">10x</button>
<button data-speed="25">25x</button>
</div>
<span class="playhead" id="playhead"></span>
{picker_html}
</footer>
</div>

<script>{data}</script>
<script>{picker_js}</script>
{leaflet_js}
<script>
window.SNAPXO_MAP_CENTRE = [{latitude}, {longitude}];
</script>
<script>{map_js}</script>
</body>
</html>
"""

MAP_JS = r"""
(function () {
    "use strict";
    var LOCATIONS = window.SNAPXO_LOCATIONS || [];
    var MEMORIES = window.SNAPXO_MEMORIES || [];
    var MONTHS = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"];

    function stamp(text) {
        return new Date(String(text).replace(" UTC", "Z").replace(" ", "T")).getTime() || 0;
    }

    [LOCATIONS, MEMORIES].forEach(function (set) {
        set.forEach(function (point) { point.ts = stamp(point.t); });
        set.sort(function (a, b) { return a.ts - b.ts; });
    });

    var all = LOCATIONS.concat(MEMORIES).sort(function (a, b) { return a.ts - b.ts; });
    if (!all.length) return;

    var onPhone = window.matchMedia("(max-width: 820px)");

    var map = L.map("map", { zoomControl: false }).setView(window.SNAPXO_MAP_CENTRE, 6);
    // Top left on a phone is where the sheet comes down, so the buttons move out
    // from under it.
    var zoomControl = L.control.zoom({ position: onPhone.matches ? "bottomleft" : "topleft" });
    zoomControl.addTo(map);
    onPhone.addEventListener("change", function (event) {
        zoomControl.setPosition(event.matches ? "bottomleft" : "topleft");
    });
    map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank">Leaflet</a>');
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 19,
    }).addTo(map);

    var pathLayer = L.layerGroup().addTo(map);
    var clusterLayer = L.markerClusterGroup({
        // Clicking a cluster opens the strip instead of zooming, because seeing
        // what is there is the point. Zooming still splits them apart.
        zoomToBoundsOnClick: false,
        showCoverageOnHover: false,
        maxClusterRadius: 45,
    });

    // One point every BASE_TICK_MS at 1x. Below the floor the tick cannot get
    // shorter, so it draws several points at once instead.
    var BASE_TICK_MS = 450;
    var FASTEST_TICK_MS = 40;

    var mode = "locations";
    var speed = 1;
    var playing = false;
    var playTimer = null;
    var playIndex = 0;
    var playPoints = [];

    var months = buildMonths();
    var fromIndex = 0;
    var toIndex = 0;
    var slider = document.getElementById("time-slider");
    var hasSlider = false;
    var fromPick = document.getElementById("from-month");
    var toPick = document.getElementById("to-month");
    var fromInput = document.getElementById("from-month-input");
    var toInput = document.getElementById("to-month-input");
    var playButton = document.getElementById("play");
    var playhead = document.getElementById("playhead");
    var countLabel = document.getElementById("map-count");
    var strip = document.getElementById("strip");
    var stripList = document.getElementById("strip-list");
    // A busy spot holds thousands of memories. Handing all of them to the grid
    // at once collapses every row to nothing, so it fills up while scrolling.
    var STRIP_PAGE = 60;
    var stripPoints = [];
    var stripShown = 0;

    function buildMonths() {
        var first = new Date(all[0].ts);
        var last = new Date(all[all.length - 1].ts);
        var list = [];
        var year = first.getUTCFullYear();
        var month = first.getUTCMonth();
        while (year < last.getUTCFullYear() ||
               (year === last.getUTCFullYear() && month <= last.getUTCMonth())) {
            list.push({ year: year, month: month,
                        label: MONTHS[month] + " " + year,
                        start: Date.UTC(year, month, 1),
                        end: Date.UTC(year, month + 1, 1) - 1 });
            month += 1;
            if (month > 11) { year += 1; month = 0; }
        }
        return list;
    }

    function monthValue(index) {
        var entry = months[index];
        return entry.year + "-" + (entry.month < 9 ? "0" : "") + (entry.month + 1);
    }

    function indexOfValue(value) {
        if (!value) return -1;
        for (var i = 0; i < months.length; i++) {
            if (monthValue(i) === value) return i;
        }
        return value < monthValue(0) ? 0 : months.length - 1;
    }

    // Browsers that have a month picker get one, the rest get the list of months.
    function hasMonthInput() {
        var probe = document.createElement("input");
        probe.setAttribute("type", "month");
        return probe.type === "month";
    }

    function fillPickers() {
        var options = months.map(function (entry, index) {
            return '<option value="' + index + '">' + entry.label + "</option>";
        }).join("");
        fromPick.innerHTML = options;
        toPick.innerHTML = options;
        [fromInput, toInput].forEach(function (input) {
            input.min = monthValue(0);
            input.max = monthValue(months.length - 1);
        });
        document.querySelector(".time-fields").classList.toggle("calendar", hasMonthInput());
        setRange(0, months.length - 1);
    }

    // One place holds the period, the three controls only show it.
    function setRange(from, to, source) {
        fromIndex = Math.max(0, Math.min(from, to, months.length - 1));
        toIndex = Math.min(months.length - 1, Math.max(from, to, 0));
        fromPick.value = String(fromIndex);
        toPick.value = String(toIndex);
        fromInput.value = monthValue(fromIndex);
        toInput.value = monthValue(toIndex);
        if (hasSlider && source !== "slider") {
            slider.noUiSlider.set([fromIndex, toIndex]);
        }
    }

    function applyRange(from, to, source) {
        setRange(from, to, source);
        if (playing) stopPlaying(); else render();
    }

    function window_() {
        return { from: months[fromIndex].start, to: months[toIndex].end,
                 fromIndex: fromIndex, toIndex: toIndex };
    }

    function inWindow(set) {
        var span = window_();
        return set.filter(function (point) {
            return point.ts >= span.from && point.ts <= span.to;
        });
    }

    function dayOf(point) {
        return String(point.t).slice(0, 10);
    }

    function timeOf(point) {
        return String(point.t).slice(11, 16);
    }

    // --- Locations -------------------------------------------------------
    function dot(point, filled) {
        return L.circleMarker([point.lat, point.lon], {
            radius: filled ? 6 : 5,
            color: "#FFFE00",
            weight: 2,
            fillColor: "#FFFE00",
            fillOpacity: filled ? 0.95 : 0.35,
        }).bindPopup("<b>" + dayOf(point) + " " + timeOf(point) + "</b>" +
                     (point.acc ? "<br>accurate to about " + point.acc + " m" : ""));
    }

    function leg(from, to) {
        return L.polyline([[from.lat, from.lon], [to.lat, to.lon]],
                          { color: "#FFFE00", weight: 2, opacity: 0.55 });
    }

    function drawStep(points, index, filled) {
        dot(points[index], filled).addTo(pathLayer);
        if (index > 0) leg(points[index - 1], points[index]).addTo(pathLayer);
    }

    function drawLocations() {
        pathLayer.clearLayers();
        var points = inWindow(LOCATIONS);
        for (var i = 0; i < points.length; i++) drawStep(points, i, false);
        countLabel.textContent = points.length + " locations in this period";
        playhead.textContent = "";
    }

    // --- Memories --------------------------------------------------------
    function drawMemories() {
        clusterLayer.clearLayers();
        var points = inWindow(MEMORIES);
        points.forEach(function (point) {
            var marker = L.circleMarker([point.lat, point.lon], {
                radius: 6, color: "#FFFE00", weight: 2,
                fillColor: point.sure ? "#FFFE00" : "#c9a227",
                fillOpacity: 0.9,
            });
            marker.snapxo = point;
            clusterLayer.addLayer(marker);
        });
        countLabel.textContent = points.length + " memories in this period";
    }

    function stripItem(point) {
        var picture = point.thumb
            ? '<img src="' + point.thumb + '" loading="lazy" alt="">'
            : '<div class="placeholder">' + (point.kind === "video" ? "&#9654;" : "&#128247;") + "</div>";
        var guess = point.sure ? "" :
            '<span class="strip-guess">picture uncertain</span>';
        var inner = picture +
            '<div class="strip-meta"><span class="when" data-date="' + dayOf(point) + '">' +
            dayOf(point) + '</span><span class="at">' + timeOf(point) + "</span>" + guess + "</div>";
        return point.file
            ? '<a class="strip-item" href="' + point.file + '" target="_blank" rel="noopener">' + inner + "</a>"
            : '<div class="strip-item">' + inner + "</div>";
    }

    function showMoreOfStrip() {
        if (stripShown >= stripPoints.length) return;
        var next = stripPoints.slice(stripShown, stripShown + STRIP_PAGE);
        var holder = document.createElement("div");
        holder.innerHTML = next.map(stripItem).join("");
        while (holder.firstChild) stripList.appendChild(holder.firstChild);
        stripShown += next.length;
        if (window.SEODate) window.SEODate.apply(stripList);
    }

    function openStrip(points, title) {
        var unsure = points.filter(function (point) { return !point.sure; }).length;
        document.getElementById("strip-title").textContent = title;
        document.getElementById("strip-sub").textContent =
            points.length + (points.length === 1 ? " memory" : " memories");

        stripList.innerHTML = unsure
            ? '<p class="strip-note">Snapchat never says which picture belongs to which ' +
              'point. On a day when things were saved in several places the position is ' +
              'still right, but the thumbnail is a guess. Those are marked.</p>'
            : "";
        stripList.scrollTop = 0;
        stripPoints = points;
        stripShown = 0;
        showMoreOfStrip();
        strip.hidden = false;
        strip.classList.remove("collapsed");
    }

    stripList.addEventListener("scroll", function () {
        if (this.scrollTop + this.clientHeight >= this.scrollHeight - 400) showMoreOfStrip();
    });

    clusterLayer.on("clusterclick", function (event) {
        var points = event.layer.getAllChildMarkers().map(function (marker) {
            return marker.snapxo;
        }).sort(function (a, b) { return b.ts - a.ts; });
        openStrip(points, "This spot");
    });

    clusterLayer.on("click", function (event) {
        if (event.layer && event.layer.snapxo) {
            openStrip([event.layer.snapxo], dayOf(event.layer.snapxo));
        }
    });

    // --- playback --------------------------------------------------------
    function stopPlaying() {
        playing = false;
        if (playTimer) { clearInterval(playTimer); playTimer = null; }
        playButton.innerHTML = playButton.dataset.idle;
        render();
    }

    function pace() {
        var wanted = BASE_TICK_MS / speed;
        var tick = Math.max(FASTEST_TICK_MS, wanted);
        return { tick: tick, stride: Math.max(1, Math.round(tick / wanted)) };
    }

    function playTick() {
        var stride = pace().stride;
        for (var step = 0; step < stride && playIndex < playPoints.length; step++) {
            drawStep(playPoints, playIndex, true);
            playIndex += 1;
        }
        var current = playPoints[playIndex - 1];
        playhead.textContent = dayOf(current);
        // Following the trail is the point, so the map keeps the newest dot in view.
        map.panTo([current.lat, current.lon], { animate: true, duration: 0.25 });
        if (playIndex >= playPoints.length) stopPlaying();
    }

    function startPlaying() {
        playPoints = inWindow(LOCATIONS);
        if (!playPoints.length) return;
        playing = true;
        playIndex = 0;
        playButton.innerHTML = "&#10073;&#10073; Pause";
        pathLayer.clearLayers();
        countLabel.textContent = playPoints.length + " locations in this period";
        playTimer = setInterval(playTick, pace().tick);
    }

    // --- wiring ----------------------------------------------------------
    function render() {
        if (mode === "locations") {
            map.removeLayer(clusterLayer);
            pathLayer.addTo(map);
            drawLocations();
        } else {
            pathLayer.clearLayers();
            map.removeLayer(pathLayer);
            clusterLayer.addTo(map);
            drawMemories();
        }
        var playable = mode === "locations";
        playButton.hidden = !playable;
        document.querySelector(".speeds").hidden = !playable;
    }

    function setMode(next) {
        if (playing) stopPlaying();
        mode = next;
        strip.hidden = true;
        Array.prototype.forEach.call(document.querySelectorAll("[data-mode]"), function (button) {
            button.classList.toggle("active", button.getAttribute("data-mode") === next);
        });
        render();
    }

    function stepBy(offset) {
        applyRange(fromIndex + offset, toIndex + offset);
    }

    if (window.noUiSlider && months.length > 1) {
        noUiSlider.create(slider, {
            start: [0, months.length - 1],
            connect: true,
            step: 1,
            range: { min: 0, max: months.length - 1 },
        });
        hasSlider = true;
        slider.noUiSlider.on("update", function (values) {
            setRange(Math.round(values[0]), Math.round(values[1]), "slider");
        });
        slider.noUiSlider.on("change", function () {
            if (playing) stopPlaying(); else render();
        });
    }

    [fromPick, toPick].forEach(function (picker) {
        picker.addEventListener("change", function () {
            applyRange(parseInt(fromPick.value, 10), parseInt(toPick.value, 10));
        });
    });

    [fromInput, toInput].forEach(function (input) {
        input.addEventListener("change", function () {
            applyRange(indexOfValue(fromInput.value), indexOfValue(toInput.value));
        });
    });

    playButton.dataset.idle = playButton.innerHTML;
    playButton.addEventListener("click", function () {
        if (playing) stopPlaying(); else startPlaying();
    });

    document.getElementById("step-back").addEventListener("click", function () { stepBy(-1); });
    document.getElementById("step-forward").addEventListener("click", function () { stepBy(1); });

    document.querySelector(".speeds").addEventListener("click", function (event) {
        var button = event.target.closest("[data-speed]");
        if (!button) return;
        speed = parseInt(button.getAttribute("data-speed"), 10);
        Array.prototype.forEach.call(document.querySelectorAll("[data-speed]"), function (other) {
            other.classList.toggle("active", other === button);
        });
        if (playing) {
            clearInterval(playTimer);
            playTimer = setInterval(playTick, pace().tick);
        }
    });

    document.querySelector(".mode-switch").addEventListener("click", function (event) {
        var button = event.target.closest("[data-mode]");
        if (button) setMode(button.getAttribute("data-mode"));
    });

    document.getElementById("strip-close").addEventListener("click", function () {
        strip.hidden = true;
    });
    document.getElementById("strip-handle").addEventListener("click", function () {
        strip.classList.toggle("collapsed");
        this.textContent = strip.classList.contains("collapsed") ? "Show" : "Hide";
    });

    fillPickers();
    render();
})();
"""
