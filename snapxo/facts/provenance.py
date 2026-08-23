import html
from datetime import datetime
from pathlib import Path

from ..archive.manifest import load_manifest
from ..parts.shared import date_span, split_timestamp


def archive_facts(folder: Path, file_index: list[dict], series: dict) -> dict:
    manifest = load_manifest(folder) or {}
    days = sorted({str(entry.get("date", ""))[:10] for entry in file_index} - {""})
    months = series.get("months") or []

    starts = [value for value in ((days[0] if days else ""), (months[0] if months else "")) if value]
    ends = [value for value in ((days[-1] if days else ""), series.get("newest_data", "")) if value]

    return {
        "sources": [str(name) for name in manifest.get("sources", []) if name],
        "built": str(manifest.get("generated") or ""),
        "account": str(manifest.get("own_username") or ""),
        "timezone": str(manifest.get("timezone") or "UTC"),
        "covered_from": min(starts) if starts else "",
        "covered_to": max(ends) if ends else "",
        "files": len(file_index),
        "messages": series.get("total_messages", 0),
        "chats": series.get("total_chats", 0),
        "rendered": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def fact_rows(facts: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if facts["account"]:
        rows.append(("Account", facts["account"]))
    if facts["covered_from"] and facts["covered_to"]:
        rows.append(("Data covers", f'{facts["covered_from"]} to {facts["covered_to"]}'))
    if facts["built"]:
        rows.append(("Archive built", facts["built"]))
    rows.append(("Pages written", facts["rendered"]))
    rows.append(("Timestamps in", facts["timezone"]))
    if facts["sources"]:
        rows.append(("Built from", ", ".join(facts["sources"])))
    return rows


EXPIRY_NOTE = ("Snapchat only exports messages that were saved or had not expired yet, "
               "so a conversation is what survived, not everything that was said.")


def _shown(value: str) -> str:
    # Tagged so the date format picker can rewrite it, plain text otherwise.
    day, time = split_timestamp(value)
    return date_span(day, time) if day else html.escape(value)


def provenance_panel(facts: dict) -> str:
    rows = "".join(
        f'<tr><th scope="row">{html.escape(label)}</th><td>{_shown(value)}</td></tr>'
        for label, value in fact_rows(facts)
    )
    return f'''<section class="provenance">
<h3>About this archive</h3>
<table><tbody>{rows}</tbody></table>
<p class="provenance-note">{html.escape(EXPIRY_NOTE)}</p>
</section>'''


PROVENANCE_CSS = """
.provenance { background: #202020; border-radius: 10px; padding: 16px; margin-bottom: 24px; }
.provenance h3 { font-size: 11px; color: #777; text-transform: uppercase; letter-spacing: 0.09em; font-weight: 600; margin-bottom: 8px; }
.provenance table { width: 100%; border-collapse: collapse; font-size: 13px; }
.provenance th { text-align: left; font-weight: 400; color: #888; padding: 5px 12px 5px 0; background: none; border: none; white-space: nowrap; vertical-align: top; }
.provenance td { color: #ddd; padding: 5px 0; border: none; word-break: break-word; }
.provenance-note { color: #c9a227; font-size: 12px; margin-top: 10px; line-height: 1.45; }
@media print {
  .provenance { background: none; border: 1px solid #ddd; }
  .provenance td { color: #000; }
  .provenance-note { color: #7a6410; }
}
"""


def cover_page(title: str, subtitle: str, rows: list[tuple[str, str]], version: str) -> str:
    # Everything identifying sits here, so it can be torn off before handing the
    # document on.
    listed = "".join(
        f'<tr><th scope="row">{html.escape(label)}</th><td>{html.escape(value)}</td></tr>'
        for label, value in rows
    )
    return f'''<section class="pdf-cover">
<h1 class="cover-title">{html.escape(title)}</h1>
<p class="cover-subtitle">{html.escape(subtitle)}</p>
<table class="cover-facts"><tbody>{listed}</tbody></table>
<p class="cover-note">{html.escape(EXPIRY_NOTE)}</p>
<p class="cover-tool">Made with SnapXO {html.escape(version)} &middot; github.com/posch-dev/snapxo</p>
</section>'''


COVER_CSS = """
.pdf-cover { display: none; }
@media print {
  .pdf-cover { display: block; break-after: page; padding: 24mm 0 0; }
  .cover-title { font-size: 26px; color: #000; text-align: left; margin: 0 0 6px; }
  .cover-subtitle { font-size: 14px; color: #444; margin: 0 0 28px; }
  .cover-facts { width: 100%; border-collapse: collapse; font-size: 11.5px; margin-bottom: 28px; }
  .cover-facts th { text-align: left; font-weight: 400; color: #666; padding: 5px 14px 5px 0; background: none; border: none; white-space: nowrap; vertical-align: top; width: 34mm; }
  .cover-facts td { color: #000; padding: 5px 0; border: none; word-break: break-word; }
  .cover-note { font-size: 11px; color: #444; line-height: 1.5; border-left: 2px solid #bbb; padding-left: 10px; margin-bottom: 24px; }
  .cover-tool { font-size: 10px; color: #888; }
}
"""
