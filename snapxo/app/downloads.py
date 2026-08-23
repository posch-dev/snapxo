# XLSX, ODS, CSV and PNG built in the browser, with no library and no network.

from ..parts.icons import icon


def buttons(key: str, has_chart: bool) -> str:
    chart_flag = ' data-export-chart="1"' if has_chart else ""
    return (f'<span class="card-actions no-print">'
            f'<button class="card-btn info" data-info="{key}" title="What this shows">'
            f'{icon("info", 14)}</button>'
            f'<button class="card-btn export" data-export="{key}"{chart_flag} title="Export">'
            f'{icon("download", 14)}</button></span>')


def export_all_button() -> str:
    return (f'<button class="export-all no-print" data-export-all="1">'
            f'{icon("download", 16)} Export all stats</button>')


def dialogs() -> str:
    return '''<div class="sx-modal no-print" id="sx-info"><div class="sx-box">
<h4 id="sx-info-title"></h4><div id="sx-info-text"></div>
<div class="sx-actions sx-cancel"><button data-close="1">Close</button></div></div></div>
<div class="sx-modal no-print" id="sx-pick"><div class="sx-box">
<h4 id="sx-pick-title">Export</h4><p id="sx-pick-text"></p>
<div class="sx-actions" id="sx-pick-actions"></div>
<p class="sx-note" id="sx-pick-note"></p>
<div class="sx-actions sx-cancel"><button data-close="1">Cancel</button></div></div></div>'''


EXPORT_CSS = """
.card-actions { display: inline-flex; gap: 6px; margin-left: auto; }
.card-btn { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 6px; cursor: pointer; font-family: inherit; background: #2c2c2c; border: 1px solid #3f3f3f; color: #aaa; }
.card-btn:hover { color: #fff; border-color: #666; }
.card-btn.export { color: #7ad3ff; border-color: #2f5c73; background: #17303c; }
.card-btn.export:hover { background: #1d3d4c; border-color: #7ad3ff; }
.export-all { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; margin: 8px 0 28px; padding: 16px; border-radius: 12px; border: 1px solid #2f5c73; background: #17303c; color: #7ad3ff; font-family: inherit; font-size: 15px; font-weight: 600; cursor: pointer; }
.export-all:hover { background: #1d3d4c; border-color: #7ad3ff; }
.sx-modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 2500; align-items: center; justify-content: center; padding: 20px; }
.sx-modal.visible { display: flex; }
.sx-box { background: #242424; border: 1px solid #3a3a3a; border-radius: 12px; padding: 20px; max-width: 460px; width: 100%; }
.sx-box h4 { color: #FFFE00; font-size: 15px; margin-bottom: 10px; }
.sx-box p { color: #ccc; font-size: 13.5px; line-height: 1.6; margin-bottom: 12px; }
.sx-box p:last-of-type { margin-bottom: 0; }
.sx-box { max-height: 84vh; overflow-y: auto; }
.sx-actions { display: flex; flex-direction: column; gap: 10px; margin-top: 18px; }
.sx-actions button { width: 100%; background: #303030; border: 1px solid #4a4a4a; border-radius: 10px; color: #e0e0e0; font-family: inherit; font-size: 14px; padding: 13px 16px; cursor: pointer; text-align: left; }
.sx-actions button:hover { border-color: #FFFE00; color: #FFFE00; background: #383838; }
.sx-actions .sx-hint { display: block; color: #888; font-size: 11.5px; margin-top: 3px; }
.sx-actions button:hover .sx-hint { color: #b3a800; }
.sx-cancel button { background: none; border-color: #3a3a3a; color: #999; text-align: center; padding: 10px; }
.sx-note { color: #888; font-size: 12px; margin-top: 14px; line-height: 1.5; }
"""


def export_script(chart_css: str) -> str:
    return _EXPORT_JS.replace("__CHART_CSS__", chart_css.replace("\\", "\\\\").replace('"', '\\"')
                              .replace("\n", " "))


_EXPORT_JS = r"""
(function () {
    "use strict";
    var DATA = (window.SNAPXO_STATS || { datasets: [] }).datasets;
    var CHART_CSS = "__CHART_CSS__";
    var byKey = {};
    DATA.forEach(function (set) { byKey[set.key] = set; });

    var infoModal = document.getElementById("sx-info");
    var pickModal = document.getElementById("sx-pick");
    if (!infoModal || !pickModal) return;

    function stamp() {
        return new Date().toISOString().slice(0, 10);
    }

    function slug(text) {
        return String(text).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "stats";
    }

    function fileName(base, extension) {
        return "snapxo-" + slug(base) + "-" + stamp() + "." + extension;
    }

    function download(blob, name) {
        var url = URL.createObjectURL(blob);
        var link = document.createElement("a");
        link.href = url;
        link.download = name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
    }

    function esc(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function isNumber(value) {
        return typeof value === "number" && isFinite(value);
    }

    // --- CSV -------------------------------------------------------------
    function toCsv(set) {
        var lines = [set.columns].concat(set.rows).map(function (row) {
            return row.map(function (cell) {
                var text = String(cell == null ? "" : cell);
                return /[",\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
            }).join(",");
        });
        return "﻿" + lines.join("\r\n");
    }

    // --- ZIP, stored entries only, which every unpacker accepts -----------
    var CRC_TABLE = (function () {
        var table = new Uint32Array(256);
        for (var i = 0; i < 256; i++) {
            var value = i;
            for (var bit = 0; bit < 8; bit++) {
                value = value & 1 ? (value >>> 1) ^ 0xEDB88320 : value >>> 1;
            }
            table[i] = value >>> 0;
        }
        return table;
    })();

    function crc32(bytes) {
        var crc = 0xFFFFFFFF;
        for (var i = 0; i < bytes.length; i++) {
            crc = (crc >>> 8) ^ CRC_TABLE[(crc ^ bytes[i]) & 0xFF];
        }
        return (crc ^ 0xFFFFFFFF) >>> 0;
    }

    function bytesOf(value) {
        return typeof value === "string" ? new TextEncoder().encode(value) : value;
    }

    function zip(entries) {
        var parts = [];
        var central = [];
        var offset = 0;

        entries.forEach(function (entry) {
            var name = new TextEncoder().encode(entry.name);
            var body = bytesOf(entry.data);
            var sum = crc32(body);

            var local = new DataView(new ArrayBuffer(30));
            local.setUint32(0, 0x04034b50, true);
            local.setUint16(4, 20, true);
            local.setUint16(8, 0, true);
            local.setUint32(14, sum, true);
            local.setUint32(18, body.length, true);
            local.setUint32(22, body.length, true);
            local.setUint16(26, name.length, true);
            parts.push(new Uint8Array(local.buffer), name, body);

            var record = new DataView(new ArrayBuffer(46));
            record.setUint32(0, 0x02014b50, true);
            record.setUint16(4, 20, true);
            record.setUint16(6, 20, true);
            record.setUint16(10, 0, true);
            record.setUint32(16, sum, true);
            record.setUint32(20, body.length, true);
            record.setUint32(24, body.length, true);
            record.setUint16(28, name.length, true);
            record.setUint32(42, offset, true);
            central.push(new Uint8Array(record.buffer), name);

            offset += 30 + name.length + body.length;
        });

        var centralSize = central.reduce(function (total, part) { return total + part.length; }, 0);
        var end = new DataView(new ArrayBuffer(22));
        end.setUint32(0, 0x06054b50, true);
        end.setUint16(8, entries.length, true);
        end.setUint16(10, entries.length, true);
        end.setUint32(12, centralSize, true);
        end.setUint32(16, offset, true);

        return new Blob(parts.concat(central, [new Uint8Array(end.buffer)]),
                        { type: "application/zip" });
    }

    // --- XLSX ------------------------------------------------------------
    function sheetXml(set) {
        var rows = [set.columns].concat(set.rows).map(function (row, rowIndex) {
            var cells = row.map(function (cell, columnIndex) {
                var reference = String.fromCharCode(65 + columnIndex) + (rowIndex + 1);
                if (isNumber(cell)) {
                    return '<c r="' + reference + '"><v>' + cell + "</v></c>";
                }
                return '<c r="' + reference + '" t="inlineStr"><is><t xml:space="preserve">' +
                       esc(cell) + "</t></is></c>";
            }).join("");
            return '<row r="' + (rowIndex + 1) + '">' + cells + "</row>";
        }).join("");
        return '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns=' +
               '"http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' +
               rows + "</sheetData></worksheet>";
    }

    function sheetTitle(title) {
        return String(title).replace(/[\[\]:*?\/\\]/g, "").slice(0, 31) || "Sheet";
    }

    function toXlsx(sets) {
        var entries = [];
        var sheets = "";
        var rels = "";
        var overrides = "";

        sets.forEach(function (set, index) {
            var number = index + 1;
            entries.push({ name: "xl/worksheets/sheet" + number + ".xml", data: sheetXml(set) });
            sheets += '<sheet name="' + esc(sheetTitle(set.title)) + '" sheetId="' + number +
                      '" r:id="rId' + number + '"/>';
            rels += '<Relationship Id="rId' + number + '" Type="http://schemas.openxmlformats.org' +
                    '/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet' +
                    number + '.xml"/>';
            overrides += '<Override PartName="/xl/worksheets/sheet' + number + '.xml" ContentType=' +
                         '"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>';
        });

        entries.push({ name: "[Content_Types].xml", data:
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org' +
            '/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd' +
            '.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType=' +
            '"application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd' +
            '.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' + overrides + "</Types>" });
        entries.push({ name: "_rels/.rels", data:
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats' +
            '.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas' +
            '.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target=' +
            '"xl/workbook.xml"/></Relationships>' });
        entries.push({ name: "xl/workbook.xml", data:
            '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats' +
            '.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument' +
            '/2006/relationships"><sheets>' + sheets + "</sheets></workbook>" });
        entries.push({ name: "xl/_rels/workbook.xml.rels", data:
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas' +
            '.openxmlformats.org/package/2006/relationships">' + rels + "</Relationships>" });

        return zip(entries);
    }

    // --- ODS -------------------------------------------------------------
    function odsCell(cell) {
        if (isNumber(cell)) {
            return '<table:table-cell office:value-type="float" office:value="' + cell + '">' +
                   "<text:p>" + cell + "</text:p></table:table-cell>";
        }
        return '<table:table-cell office:value-type="string"><text:p>' + esc(cell) +
               "</text:p></table:table-cell>";
    }

    function toOds(sets) {
        var tables = sets.map(function (set) {
            var rows = [set.columns].concat(set.rows).map(function (row) {
                return "<table:table-row>" + row.map(odsCell).join("") + "</table:table-row>";
            }).join("");
            return '<table:table table:name="' + esc(sheetTitle(set.title)) + '">' +
                   '<table:table-column table:number-columns-repeated="' + set.columns.length +
                   '"/>' + rows + "</table:table>";
        }).join("");

        var content = '<?xml version="1.0" encoding="UTF-8"?><office:document-content xmlns:office=' +
            '"urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:table=' +
            '"urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:text=' +
            '"urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.3">' +
            "<office:body><office:spreadsheet>" + tables +
            "</office:spreadsheet></office:body></office:document-content>";

        var manifest = '<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest=' +
            '"urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">' +
            '<manifest:file-entry manifest:full-path="/" manifest:media-type=' +
            '"application/vnd.oasis.opendocument.spreadsheet"/><manifest:file-entry ' +
            'manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>';

        // The mimetype has to come first in the archive.
        return zip([
            { name: "mimetype", data: "application/vnd.oasis.opendocument.spreadsheet" },
            { name: "META-INF/manifest.xml", data: manifest },
            { name: "content.xml", data: content },
        ]);
    }

    // --- the chart itself, as a picture -----------------------------------
    function chartSvgOf(key) {
        var card = document.querySelector('[data-export="' + key + '"]');
        var section = card ? card.closest(".chart-card") : null;
        return section ? section.querySelector("svg.chart") : null;
    }

    function exportPng(set) {
        var svg = chartSvgOf(set.key);
        if (!svg) return;

        var clone = svg.cloneNode(true);
        // The stylesheet does not travel with a serialised SVG, so it moves inside.
        var style = document.createElementNS("http://www.w3.org/2000/svg", "style");
        style.textContent = CHART_CSS + " svg { background: #1a1a1a; }";
        clone.insertBefore(style, clone.firstChild);
        clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");

        var box = (svg.getAttribute("viewBox") || "0 0 720 240").split(/\s+/);
        var width = parseFloat(box[2]) || 720;
        var height = parseFloat(box[3]) || 240;
        var scale = 2;

        var source = new XMLSerializer().serializeToString(clone);
        var image = new Image();
        image.onload = function () {
            var canvas = document.createElement("canvas");
            canvas.width = width * scale;
            canvas.height = height * scale;
            var context = canvas.getContext("2d");
            context.fillStyle = "#1a1a1a";
            context.fillRect(0, 0, canvas.width, canvas.height);
            context.drawImage(image, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(function (blob) {
                if (blob) download(blob, fileName(set.title, "png"));
            }, "image/png");
        };
        image.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(source);
    }

    // --- dialogs ----------------------------------------------------------
    function show(modal) { modal.classList.add("visible"); }
    function hide(modal) { modal.classList.remove("visible"); }

    function askFormat(title, sets, base) {
        document.getElementById("sx-pick-title").textContent = "Export " + title;
        document.getElementById("sx-pick-text").textContent = "Pick a file type.";
        document.getElementById("sx-pick-note").textContent =
            "These files hold the numbers. To get charts inside the spreadsheet, run " +
            "snapxo spreadsheet from the command line.";
        var actions = document.getElementById("sx-pick-actions");
        actions.innerHTML =
            '<button data-format="xlsx">Excel workbook (.xlsx)' +
            '<span class="sx-hint">Opens in Excel, LibreOffice, Numbers and Google Sheets</span></button>' +
            '<button data-format="ods">OpenDocument (.ods)' +
            '<span class="sx-hint">The open format, opens in the same places</span></button>' +
            '<button data-format="csv">Plain text (.csv)' +
            '<span class="sx-hint">One simple table per file, opens anywhere</span></button>';
        actions.onclick = function (event) {
            var button = event.target.closest("[data-format]");
            if (!button) return;
            writeSets(button.getAttribute("data-format"), sets, base);
            hide(pickModal);
        };
        show(pickModal);
    }

    function writeSets(format, sets, base) {
        if (format === "csv") {
            if (sets.length === 1) {
                download(new Blob([toCsv(sets[0])], { type: "text/csv" }),
                         fileName(sets[0].title, "csv"));
                return;
            }
            download(zip(sets.map(function (set) {
                return { name: fileName(set.title, "csv"), data: toCsv(set) };
            })), fileName(base, "zip"));
            return;
        }
        if (format === "ods") {
            download(toOds(sets), fileName(base, "ods"));
            return;
        }
        download(toXlsx(sets), fileName(base, "xlsx"));
    }

    function askChartOrData(set) {
        document.getElementById("sx-pick-title").textContent = "Export " + set.title;
        document.getElementById("sx-pick-text").textContent = "What would you like?";
        document.getElementById("sx-pick-note").textContent = "";
        var actions = document.getElementById("sx-pick-actions");
        actions.innerHTML =
            '<button data-choice="chart">The chart as a picture' +
            '<span class="sx-hint">A PNG you can drop into a document or a chat</span></button>' +
            '<button data-choice="data">The numbers behind it' +
            '<span class="sx-hint">A spreadsheet you can sort, filter and chart yourself</span></button>';
        actions.onclick = function (event) {
            var button = event.target.closest("[data-choice]");
            if (!button) return;
            hide(pickModal);
            if (button.getAttribute("data-choice") === "chart") exportPng(set);
            else askFormat(set.title, [set], set.title);
        };
        show(pickModal);
    }

    document.addEventListener("click", function (event) {
        if (!event.target.closest) return;

        if (event.target.closest("[data-close]") || event.target.classList.contains("sx-modal")) {
            hide(infoModal);
            hide(pickModal);
            return;
        }

        var infoButton = event.target.closest("[data-info]");
        if (infoButton) {
            var infoSet = byKey[infoButton.getAttribute("data-info")];
            if (!infoSet) return;
            document.getElementById("sx-info-title").textContent = infoSet.title;
            var paragraphs = [].concat(infoSet.info || []);
            document.getElementById("sx-info-text").innerHTML = paragraphs.map(
                function (line) { return "<p>" + esc(line) + "</p>"; }).join("");
            show(infoModal);
            return;
        }

        var exportButton = event.target.closest("[data-export]");
        if (exportButton) {
            var set = byKey[exportButton.getAttribute("data-export")];
            if (!set) return;
            if (exportButton.hasAttribute("data-export-chart")) askChartOrData(set);
            else askFormat(set.title, [set], set.title);
            return;
        }

        if (event.target.closest("[data-export-all]")) {
            askFormat("all statistics", DATA, "stats");
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") { hide(infoModal); hide(pickModal); }
    });
})();
"""
