# The Media tab. Tiles append while scrolling rather than all at once, so tens
# of thousands of files still open instantly. Filled from _meta/app-media.js.

import html

BATCH_SIZE = 120

MEDIA_CSS = """
.media-toolbar { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 10px 24px; margin-bottom: 16px; }
.media-filter-group { display: flex; align-items: center; gap: 10px; min-width: 0; }
.media-filter-group:last-child { margin-left: auto; }
.media-filter-label { color: #777; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; white-space: nowrap; }
.media-filters { display: flex; flex-wrap: wrap; gap: 6px; }
.media-filters button { background: #333; color: #e0e0e0; border: 1px solid #555; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-family: inherit; }
.media-filters button:hover { background: #444; }
.media-filters button.active { background: #FFFE00; color: #1a1a1a; border-color: #FFFE00; font-weight: 600; }
.media-years { background: #2a2a2a; color: #e0e0e0; border: 1px solid #555; border-radius: 6px; padding: 6px 10px; font-size: 13px; font-family: inherit; cursor: pointer; min-width: 130px; }
.media-years:hover { border-color: #FFFE00; }
.media-years:focus { outline: none; border-color: #FFFE00; }
.media-count { color: #888; font-size: 13px; margin-bottom: 12px; }
.media-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.media-item { background: #222; border-radius: 10px; overflow: hidden; position: relative; }
/* the tile is a link, and a link underline in the accent colour is a yellow bar */
.media-item a { text-decoration: none; display: block; }
.media-item .thumb { width: 100%; height: 150px; object-fit: cover; display: block; background: #2a2a2a; }
.media-item .placeholder { display: flex; align-items: center; justify-content: center; height: 150px; background: #333; font-size: 40px; color: #666; }
.media-info { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 7px 10px; font-size: 12px; }
.media-info .date { color: #ddd; font-weight: 600; }
.media-year-head { grid-column: 1 / -1; display: flex; align-items: center; gap: 8px; color: #FFFE00; font-size: 20px; font-weight: 700; padding: 26px 0 4px; border-top: 1px solid #3a3a3a; cursor: pointer; user-select: none; }
.media-year-head:first-child { padding-top: 4px; border-top: none; }
.media-month-head { grid-column: 1 / -1; display: flex; align-items: center; gap: 8px; color: #bbb; font-size: 13px; font-weight: 600; letter-spacing: 0.04em; padding: 12px 0 2px; cursor: pointer; user-select: none; }
.fold-mark { flex: 0 0 auto; color: #777; transition: transform 0.12s ease; }
.folded-head .fold-mark { transform: rotate(-90deg); }
.media-year-head:hover, .media-month-head:hover { color: #fff; }
.media-year-head:hover .fold-mark, .media-month-head:hover .fold-mark { color: #fff; }
.media-grid .hidden { display: none; }
.type-badge { position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.7); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
#media-sentinel { height: 1px; }
@media (max-width: 760px) {
  /* Each filter row gets its own line with the label above it, instead of
     four groups fighting over one row. */
  .media-toolbar { flex-direction: column; align-items: stretch; gap: 12px; }
  .media-filter-group { flex-direction: column; align-items: flex-start; gap: 6px; }
  .media-filter-group:last-child { margin-left: 0; }
  .media-filters button { flex: 1 1 auto; }
  .media-filters { width: 100%; }
  .media-grid { grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 8px; }
}
"""


def media_panel() -> str:
    filters = "".join(
        f'<button class="{"active" if key == "all" else ""}" data-media-filter="{key}">'
        f"{html.escape(label)}</button>"
        for key, label in [("all", "All"), ("image", "Images"),
                           ("video", "Videos"), ("audio", "Voice")]
    )
    return f'''<section class="tab-panel" id="tab-media">
<div class="media-toolbar">
<div class="media-filter-group">
<span class="media-filter-label">Media type:</span>
<div class="media-filters">{filters}</div>
</div>
<div class="media-filter-group">
<span class="media-filter-label">Year:</span>
<select class="media-years" id="media-years"><option value="">All years</option></select>
</div>
</div>
<div class="media-count" id="media-count"></div>
<div class="media-grid" id="media-grid"></div>
<div id="media-sentinel"></div>
</section>'''


MEDIA_JS = r"""
(function () {
    "use strict";
    var DATA = window.SNAPXO_MEDIA || { items: [], details: {} };
    var BATCH = __BATCH__;

    var grid = document.getElementById("media-grid");
    var years = document.getElementById("media-years");
    var count = document.getElementById("media-count");
    var sentinel = document.getElementById("media-sentinel");
    if (!grid) return;

    var MONTHS = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"];

    var typeFilter = "all";
    var yearFilter = "";
    var shown = 0;
    var visible = DATA.items;
    var lastMonth = null;
    var lastYear = null;
    var foldedYears = {};
    var foldedMonths = {};

    function esc(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function preview(item) {
        if (item.t) return '<img class="thumb" src="' + esc(item.t) + '" loading="lazy" alt="">';
        if (item.k === "audio") return '<div class="placeholder">&#9835;</div>';
        if (item.k === "video") return '<video class="thumb" src="' + esc(item.f) + '" preload="metadata"></video>';
        return '<div class="placeholder">&#128247;</div>';
    }

    function tile(item) {
        var badge = "";
        if (item.k === "video") badge = '<span class="type-badge">&#9654; Video</span>';
        else if (item.k === "audio") badge = '<span class="type-badge">&#9835; Audio</span>';
        var flag = item.b ? '<span class="damaged-badge">damaged</span>' : "";
        var month = String(item.d || "").slice(0, 7);
        return '<div class="media-item" data-year="' + esc(month.slice(0, 4)) +
            '" data-month="' + esc(month) + '">' +
            '<a href="' + esc(item.f) + '" target="_blank" rel="noopener">' +
            badge + preview(item) + "</a>" +
            '<div class="media-info"><span class="date" data-date="' + esc(item.d) + '">' +
            esc(item.d) + "</span>" + flag +
            '<button class="info-btn" data-id="' + esc(item.i) + '" title="Details">&#8505;</button>' +
            "</div></div>";
    }

    var FOLD_MARK = '<svg class="fold-mark" viewBox="0 0 24 24" width="14" height="14" ' +
        'fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" ' +
        'stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';

    function monthLabel(day) {
        // "2026-07-20" -> "July 2026", independent of the folder structure.
        var index = parseInt(day.slice(5, 7), 10) - 1;
        return (MONTHS[index] || day.slice(5, 7)) + " " + day.slice(0, 4);
    }

    function headings(item, month) {
        var year = month.slice(0, 4);
        var markup = "";
        if (year !== lastYear) {
            lastYear = year;
            markup += '<h3 class="media-year-head" data-fold-year="' + esc(year) + '" id="media-year-' +
                      esc(year) + '">' + esc(year || "Undated") + FOLD_MARK + "</h3>";
        }
        markup += '<h4 class="media-month-head" data-fold-month="' + esc(month) + '" data-year="' +
                  esc(year) + '">' + esc(month ? monthLabel(item.d) : "No date") + FOLD_MARK + "</h4>";
        return markup;
    }

    function appendBatch() {
        if (shown >= visible.length) return;
        var markup = "";
        var end = Math.min(shown + BATCH, visible.length);
        for (var i = shown; i < end; i++) {
            var item = visible[i];
            var month = String(item.d || "").slice(0, 7);
            if (month !== lastMonth) {
                lastMonth = month;
                markup += headings(item, month);
            }
            markup += tile(item);
        }
        grid.insertAdjacentHTML("beforeend", markup);
        shown = end;
        if (window.SEODate) window.SEODate.apply(grid);
        applyFolding();
    }

    // A month hides its own tiles. A year hides everything inside it, months
    // included, which is why both are checked for every element.
    function applyFolding() {
        Array.prototype.forEach.call(grid.children, function (node) {
            if (node.hasAttribute("data-fold-year")) {
                node.classList.toggle("folded-head", foldedYears[node.getAttribute("data-fold-year")] === true);
                return;
            }
            var year = node.getAttribute("data-year") || "";
            var month = node.getAttribute("data-month") || node.getAttribute("data-fold-month") || "";
            var hidden = foldedYears[year] === true ||
                         (foldedMonths[month] === true && !node.hasAttribute("data-fold-month"));
            node.classList.toggle("hidden", hidden);
            if (node.hasAttribute("data-fold-month")) {
                node.classList.toggle("folded-head", foldedMonths[month] === true);
            }
        });
    }

    function reset() {
        visible = DATA.items.filter(function (item) {
            if (typeFilter !== "all" && item.k !== typeFilter) return false;
            return !yearFilter || item.y === yearFilter;
        });
        grid.innerHTML = "";
        shown = 0;
        lastMonth = null;
        lastYear = null;
        count.textContent = visible.length + (visible.length === 1 ? " file" : " files");
        appendBatch();
    }

    function renderYears() {
        var seen = [];
        DATA.items.forEach(function (item) {
            if (item.y && seen.indexOf(item.y) < 0) seen.push(item.y);
        });
        seen.sort().reverse();
        years.innerHTML = '<option value="">All years</option>' + seen.map(function (year) {
            return '<option value="' + esc(year) + '">' + esc(year) + "</option>";
        }).join("");
    }

    document.addEventListener("click", function (event) {
        if (!event.target.closest) return;

        var filterButton = event.target.closest("[data-media-filter]");
        if (filterButton) {
            typeFilter = filterButton.getAttribute("data-media-filter");
            Array.prototype.forEach.call(document.querySelectorAll("[data-media-filter]"), function (other) {
                other.classList.toggle("active", other === filterButton);
            });
            reset();
            return;
        }

        var yearHead = event.target.closest("[data-fold-year]");
        if (yearHead && grid.contains(yearHead)) {
            var year = yearHead.getAttribute("data-fold-year");
            foldedYears[year] = !foldedYears[year];
            applyFolding();
            return;
        }

        var monthHead = event.target.closest("[data-fold-month]");
        if (monthHead && grid.contains(monthHead)) {
            var month = monthHead.getAttribute("data-fold-month");
            foldedMonths[month] = !foldedMonths[month];
            applyFolding();
        }
    });

    years.addEventListener("change", function () {
        yearFilter = years.value;
        reset();
    });

    if (window.IntersectionObserver) {
        new IntersectionObserver(function (entries) {
            if (entries[0].isIntersecting) appendBatch();
        }, { rootMargin: "600px" }).observe(sentinel);
    } else {
        window.addEventListener("scroll", function () {
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 600) appendBatch();
        });
    }

    renderYears();
    reset();
})();
"""


def media_script() -> str:
    return MEDIA_JS.replace("__BATCH__", str(BATCH_SIZE))
