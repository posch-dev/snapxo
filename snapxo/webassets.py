# Snippets shared by every generated page. The pages open straight from disk, so
# no fetch, no modules, no external assets. Dates go into the markup as ISO with a
# data-date attribute and are rewritten by script, which means they still read
# correctly when the script never runs, as inside a PDF renderer.

DATE_FORMATS = [
    ("iso", "2026-07-20"),
    ("dmy", "20.07.2026"),
    ("mdy", "07/20/2026"),
    ("dmonthy", "20 July 2026"),
    ("monthdy", "July 20, 2026"),
]

DEFAULT_DATE_FORMAT = "iso"


def date_format_css() -> str:
    return """
.date-format-picker { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #888; }
.date-format-picker select {
    background: #2a2a2a; color: #e0e0e0; border: 1px solid #555; border-radius: 6px;
    padding: 5px 8px; font-size: 12px; font-family: inherit; cursor: pointer;
}
.date-format-picker select:hover { border-color: #888; }
@media print { .date-format-picker { display: none; } }
"""


def date_format_picker_html(label: str = "Date format") -> str:
    options = "".join(
        f'<option value="{key}">{example}</option>' for key, example in DATE_FORMATS
    )
    return (
        '<span class="date-format-picker no-print">'
        f"<label for=\"date-format-select\">{label}</label>"
        f'<select id="date-format-select">{options}</select>'
        "</span>"
    )


def date_format_js() -> str:
    # Runtime date formatting, exposed as window.SEODate for other scripts.
    return """
(function () {
    "use strict";
    var KEY = "snapxo.dateFormat";
    var MONTHS = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"];
    var fallback = null;  // used when localStorage is unavailable (some file:// setups)

    function read() {
        try {
            return window.localStorage.getItem(KEY) || fallback || "iso";
        } catch (e) {
            return fallback || "iso";
        }
    }

    function store(value) {
        fallback = value;
        try { window.localStorage.setItem(KEY, value); } catch (e) { /* session only */ }
    }

    // iso is "YYYY-MM-DD"; anything unparseable is returned untouched.
    function format(iso, fmt) {
        if (!iso) return "";
        var m = /^(\\d{4})-(\\d{2})-(\\d{2})/.exec(iso);
        if (!m) return iso;
        var y = m[1], mo = m[2], d = m[3];
        var monthName = MONTHS[parseInt(mo, 10) - 1] || mo;
        switch (fmt || read()) {
            case "dmy": return d + "." + mo + "." + y;
            case "mdy": return mo + "/" + d + "/" + y;
            case "dmonthy": return parseInt(d, 10) + " " + monthName + " " + y;
            case "monthdy": return monthName + " " + parseInt(d, 10) + ", " + y;
            default: return y + "-" + mo + "-" + d;
        }
    }

    var listeners = [];

    function applyAll(root) {
        var fmt = read();
        var nodes = (root || document).querySelectorAll("[data-date]");
        for (var i = 0; i < nodes.length; i++) {
            var el = nodes[i];
            var text = format(el.getAttribute("data-date"), fmt);
            var time = el.getAttribute("data-time");
            if (time) text += " " + time;
            var suffix = el.getAttribute("data-suffix");
            if (suffix) text += " " + suffix;
            el.textContent = text;
        }
    }

    function setFormat(value) {
        store(value);
        applyAll();
        for (var i = 0; i < listeners.length; i++) {
            try { listeners[i](value); } catch (e) { /* keep the others running */ }
        }
    }

    window.SEODate = {
        format: format,
        current: read,
        set: setFormat,
        apply: applyAll,
        onChange: function (cb) { listeners.push(cb); }
    };

    function init() {
        var select = document.getElementById("date-format-select");
        if (select) {
            select.value = read();
            select.addEventListener("change", function () { setFormat(this.value); });
        }
        applyAll();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
"""


def date_span(iso_date: str, time: str = "", extra_class: str = "", suffix: str = "") -> str:
    # A date the format picker can rewrite. Renders ISO if the script never runs.
    if not iso_date:
        return ""
    cls = f' class="{extra_class}"' if extra_class else ""
    time_attr = f' data-time="{time}"' if time else ""
    suffix_attr = f' data-suffix="{suffix}"' if suffix else ""
    text = iso_date
    if time:
        text += f" {time}"
    if suffix:
        text += f" {suffix}"
    return f'<span{cls} data-date="{iso_date}"{time_attr}{suffix_attr}>{text}</span>'


def split_timestamp(value: str) -> tuple[str, str]:
    # Split "2026-07-20 14:32:05 UTC" into ("2026-07-20", "14:32"). Returns ("", "")
    # for anything that is not ISO-ish, so callers can print the raw value instead.
    if not value or len(value) < 10:
        return "", ""
    date_part = value[:10]
    if len(date_part) != 10 or date_part[4] != "-" or date_part[7] != "-":
        return "", ""
    if not (date_part[:4].isdigit() and date_part[5:7].isdigit() and date_part[8:10].isdigit()):
        return "", ""
    time_part = value[11:16] if len(value) >= 16 else ""
    if time_part and (len(time_part) != 5 or time_part[2] != ":"):
        time_part = ""
    return date_part, time_part
