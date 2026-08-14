import json
import math
import re
from pathlib import Path

from rich.console import Console

from .webassets import date_format_css, date_format_js, date_format_picker_html

console = Console()

LOCATION_RE = re.compile(r"Latitude,\s*Longitude:\s*([-\d.]+),\s*([-\d.]+)")


def _collect_markers(json_data: dict) -> list[dict]:
    # All GPS markers from the JSON sources, sorted by date:
    #   memories_history        "Location": "Latitude, Longitude: -48.87667, -123.39333"
    #   location_history        [["2026-07-20 14:32:05 UTC", "-48.877, -123.393"]]
    #   snap_map_places_history has no coordinates, so it cannot go on the map
    markers = []

    # memories_history.json: GPS as string
    memories = json_data.get("memories_history", {})
    if isinstance(memories, dict):
        for entry in memories.get("Saved Media", []):
            if not isinstance(entry, dict):
                continue
            location = entry.get("Location", "")
            m = LOCATION_RE.search(location)
            if m:
                try:
                    lat, lon = float(m.group(1)), float(m.group(2))
                    if lat != 0 or lon != 0:
                        markers.append({
                            "lat": lat, "lon": lon,
                            "type": "memory",
                            "date": str(entry.get("Date", "")),
                            "label": entry.get("Media Type", "Memory"),
                        })
                except ValueError:
                    continue

    # location_history.json: "Location History": [["timestamp", "lat, lon"], ...]
    location = json_data.get("location_history", {})
    if isinstance(location, dict):
        loc_list = location.get("Location History", [])
        if isinstance(loc_list, list):
            for entry in loc_list:
                if isinstance(entry, list) and len(entry) == 2:
                    timestamp, coords = entry
                    try:
                        parts = coords.split(",")
                        if len(parts) == 2:
                            lat, lon = float(parts[0].strip()), float(parts[1].strip())
                            if lat != 0 or lon != 0:
                                markers.append({
                                    "lat": lat, "lon": lon,
                                    "type": "location",
                                    "date": str(timestamp),
                                    "label": "Location",
                                })
                    except (ValueError, AttributeError):
                        continue

    # snap_map_places_history.json has no coordinates, so it is skipped here
    # These entries have no lat/lon so they can't be placed on the map.

    # Filter out markers without valid coordinates
    map_markers = [m for m in markers if m["lat"] != 0 or m["lon"] != 0]

    # Sort by date chronologically
    map_markers.sort(key=lambda m: m["date"])

    return map_markers


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Distance in metres between two GPS points.
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _find_nearby_media(
    marker: dict,
    file_index: list[dict],
    max_dist_m: float = 100.0,
) -> list[dict]:
    # Media files matching a marker by same day and GPS proximity.
    marker_date = marker["date"][:10]
    nearby = []
    for fi in file_index:
        fi_date = str(fi.get("date", ""))[:10]
        if fi_date != marker_date:
            continue
        fi_lat = fi.get("lat")
        fi_lon = fi.get("lon")
        if fi_lat is not None and fi_lon is not None:
            dist = _haversine_m(marker["lat"], marker["lon"], fi_lat, fi_lon)
            if dist <= max_dist_m:
                nearby.append(fi)
        else:
            # No GPS on the file, so match by date only
            nearby.append(fi)
    return nearby


def _media_popup_html(media_list: list[dict], output_dir: Path) -> str:
    # Thumbnails for a marker popup.
    if not media_list:
        return ""
    parts = ['<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px">']
    for fi in media_list[:6]:  # max 6 thumbnails
        dest = fi.get("dest", "")
        new_name = fi.get("new_name", "")
        ftype = fi.get("type", "")
        # Build relative path from map.html location (output_dir) to file
        try:
            rel = Path(dest).relative_to(output_dir).as_posix()
        except (ValueError, TypeError):
            rel = dest
        if ftype == "video":
            parts.append(
                f'<a href="{rel}" target="_blank" title="{new_name}" '
                f'style="display:block;width:48px;height:48px;background:#333;'
                f'border-radius:4px;text-align:center;line-height:48px;'
                f'font-size:20px;text-decoration:none">&#9654;</a>'
            )
        else:
            parts.append(
                f'<a href="{rel}" target="_blank" title="{new_name}">'
                f'<img src="{rel}" style="width:48px;height:48px;'
                f'object-fit:cover;border-radius:4px"></a>'
            )
    parts.append("</div>")
    return "".join(parts)


def generate_map_html(
    json_data: dict,
    output_dir: Path,
    file_index: list[dict] | None = None,
    dry_run: bool = False,
) -> bool:
    if dry_run:
        return True

    markers = _collect_markers(json_data)
    if not markers:
        console.print("[yellow]No GPS data found for map[/yellow]")
        return False

    # Attach media info to markers
    if file_index:
        for m in markers:
            nearby = _find_nearby_media(m, file_index)
            if nearby:
                m["media_html"] = _media_popup_html(nearby, output_dir)

    avg_lat = sum(m["lat"] for m in markers) / len(markers)
    avg_lon = sum(m["lon"] for m in markers) / len(markers)

    # Prepare markers JSON, including media_html where present
    markers_for_js = []
    for m in markers:
        entry = {
            "lat": m["lat"],
            "lon": m["lon"],
            "type": m["type"],
            "date": m["date"],
            "label": m["label"],
        }
        if "media_html" in m:
            entry["media"] = m["media_html"]
        markers_for_js.append(entry)

    markers_json = json.dumps(markers_for_js, ensure_ascii=False).replace("</", "<\\/")
    picker_css = date_format_css()
    picker_html = date_format_picker_html()
    picker_js = date_format_js()

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Snap Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossorigin="anonymous" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" integrity="sha384-pmjIAcz2bAn0xukfxADbZIb3t8oRT9Sv0rvO+BR5Csr6Dhqq+nZs59P0pPKQJkEV" crossorigin="anonymous" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" integrity="sha384-wgw+aLYNQ7dlhK47ZPK7FRACiq7ROZwgFNg0m04avm4CaXS+Z9Y7nMu8yNjBKYC+" crossorigin="anonymous" />
<link rel="stylesheet" href="https://unpkg.com/nouislider@15.7.1/dist/nouislider.min.css" integrity="sha384-PSZaVsyG9jDu8hFaSJev5s/9poIJlX7cuxSGdqCgXRHpo2DzIaZAyCd2rG/DJJmV" crossorigin="anonymous" />
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #111; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #e0e0e0; overflow: hidden; }}
#map {{ width: 100vw; height: calc(100vh - 110px); }}

/* Info badge */
.info-box {{
    position: absolute; top: 12px; right: 12px; z-index: 1000;
    background: rgba(17,17,17,0.85); color: #e0e0e0; padding: 8px 14px;
    border-radius: 8px; font-size: 13px; backdrop-filter: blur(6px);
    border: 1px solid rgba(255,255,255,0.1);
}}

/* Bottom control panel */
#controls {{
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 1000;
    height: 110px; background: rgba(17,17,17,0.92);
    backdrop-filter: blur(10px); border-top: 1px solid rgba(255,255,255,0.08);
    padding: 12px 24px 16px;
    display: flex; flex-direction: column; gap: 8px;
}}

/* Slider row */
.slider-row {{
    display: flex; align-items: center; gap: 14px;
}}
.slider-row label {{
    font-size: 12px; color: #999; white-space: nowrap; min-width: 130px;
    font-variant-numeric: tabular-nums;
}}
#date-slider {{ flex: 1; }}

/* noUiSlider dark theme overrides */
.noUi-target {{ background: #333; border: none; border-radius: 4px; height: 6px; }}
.noUi-connect {{ background: #FFFC00; }}
.noUi-handle {{ background: #FFFC00; border: 2px solid #111; border-radius: 50%; width: 18px !important; height: 18px !important; top: -7px !important; right: -9px !important; box-shadow: 0 1px 4px rgba(0,0,0,0.5); cursor: pointer; }}
.noUi-handle::before, .noUi-handle::after {{ display: none; }}
.noUi-tooltip {{ background: #222; color: #e0e0e0; border: 1px solid #444; font-size: 11px; border-radius: 4px; padding: 2px 6px; }}

/* Playback row */
.playback-row {{
    display: flex; align-items: center; gap: 10px;
}}
.playback-row button {{
    background: #222; color: #e0e0e0; border: 1px solid #444; border-radius: 6px;
    padding: 5px 14px; font-size: 12px; cursor: pointer; transition: all 0.15s;
}}
.playback-row button:hover {{ background: #333; border-color: #666; }}
.playback-row button.active {{ background: #FFFC00; color: #111; border-color: #FFFC00; font-weight: 600; }}
.playback-row .speed-group {{ display: flex; gap: 4px; }}
#playback-date {{ font-size: 13px; color: #FFFC00; margin-left: 12px; font-variant-numeric: tabular-nums; min-width: 160px; }}
#marker-count {{ font-size: 12px; color: #888; margin-left: auto; }}

/* Popups */
.leaflet-popup-content-wrapper {{ background: #1a1a1a; color: #e0e0e0; border-radius: 8px; border: 1px solid #333; }}
.leaflet-popup-tip {{ background: #1a1a1a; }}
.leaflet-popup-content {{ font-family: inherit; font-size: 13px; }}
.leaflet-popup-content b {{ color: #fff; }}

/* Dark map tiles */
.leaflet-tile {{ filter: brightness(0.85) contrast(1.1) saturate(0.8); }}
.leaflet-control-zoom a {{ background: #222 !important; color: #e0e0e0 !important; border-color: #444 !important; }}

/* Cluster dark */
.marker-cluster {{ background: rgba(255,252,0,0.25) !important; }}
.marker-cluster div {{ background: rgba(255,252,0,0.7) !important; color: #111 !important; font-weight: 600; }}
{picker_css}
.date-format-picker {{ margin-left: 12px; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="info-box" id="info-box">{len(markers)} Locations</div>

<div id="controls">
    <div class="slider-row">
        <label id="range-label">Loading...</label>
        <div id="date-slider"></div>
        <label id="range-label-end"></label>
    </div>
    <div class="playback-row">
        <button id="btn-play" title="Play / Pause">&#9654; Play</button>
        <div class="speed-group">
            <button class="speed-btn active" data-speed="1">1x</button>
            <button class="speed-btn" data-speed="2">2x</button>
            <button class="speed-btn" data-speed="5">5x</button>
            <button class="speed-btn" data-speed="10">10x</button>
        </div>
        <span id="playback-date"></span>
        {picker_html}
        <span id="marker-count"></span>
    </div>
</div>

<script>{picker_js}</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH" crossorigin="anonymous"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js" integrity="sha384-eXVCORTRlv4FUUgS/xmOyr66XBVraen8ATNLMESp92FKXLAMiKkerixTiBvXriZr" crossorigin="anonymous"></script>
<script src="https://unpkg.com/nouislider@15.7.1/dist/nouislider.min.js" integrity="sha384-/gBUOLHADjY2rp6bHB0IyW9AC28q4OsnirJScje4l1crgYW7Qarx3dH8zcqcUgmy" crossorigin="anonymous"></script>
<script>
(function() {{
    "use strict";

    // --- Data ---
    const allMarkers = {markers_json};
    const map = L.map('map').setView([{avg_lat}, {avg_lon}], 6);

    // Leaflet 1.9 puts a Ukrainian flag in the default prefix -- keep the
    // credits, drop the flag
    map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank">Leaflet</a>');

    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
    }}).addTo(map);

    // Parse dates to timestamps for sorting/filtering
    allMarkers.forEach(m => {{
        m._ts = new Date(m.date.replace(' UTC', 'Z').replace(' ', 'T')).getTime() || 0;
    }});
    allMarkers.sort((a, b) => a._ts - b._ts);

    const tsMin = allMarkers[0]._ts;
    const tsMax = allMarkers[allMarkers.length - 1]._ts;

    // --- Icons ---
    function makeIcon(type) {{
        const colors = {{ memory: '#FFFC00', location: '#4FC3F7', place: '#FF7043' }};
        const symbols = {{ memory: '&#128247;', location: '&#128205;', place: '&#128204;' }};
        const color = colors[type] || '#4FC3F7';
        const sym = symbols[type] || '&#128205;';
        return L.divIcon({{
            html: '<div style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;'
                + 'font-size:18px;background:' + color + '22;border:2px solid ' + color
                + ';border-radius:50%;backdrop-filter:blur(2px)">' + sym + '</div>',
            className: '',
            iconSize: [28, 28],
            iconAnchor: [14, 14],
        }});
    }}

    // --- Layer groups ---
    const cluster = L.markerClusterGroup({{ maxClusterRadius: 50, disableClusteringAtZoom: 15 }});
    const routeLine = L.polyline([], {{ color: '#FFFC00', weight: 2.5, opacity: 0.6, smoothFactor: 1 }}).addTo(map);
    let leafletMarkers = [];

    function isoDate(ts) {{
        const d = new Date(ts);
        const y = d.getFullYear();
        const mo = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return y + '-' + mo + '-' + day;
    }}

    // Route every date through the shared formatter so the picker applies here too
    function formatDate(ts) {{
        const iso = isoDate(ts);
        return window.SEODate ? window.SEODate.format(iso) : iso;
    }}

    function formatDateTime(ts) {{
        const d = new Date(ts);
        const h = String(d.getHours()).padStart(2, '0');
        const mi = String(d.getMinutes()).padStart(2, '0');
        return formatDate(ts) + ' ' + h + ':' + mi;
    }}

    // Marker dates arrive as "2026-07-20 14:32:05 UTC"
    function formatRawDate(raw) {{
        const m = /^(\\d{{4}}-\\d{{2}}-\\d{{2}})[ T]?(\\d{{2}}:\\d{{2}})?/.exec(raw || '');
        if (!m) return raw || '';
        const out = window.SEODate ? window.SEODate.format(m[1]) : m[1];
        return m[2] ? out + ' ' + m[2] : out;
    }}

    // --- Render markers for a time range ---
    function renderRange(lo, hi) {{
        cluster.clearLayers();
        leafletMarkers = [];
        const coords = [];

        let count = 0;
        allMarkers.forEach(m => {{
            if (m._ts < lo || m._ts > hi) return;
            count++;
            const lm = L.marker([m.lat, m.lon], {{ icon: makeIcon(m.type) }});
            let popup = '<b>' + m.label + '</b><br>'
                + '<span style="color:#999">' + formatRawDate(m.date) + '</span><br>'
                + '<small style="color:#666">' + m.lat.toFixed(5) + ', ' + m.lon.toFixed(5) + '</small>';
            if (m.media) popup += m.media;
            lm.bindPopup(popup, {{ maxWidth: 300 }});
            cluster.addLayer(lm);
            leafletMarkers.push(lm);
            coords.push([m.lat, m.lon]);
        }});

        routeLine.setLatLngs(coords);
        map.addLayer(cluster);

        document.getElementById('marker-count').textContent = count + ' / ' + allMarkers.length + ' visible';
    }}

    // --- noUiSlider ---
    const slider = document.getElementById('date-slider');
    noUiSlider.create(slider, {{
        start: [tsMin, tsMax],
        connect: true,
        range: {{ min: tsMin, max: tsMax || tsMin + 1 }},
        step: 86400000, // 1 day
        behaviour: 'drag',
        tooltips: [
            {{ to: v => formatDate(v) }},
            {{ to: v => formatDate(v) }},
        ],
    }});

    document.getElementById('range-label').textContent = formatDate(tsMin);
    document.getElementById('range-label-end').textContent = formatDate(tsMax);

    slider.noUiSlider.on('update', function(values) {{
        const lo = Number(values[0]);
        const hi = Number(values[1]);
        renderRange(lo, hi);
    }});

    // Initial render
    renderRange(tsMin, tsMax);

    // Re-render everything when the date format changes
    if (window.SEODate) {{
        window.SEODate.onChange(function () {{
            const vals = slider.noUiSlider.get();
            renderRange(Number(vals[0]), Number(vals[1]));
            document.getElementById('range-label').textContent = formatDate(tsMin);
            document.getElementById('range-label-end').textContent = formatDate(tsMax);
        }});
    }}

    // --- Playback / Animation ---
    let playing = false;
    let playIndex = 0;
    let playSpeed = 1;
    let playTimer = null;
    let movingMarker = null;

    const btnPlay = document.getElementById('btn-play');
    const playbackDate = document.getElementById('playback-date');

    function stopPlay() {{
        playing = false;
        btnPlay.innerHTML = '&#9654; Play';
        if (playTimer) {{ clearTimeout(playTimer); playTimer = null; }}
        if (movingMarker) {{ map.removeLayer(movingMarker); movingMarker = null; }}
        playbackDate.textContent = '';
    }}

    function startPlay() {{
        playing = true;
        playIndex = 0;
        btnPlay.innerHTML = '&#9724; Stop';

        // Get currently visible markers
        const sliderVals = slider.noUiSlider.get();
        const lo = Number(sliderVals[0]);
        const hi = Number(sliderVals[1]);
        const visible = allMarkers.filter(m => m._ts >= lo && m._ts <= hi);

        if (visible.length === 0) {{ stopPlay(); return; }}

        // Moving marker icon
        const moveIcon = L.divIcon({{
            html: '<div style="width:20px;height:20px;background:#FFFC00;border:3px solid #111;border-radius:50%;box-shadow:0 0 12px #FFFC00"></div>',
            className: '',
            iconSize: [20, 20],
            iconAnchor: [10, 10],
        }});

        movingMarker = L.marker([visible[0].lat, visible[0].lon], {{ icon: moveIcon, zIndexOffset: 10000 }}).addTo(map);

        function step() {{
            if (!playing || playIndex >= visible.length) {{
                stopPlay();
                return;
            }}
            const m = visible[playIndex];
            movingMarker.setLatLng([m.lat, m.lon]);
            playbackDate.textContent = formatDateTime(m._ts);
            map.panTo([m.lat, m.lon], {{ animate: true, duration: 0.3 }});
            playIndex++;

            // Delay: base 500ms, divided by speed
            const delay = Math.max(50, 500 / playSpeed);
            playTimer = setTimeout(step, delay);
        }}

        step();
    }}

    btnPlay.addEventListener('click', function() {{
        if (playing) stopPlay(); else startPlay();
    }});

    // Speed buttons
    document.querySelectorAll('.speed-btn').forEach(btn => {{
        btn.addEventListener('click', function() {{
            document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            playSpeed = Number(this.dataset.speed);
        }});
    }});

}})();
</script>
</body>
</html>'''

    (output_dir / "map.html").write_text(page, encoding="utf-8")
    console.print(f"[green]Map generated with {len(markers)} locations[/green]")
    return True
