# Inline SVG from numbers and labels, knowing nothing about Snapchat. Colours
# live in CHART_CSS, so one place decides how a chart looks on screen and paper.

import html
import math

SERIES_COLORS = ["#FFFE00", "#00BFFF", "#FF6B6B", "#4ECDC4", "#BB8FCE"]

# The blue, red and green a spreadsheet would pick, for white paper.
PRINT_SERIES_COLORS = ["#2F5597", "#C00000", "#548235", "#BF8F00", "#7030A0"]
PRINT_BAR = "#2F5597"


def _series_rules() -> tuple[str, str]:
    # An attribute keeps a chart right with no stylesheet at all, the class beside
    # it lets print override the colour.
    screen = [f".chart-swatch.chart-s{index} {{ background: {color}; }}"
              for index, color in enumerate(SERIES_COLORS)]
    printed = []
    for index, color in enumerate(PRINT_SERIES_COLORS):
        printed.append(f"  .chart-line.chart-s{index} {{ stroke: {color}; }}")
        printed.append(f"  .chart-area.chart-s{index} {{ fill: {color}; }}")
        printed.append(f"  .chart-slice.chart-s{index} {{ fill: {color}; }}")
        printed.append(f"  .chart-swatch.chart-s{index} {{ background: {color}; }}")
    return "\n".join(screen), "\n".join(printed)


_SCREEN_SWATCHES, _PRINT_SERIES = _series_rules()

CHART_CSS = f"""
.chart {{ width: 100%; height: auto; display: block; }}
.chart-grid {{ stroke: #333; stroke-width: 1; }}
.chart-axis-text {{ fill: #888; font-size: 11px; font-family: inherit; }}
.chart-bar {{ fill: #FFFE00; }}
/* same yellow as the area under a line, so a bar chart reads as one family */
.chart-bar-muted {{ fill: #FFFE00; fill-opacity: 0.32; }}
.chart-line {{ fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }}
.chart-area {{ opacity: 0.14; }}
.chart-legend {{ display: flex; flex-wrap: wrap; gap: 14px; margin: 4px 0 8px; font-size: 12px; color: #aaa; }}
.chart-legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
.chart-swatch {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; }}
{_SCREEN_SWATCHES}
.chart-center-value {{ fill: #FFFE00; font-size: 22px; font-weight: 700; font-family: inherit; }}
.chart-empty {{ fill: #666; font-size: 12px; font-family: inherit; }}
@media print {{
  .chart {{ background: #fff; }}
  .chart-grid {{ stroke: #d0d0d0; }}
  .chart-axis-text {{ fill: #444; }}
  .chart-legend {{ color: #333; }}
  .chart-bar {{ fill: {PRINT_BAR}; }}
  .chart-bar-muted {{ fill: {PRINT_BAR}; fill-opacity: 0.4; }}
  .chart-area {{ opacity: 0.16; }}
  .chart-center-value {{ fill: #000; }}
  .chart-empty {{ fill: #666; }}
{_PRINT_SERIES}
}}
"""

_MARGIN_LEFT = 46
_MARGIN_RIGHT = 12
_MARGIN_TOP = 12
_MARGIN_BOTTOM = 28


def nice_ceiling(value: int) -> int:
    if value <= 5:
        return max(value, 1)
    step = 10 ** (len(str(value)) - 1)
    for factor in (1, 2, 2.5, 5, 10):
        candidate = int(step * factor)
        if candidate >= value:
            return candidate
    return value


def line_chart(series: list[tuple[str, list[int]]], tick_marks: list[tuple[int, str]],
               width: int = 720, height: int = 240) -> str:
    # series is [(name, values)] of equal length, tick_marks is [(index, label)].
    filled = [values for _, values in series if values]
    if not filled or len(filled[0]) < 2:
        return _empty_chart(width, height)

    count = len(filled[0])
    top = nice_ceiling(max(max(values) for values in filled))
    plot_width = width - _MARGIN_LEFT - _MARGIN_RIGHT
    plot_height = height - _MARGIN_TOP - _MARGIN_BOTTOM

    def x_at(index):
        return _MARGIN_LEFT + plot_width * index / (count - 1)

    def y_at(value):
        return _MARGIN_TOP + plot_height * (1 - value / top)

    parts = [_open_svg(width, height), _horizontal_grid(top, width, y_at)]

    for position, (name, values) in enumerate(series):
        if not values:
            continue
        color = SERIES_COLORS[position % len(SERIES_COLORS)]
        line = " ".join(f"{x_at(i):.1f},{y_at(v):.1f}" for i, v in enumerate(values))
        if len(series) == 1:
            baseline = y_at(0)
            parts.append(f'<polygon class="chart-area chart-s{position}" fill="{color}" points="'
                         f'{x_at(0):.1f},{baseline:.1f} {line} {x_at(count - 1):.1f},{baseline:.1f}"/>')
        parts.append(f'<polyline class="chart-line chart-s{position}" stroke="{color}" points="{line}">'
                     f'<title>{html.escape(name)}</title></polyline>')

    for index, label in tick_marks:
        if 0 <= index < count:
            parts.append(f'<text class="chart-axis-text" x="{x_at(index):.1f}" y="{height - 8}" '
                         f'text-anchor="middle">{html.escape(label)}</text>')

    parts.append("</svg>")
    legend = _legend([name for name, _ in series]) if len(series) > 1 else ""
    return legend + "".join(parts)


def bar_chart(labels: list[str], values: list[int], width: int = 720, height: int = 220) -> str:
    if not values or not any(values):
        return _empty_chart(width, height)

    top = nice_ceiling(max(values))
    plot_width = width - _MARGIN_LEFT - _MARGIN_RIGHT
    plot_height = height - _MARGIN_TOP - _MARGIN_BOTTOM
    slot = plot_width / len(values)
    bar_width = max(slot * 0.66, 2)
    peak = max(values)

    def y_at(value):
        return _MARGIN_TOP + plot_height * (1 - value / top)

    parts = [_open_svg(width, height), _horizontal_grid(top, width, y_at)]

    for index, value in enumerate(values):
        x = _MARGIN_LEFT + slot * index + (slot - bar_width) / 2
        y = y_at(value)
        css_class = "chart-bar" if value == peak else "chart-bar-muted"
        parts.append(f'<rect class="{css_class}" x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                     f'height="{_MARGIN_TOP + plot_height - y:.1f}" rx="2">'
                     f'<title>{html.escape(labels[index])}: {value}</title></rect>')
        parts.append(f'<text class="chart-axis-text" x="{x + bar_width / 2:.1f}" y="{height - 8}" '
                     f'text-anchor="middle">{html.escape(labels[index])}</text>')

    parts.append("</svg>")
    return "".join(parts)


def donut_chart(slices: list[tuple[str, int]], size: int = 240) -> str:
    total = sum(value for _, value in slices)
    if not total:
        return _empty_chart(size, size)

    radius = size / 2 - 10
    inner = radius * 0.62
    center = size / 2
    parts = [_open_svg(size, size)]
    start_fraction = 0.0
    named = []

    for position, (name, value) in enumerate(slices):
        if not value:
            continue
        end_fraction = start_fraction + value / total
        color = SERIES_COLORS[position % len(SERIES_COLORS)]
        parts.append(f'<path class="chart-slice chart-s{position}" '
                     f'd="{_ring_segment(center, radius, inner, start_fraction, end_fraction)}" '
                     f'fill="{color}"><title>{html.escape(name)}: {value}</title></path>')
        start_fraction = end_fraction
        named.append(name)

    parts.append(f'<text class="chart-center-value" x="{center}" y="{center + 8}" '
                 f'text-anchor="middle">{total}</text>')
    parts.append("</svg>")
    return "".join(parts) + _legend(named)


def _ring_segment(center: float, radius: float, inner: float,
                  start_fraction: float, end_fraction: float) -> str:
    # A full ring cannot be one arc, start and end point would coincide.
    end_fraction = min(end_fraction, start_fraction + 0.9999)
    start_angle = start_fraction * 2 * math.pi - math.pi / 2
    end_angle = end_fraction * 2 * math.pi - math.pi / 2
    large_arc = 1 if end_fraction - start_fraction > 0.5 else 0

    outer_start = _point_on_circle(center, radius, start_angle)
    outer_end = _point_on_circle(center, radius, end_angle)
    inner_end = _point_on_circle(center, inner, end_angle)
    inner_start = _point_on_circle(center, inner, start_angle)

    return (f"M{outer_start[0]:.2f},{outer_start[1]:.2f} "
            f"A{radius:.2f},{radius:.2f} 0 {large_arc} 1 {outer_end[0]:.2f},{outer_end[1]:.2f} "
            f"L{inner_end[0]:.2f},{inner_end[1]:.2f} "
            f"A{inner:.2f},{inner:.2f} 0 {large_arc} 0 {inner_start[0]:.2f},{inner_start[1]:.2f} Z")


def _point_on_circle(center: float, radius: float, angle: float) -> tuple[float, float]:
    return center + radius * math.cos(angle), center + radius * math.sin(angle)


def _open_svg(width: int, height: int) -> str:
    return (f'<svg class="chart" viewBox="0 0 {width} {height}" '
            f'preserveAspectRatio="xMidYMid meet" role="img">')


def _horizontal_grid(top: int, width: int, y_at) -> str:
    parts = []
    for value in sorted({0, top // 2, top}):
        y = y_at(value)
        parts.append(f'<line class="chart-grid" x1="{_MARGIN_LEFT}" y1="{y:.1f}" '
                     f'x2="{width - _MARGIN_RIGHT}" y2="{y:.1f}"/>')
        parts.append(f'<text class="chart-axis-text" x="{_MARGIN_LEFT - 8}" y="{y + 4:.1f}" '
                     f'text-anchor="end">{_short_number(value)}</text>')
    return "".join(parts)


def _short_number(value: int) -> str:
    if value < 1000:
        return str(value)
    thousands = value / 1000
    return f"{thousands:.0f}k" if value % 1000 == 0 else f"{thousands:.1f}k"


def _legend(names: list[str]) -> str:
    # A class rather than an inline style, so print swaps it with its line.
    entries = []
    for position, name in enumerate(names):
        index = position % len(SERIES_COLORS)
        entries.append(f'<span><i class="chart-swatch chart-s{index}"></i>'
                       f'{html.escape(name)}</span>')
    return f'<div class="chart-legend">{"".join(entries)}</div>'


def _empty_chart(width: int, height: int) -> str:
    return (f'{_open_svg(width, height)}<text class="chart-empty" x="{width / 2}" '
            f'y="{height / 2}" text-anchor="middle">Not enough data</text></svg>')
