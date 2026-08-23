# Only the frame, _meta/app-chats.js fills the chat list and the messages in.

from ..parts.icons import icon


def chats_panel(cover: str = "") -> str:
    return f'''<section class="tab-panel" id="tab-chats">
<div class="chat-search"><input id="chat-query" type="search"
 placeholder="Search names and messages" autocomplete="off"></div>
<div class="chat-layout">
<aside class="chat-list-pane">
<section class="result-block" id="chat-name-block">
<div class="pane-label" id="chat-list-label">Chats</div>
<div id="chat-list"></div>
</section>
<section class="result-block" id="chat-hit-block" hidden>
<div class="pane-label" id="chat-hit-label">Messages</div>
<div id="chat-hits"></div>
</section>
</aside>
<div class="chat-view-pane">
<div id="chat-cover">{cover}</div>
<div class="chat-view-head" id="chat-head" hidden>
<span class="avatar-slot" id="chat-head-avatar"></span>
<span class="chat-head-main">
<span class="chat-head-name" id="chat-head-name"></span>
<span class="chat-head-meta" id="chat-head-meta"></span>
</span>
<button class="chat-export no-print" id="chat-export" type="button"
 title="Print this chat, or save it as a PDF">{icon("download", 14)} Export PDF</button>
<span class="head-break"></span>
<input id="chat-inner-query" type="search" placeholder="Search in this chat" autocomplete="off">
</div>
<div id="chat-body"><p class="empty">Pick a chat</p></div>
</div>
</div>
</section>'''


CHATS_CSS = """
.chat-search { margin-bottom: 12px; }
#chat-query, #chat-inner-query { background: #262626; border: 1px solid #444; border-radius: 8px; color: #e0e0e0; padding: 10px 12px; font-size: 15px; font-family: inherit; width: 100%; }
#chat-inner-query { font-size: 13px; padding: 7px 10px; max-width: 220px; }
#chat-query:focus, #chat-inner-query:focus { outline: none; border-color: #FFFE00; }
.chat-layout { display: grid; grid-template-columns: minmax(240px, 340px) minmax(0, 1fr); gap: 16px; height: calc(100vh - 170px); min-height: 420px; }
.chat-list-pane, .chat-view-pane { background: #202020; border-radius: 12px; overflow-y: auto; overflow-x: hidden; scrollbar-width: thin; scrollbar-color: #4a4a4a transparent; }
/* Firefox takes the two lines above, everything on WebKit needs the parts named. */
.chat-list-pane::-webkit-scrollbar, .chat-view-pane::-webkit-scrollbar { width: 10px; }
.chat-list-pane::-webkit-scrollbar-track, .chat-view-pane::-webkit-scrollbar-track { background: transparent; }
.chat-list-pane::-webkit-scrollbar-thumb, .chat-view-pane::-webkit-scrollbar-thumb { background: #3d3d3d; border: 2px solid #202020; border-radius: 6px; }
.chat-list-pane::-webkit-scrollbar-thumb:hover, .chat-view-pane::-webkit-scrollbar-thumb:hover { background: #5a5a5a; }
.chat-list-pane { padding: 8px; }
.pane-label { color: #777; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; padding: 10px 10px 4px; }
/* Two answers to one search, kept apart so it is obvious which is which. */
.result-block + .result-block { margin-top: 14px; padding-top: 10px; border-top: 1px solid #333; }
#chat-hit-block .pane-label { color: #FFFE00; }
.chat-row { display: flex; align-items: center; gap: 10px; width: 100%; padding: 9px 10px; border: none; border-radius: 10px; background: none; color: inherit; font-family: inherit; text-align: left; cursor: pointer; }
.chat-row:hover { background: #2a2a2a; }
.chat-row.active { background: #333; }
.chat-row-main { min-width: 0; flex: 1 1 auto; }
.chat-row-top { display: flex; justify-content: space-between; gap: 8px; }
.chat-row-name { display: flex; align-items: center; gap: 5px; font-weight: 700; color: #fff; font-size: 14px; overflow: hidden; white-space: nowrap; min-width: 0; }
.chat-row-user { color: #8d8d8d; font-weight: 400; font-size: 12px; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.avatar-slot { flex: 0 0 auto; display: inline-flex; }
.avatar-group { background: #262626; padding: 0; }
.avatar-group svg { width: 100%; height: 100%; display: block; }
.chat-row-date, .chat-row-count { color: #888; font-size: 11px; white-space: nowrap; }
.chat-row-preview { display: block; color: #999; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-hit { display: block; width: 100%; padding: 8px 10px; border: none; border-radius: 8px; background: none; color: inherit; font-family: inherit; text-align: left; cursor: pointer; border-bottom: 1px solid #262626; }
.chat-hit:hover { background: #2a2a2a; }
.chat-hit-head { display: flex; justify-content: space-between; gap: 8px; font-size: 11px; color: #888; }
.chat-hit-chat { color: #FFFE00; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-hit-text { display: block; font-size: 12.5px; color: #ddd; margin-top: 2px; overflow-wrap: anywhere; }
mark { background: #FFFE00; color: #1a1a1a; border-radius: 2px; }
.chat-view-head[hidden] { display: none; }
.chat-view-head { position: sticky; top: 0; z-index: 2; display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #242424; border-bottom: 1px solid #303030; }
.chat-head-main { flex: 1 1 auto; min-width: 0; }
.chat-head-name { display: flex; align-items: center; gap: 6px; font-weight: 700; color: #fff; font-size: 15px; overflow: hidden; white-space: nowrap; }
.chat-head-meta { display: block; color: #888; font-size: 12px; }
/* Same colours as the export buttons on the charts, only wide enough for a word. */
.chat-export { display: inline-flex; align-items: center; gap: 7px; flex: 0 0 auto; border-radius: 8px; border: 1px solid #2f5c73; background: #17303c; color: #7ad3ff; font-family: inherit; font-size: 12.5px; font-weight: 600; padding: 7px 12px; cursor: pointer; }
.chat-export:hover { background: #1d3d4c; border-color: #7ad3ff; }
.head-break { display: none; }
/* The cover belongs to the printed chat only, never to the page on screen. */
#chat-cover { display: none; }
#chat-body { padding: 16px 20px; }
#chat-body .sender { font-weight: 700; font-size: 14px; margin-top: 16px; padding-top: 8px; }
#chat-body hr { border: none; border-top: 1px solid; margin: 2px 0 6px; }
#chat-body .msg { padding: 4px 0; font-size: 15px; line-height: 1.4; overflow-wrap: anywhere; }
#chat-body .msg.target { background: #2f2f1a; border-radius: 6px; }
#chat-body .ts { color: #888; font-size: 11px; margin-left: 8px; }
#chat-body .system-msg { text-align: center; color: #888; font-size: 13px; padding: 8px 0; font-style: italic; }
#chat-body .media, #chat-body .snap { color: #aaa; }
#chat-body .msg-media { margin: 6px 0; }
#chat-body .msg-media img, #chat-body .msg-media video { max-width: 100%; max-height: 400px; border-radius: 8px; display: block; }
#chat-body .msg-media audio { width: 100%; margin: 4px 0; }
#chat-body .msg-media-link { margin: 6px 0; font-size: 13px; word-break: break-all; }
#chat-body .damaged-note { color: #c9a227; font-size: 11px; margin-top: 2px; }
#chat-body .collapsed { background: #191919; border-radius: 8px; padding: 10px 14px; margin: 8px 0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
#chat-body .collapsed:hover { background: #222; }
#chat-body .collapsed-label { color: #ccc; font-size: 13px; }
#chat-body .collapsed-toggle { color: #888; font-size: 12px; }
#chat-body .hidden { display: none; }
@media (max-width: 860px) {
  .chat-layout { grid-template-columns: minmax(0, 1fr); height: auto; }
  .chat-list-pane { max-height: 320px; }
  #chat-inner-query { max-width: 140px; }
  /* The button gets a line of its own under the name and the search. */
  .chat-view-head { flex-wrap: wrap; }
  .avatar-slot { order: 1; }
  .chat-head-main { order: 2; }
  #chat-inner-query { order: 3; }
  .head-break { display: block; order: 4; flex: 1 0 100%; height: 0; }
  .chat-export { order: 5; margin-right: auto; }
}

/* Printing one chat: everything that is not the conversation steps out of the
   way, and the dark theme flips so it does not eat a cartridge. */
@media print {
  body.printing-chat .app-nav, body.printing-chat .to-top, body.printing-chat .chat-search,
  body.printing-chat .chat-list-pane, body.printing-chat #chat-inner-query,
  body.printing-chat .chat-export, body.printing-chat .head-break { display: none !important; }
  body.printing-chat .tab-panel { display: none !important; }
  body.printing-chat #tab-chats { display: block !important; }
  body.printing-chat .chat-layout { display: block; height: auto; min-height: 0; }
  body.printing-chat .chat-view-pane { background: none; overflow: visible; border-radius: 0; }
  body.printing-chat .chat-view-head { position: static; background: none; border-bottom: 1pt solid #999; padding: 0 0 6pt; margin-bottom: 10pt; }
  body.printing-chat .chat-head-name { color: #000; }
  body.printing-chat .chat-head-meta { color: #555; }
  body.printing-chat #chat-cover { display: block; }
  body.printing-chat #chat-body { padding: 0; }
  body.printing-chat #chat-body .msg { color: #000; }
  body.printing-chat #chat-body .sender { color: var(--sender-print) !important; break-after: avoid; }
  body.printing-chat #chat-body hr { border-color: var(--sender-print) !important; opacity: 0.55 !important; }
  body.printing-chat #chat-body .ts, body.printing-chat #chat-body .system-msg,
  body.printing-chat #chat-body .media, body.printing-chat #chat-body .snap { color: #666; }
  body.printing-chat #chat-body .msg.target { background: none; }
  body.printing-chat #chat-body .collapsed { background: #f2f2f2; border: 0.5pt solid #ddd; break-inside: avoid; }
  body.printing-chat #chat-body .collapsed-label { color: #333; }
  body.printing-chat #chat-body .collapsed-toggle { display: none; }
  body.printing-chat #chat-body .msg-media { break-inside: avoid; }
  body.printing-chat #chat-body .msg-media img { max-height: 90mm; width: auto; }
  body.printing-chat #chat-body video, body.printing-chat #chat-body audio { display: none; }
  @page { margin: 14mm 12mm; }
}
"""

CHATS_JS = r"""
(function () {
    "use strict";
    var DATA = window.SNAPXO_CHATS || { chats: [] };
    var MAX_HITS = 200;

    var query = document.getElementById("chat-query");
    var innerQuery = document.getElementById("chat-inner-query");
    var list = document.getElementById("chat-list");
    var listLabel = document.getElementById("chat-list-label");
    var hits = document.getElementById("chat-hits");
    var hitBlock = document.getElementById("chat-hit-block");
    var hitLabel = document.getElementById("chat-hit-label");
    var body = document.getElementById("chat-body");
    var head = document.getElementById("chat-head");
    var headAvatar = document.getElementById("chat-head-avatar");
    var headName = document.getElementById("chat-head-name");
    var headMeta = document.getElementById("chat-head-meta");
    var exportButton = document.getElementById("chat-export");
    if (!list) return;

    var openIndex = -1;

    function esc(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function initials(name) {
        var parts = String(name).replace(/[_.\-]/g, " ").split(" ").filter(Boolean);
        if (!parts.length) return "?";
        if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }

    function hue(name) {
        var total = 0;
        for (var i = 0; i < name.length; i++) total += name.charCodeAt(i);
        return total % 360;
    }

    function day(stamp) {
        return String(stamp || "").slice(0, 10);
    }

    function dateCell(stamp) {
        var iso = day(stamp);
        return iso ? '<span data-date="' + iso + '">' + iso + "</span>" : "";
    }

    // A person keeps their initials. A group gets three circles instead, which
    // tells the two apart before you have read a single name.
    function avatarMarkup(chat, className) {
        var base = hue(chat.t);
        if (!chat.g) {
            return '<span class="' + className + '" style="background:hsl(' + base +
                   ',45%,42%)">' + esc(initials(chat.t)) + "</span>";
        }
        var circles = "";
        var spots = [[8.5, 8], [15.5, 8], [12, 15.5]];
        for (var i = 0; i < 3; i++) {
            circles += '<circle cx="' + spots[i][0] + '" cy="' + spots[i][1] + '" r="5.4" fill="hsl(' +
                       ((base + i * 110) % 360) + ',55%,52%)" stroke="#202020" stroke-width="1.4"/>';
        }
        return '<span class="' + className + ' avatar-group"><svg viewBox="0 0 24 24">' +
               circles + "</svg></span>";
    }

    function renderList(matching) {
        var markup = "";
        DATA.chats.forEach(function (chat, index) {
            if (matching && matching.indexOf(index) < 0) return;
            markup += '<button class="chat-row' + (index === openIndex ? " active" : "") +
                '" data-chat="' + index + '">' +
                avatarMarkup(chat, "avatar") +
                '<span class="chat-row-main"><span class="chat-row-top">' +
                '<span class="chat-row-name">' + esc(chat.t) +
                (chat.u ? '<span class="chat-row-user">(' + esc(chat.u) + ")</span>" : "") +
                "</span>" +
                '<span class="chat-row-date">' + dateCell(chat.d) + "</span></span>" +
                '<span class="chat-row-preview">' + esc(chat.p) + "</span></span>" +
                '<span class="chat-row-count">' + chat.n + " msg</span></button>";
        });
        list.innerHTML = markup || '<p class="empty">No chat matches.</p>';
        if (window.SEODate) window.SEODate.apply(list);
    }

    function highlight(text, needle) {
        var at = text.toLowerCase().indexOf(needle);
        if (at < 0) return esc(text);
        var start = Math.max(0, at - 40);
        return (start > 0 ? "..." : "") + esc(text.slice(start, at)) + "<mark>" +
               esc(text.slice(at, at + needle.length)) + "</mark>" +
               esc(text.slice(at + needle.length, at + needle.length + 90));
    }

    function renderHits(needle) {
        var found = [];
        for (var i = 0; i < DATA.chats.length && found.length < MAX_HITS; i++) {
            var messages = DATA.chats[i].x || [];
            for (var j = 0; j < messages.length && found.length < MAX_HITS; j++) {
                if (messages[j].x.toLowerCase().indexOf(needle) >= 0) {
                    found.push({ chat: i, message: messages[j] });
                }
            }
        }
        hitBlock.hidden = false;
        if (!found.length) {
            hitLabel.textContent = "No message matches";
            hits.innerHTML = "";
            return;
        }
        hitLabel.textContent = found.length +
            (found.length === 1 ? " message contains it" : " messages contain it");
        var markup = "";
        found.forEach(function (entry) {
            var chat = DATA.chats[entry.chat];
            markup += '<button class="chat-hit" data-chat="' + entry.chat + '" data-anchor="' +
                esc(entry.message.a) + '"><span class="chat-hit-head">' +
                '<span class="chat-hit-chat">' + esc(chat.t) + "</span><span>" +
                dateCell(entry.message.t) + "</span></span>" +
                '<span class="chat-hit-text">' + highlight(entry.message.x, needle) +
                "</span></button>";
        });
        hits.innerHTML = markup;
        if (window.SEODate) window.SEODate.apply(hits);
    }

    function openChat(index, anchor) {
        var chat = DATA.chats[index];
        if (!chat) return;
        openIndex = index;
        body.innerHTML = chat.b || '<p class="empty">This chat has no messages.</p>';
        headAvatar.innerHTML = avatarMarkup(chat, "avatar");
        headName.innerHTML = esc(chat.t) +
            (chat.u ? ' <span class="chat-row-user">(' + esc(chat.u) + ")</span>" : "");
        headMeta.textContent = (chat.g ? "Group · " : "") + chat.n + " messages" +
            (chat.d ? " · last " + day(chat.d) : "");
        head.hidden = false;
        innerQuery.value = "";
        if (window.SEODate) window.SEODate.apply(body);
        Array.prototype.forEach.call(list.querySelectorAll(".chat-row"), function (row) {
            row.classList.toggle("active", row.getAttribute("data-chat") === String(index));
        });

        var target = anchor ? document.getElementById(anchor) : null;
        if (target) {
            target.classList.add("target");
            target.scrollIntoView({ block: "center" });
        } else {
            body.parentNode.scrollTop = 0;
        }
    }

    function filterOpenChat(needle) {
        var nodes = body.children;
        if (!needle) {
            Array.prototype.forEach.call(nodes, function (node) { node.classList.remove("hidden"); });
            return;
        }
        Array.prototype.forEach.call(nodes, function (node) { node.classList.add("hidden"); });
        Array.prototype.forEach.call(body.querySelectorAll(".msg"), function (node) {
            if (node.textContent.toLowerCase().indexOf(needle) < 0) return;
            node.classList.remove("hidden");
            for (var above = node.previousElementSibling; above; above = above.previousElementSibling) {
                if (above.tagName === "HR") above.classList.remove("hidden");
                if (above.classList.contains("sender")) {
                    above.classList.remove("hidden");
                    return;
                }
            }
        });
    }

    query.addEventListener("input", function () {
        var needle = query.value.trim().toLowerCase();
        if (!needle) {
            hits.innerHTML = "";
            hitBlock.hidden = true;
            listLabel.textContent = "Chats";
            renderList(null);
            return;
        }
        var matching = [];
        DATA.chats.forEach(function (chat, index) {
            var haystack = (chat.t + " " + (chat.u || "")).toLowerCase();
            if (haystack.indexOf(needle) >= 0) matching.push(index);
        });
        listLabel.textContent = matching.length +
            (matching.length === 1 ? " chat matches the name" : " chats match the name");
        renderList(matching);
        renderHits(needle);
    });

    innerQuery.addEventListener("input", function () {
        filterOpenChat(innerQuery.value.trim().toLowerCase());
    });

    // The archive facts are already on the cover, only the chat itself is not.
    function fillCover(chat) {
        var cover = document.getElementById("chat-cover");
        cover.querySelector(".cover-title").textContent = chat.t;
        cover.querySelector(".cover-subtitle").textContent =
            chat.g ? "Group chat" : "Conversation between two people";

        var facts = [];
        if (chat.u) facts.push(["Username", chat.u]);
        facts.push(["Messages", String(chat.n)]);
        if (chat.d) facts.push(["Last message", chat.d]);

        var body = cover.querySelector(".cover-facts tbody");
        Array.prototype.forEach.call(body.querySelectorAll(".cover-chat-fact"),
                                     function (row) { body.removeChild(row); });
        facts.reverse().forEach(function (pair) {
            var row = document.createElement("tr");
            row.className = "cover-chat-fact";
            var label = document.createElement("th");
            label.setAttribute("scope", "row");
            label.textContent = pair[0];
            var value = document.createElement("td");
            value.textContent = pair[1];
            row.appendChild(label);
            row.appendChild(value);
            body.insertBefore(row, body.firstChild);
        });
    }

    // No PDF writer here, the browser has one: printing a page to PDF is a
    // save dialog away, so this only clears the way and names the file.
    function printOpenChat() {
        if (openIndex < 0) return;
        var chat = DATA.chats[openIndex];
        var title = document.title;
        fillCover(chat);
        innerQuery.value = "";
        filterOpenChat("");
        document.title = chat.t + " - SnapXO chat";
        document.body.classList.add("printing-chat");
        window.addEventListener("afterprint", function restore() {
            window.removeEventListener("afterprint", restore);
            document.body.classList.remove("printing-chat");
            document.title = title;
        });
        window.print();
    }

    exportButton.addEventListener("click", printOpenChat);

    document.addEventListener("click", function (event) {
        var row = event.target.closest ? event.target.closest("[data-chat]") : null;
        if (!row || !list.contains(row) && !hits.contains(row)) return;
        openChat(parseInt(row.getAttribute("data-chat"), 10), row.getAttribute("data-anchor"));
    });

    document.addEventListener("click", function (event) {
        var shortcut = event.target.closest ? event.target.closest("[data-open-chat]") : null;
        if (!shortcut) return;
        var wanted = shortcut.getAttribute("data-open-chat");
        for (var i = 0; i < DATA.chats.length; i++) {
            if (DATA.chats[i].t === wanted) {
                if (window.SEOTabs) window.SEOTabs.show("chats");
                window.location.hash = "chats";
                openChat(i, null);
                return;
            }
        }
    });

    renderList(null);
})();
"""
