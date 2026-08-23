# Markup, styles and script in one place, so gallery.html and the Media tab
# show the identical panel.


def details_overlay_html() -> str:
    return '<div id="detail-overlay"><div id="detail-panel"></div></div>'


DETAILS_CSS = """
.info-btn { background: none; border: 1px solid #555; color: #aaa; border-radius: 50%; width: 22px; height: 22px; font-size: 12px; line-height: 1; cursor: pointer; flex: 0 0 auto; font-family: inherit; }
.info-btn:hover { border-color: #FFFE00; color: #FFFE00; }
.damaged-badge { background: #c9a227; color: #1a1a1a; border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: 700; }
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
"""


DETAILS_JS = r"""
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
        if (d.len) body += row("Length", esc(d.len));
        if (d.px) body += row("Resolution", esc(d.px));
        if (d.cod) body += row("Encoding", esc(d.cod));
        if (d.br) body += row("Bitrate", esc(d.br));

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

        if (d.bad) body += row("Damaged", '<span class="detail-note">' + esc(d.bad) + " when it was merged in</span>");
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
            body += '<div class="detail-note">Paths are relative &mdash; open gallery.html directly from disk to get full paths.</div>';
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
