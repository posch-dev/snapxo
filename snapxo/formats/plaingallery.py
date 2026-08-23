# The picture book: every file uncropped at print size, with only its date over
# it, as many to a page as fit without cutting anything off.

import html

from ..facts.provenance import COVER_CSS

PLAIN_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, 'Segoe UI', sans-serif; background: #fff; color: #1a1a1a; font-size: 10pt; }
h2 { font-size: 13pt; margin: 0 0 3mm; padding-bottom: 1.5mm; border-bottom: 1pt solid #999; break-after: avoid; }
.year { break-before: page; }
.year:first-of-type { break-before: avoid; }
/* Nothing is cropped, so the tiles are as tall as the pictures make them and
   the page simply takes what fits. */
.plate { display: flex; flex-wrap: wrap; gap: 4mm; align-items: flex-start; }
.piece { break-inside: avoid; text-align: center; }
.piece img { max-width: 84mm; max-height: 105mm; width: auto; height: auto; display: block; border-radius: 1.5mm; }
.piece .frame { position: relative; display: inline-block; }
.piece .caption { font-size: 7pt; color: #777; margin-top: 1mm; line-height: 1.3; }
.piece .file { display: block; font-size: 6.5pt; color: #999; word-break: break-all; }
.play-mark { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 14mm; height: 14mm; border-radius: 50%; background: rgba(0,0,0,0.55); color: #fff; font-size: 14pt; display: flex; align-items: center; justify-content: center; }
.no-picture { display: flex; align-items: center; justify-content: center; width: 60mm; height: 34mm; background: #f4f4f4; border: 0.5pt solid #ccc; border-radius: 1.5mm; color: #888; font-size: 9pt; }
@page { size: A4; margin: 12mm 10mm; }
"""


def _piece(entry: dict, preview: str | None) -> str:
    kind = entry.get("type", "")
    name = html.escape(entry.get("new_name", ""))
    date = html.escape(str(entry.get("date", "")))

    if preview:
        mark = '<span class="play-mark">&#9654;</span>' if kind == "video" else ""
        frame = f'<span class="frame"><img src="{html.escape(preview)}" alt="{name}">{mark}</span>'
    else:
        label = {"audio": "Voice message", "video": "Video"}.get(kind, "No preview")
        frame = f'<span class="frame"><span class="no-picture">{label}</span></span>'

    return (f'<figure class="piece">{frame}<figcaption class="caption">{date}'
            f'<span class="file">{name}</span></figcaption></figure>')


def build_plain_gallery(file_index: list[dict], previews: dict[int, str], cover: str = "") -> str:
    # previews holds the 1280 px copy where there is one, the thumbnail otherwise.
    by_year: dict[str, list[str]] = {}
    for position, entry in enumerate(file_index):
        year = str(entry.get("subfolder") or entry.get("year") or "unknown")[:4]
        by_year.setdefault(year, []).append(_piece(entry, previews.get(position)))

    sections = []
    for year in sorted(by_year, reverse=True):
        pieces = by_year[year]
        sections.append(f'<section class="year"><h2>{html.escape(year)} '
                        f'({len(pieces)} files)</h2><div class="plate">{"".join(pieces)}</div></section>')

    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
            '<title>Snapchat Memories</title>\n<style>' + PLAIN_CSS + COVER_CSS +
            "</style>\n</head>\n<body>\n" + cover + "".join(sections) + "\n</body></html>")
