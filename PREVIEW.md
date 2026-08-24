# What SnapXO looks like

Snapchat hands you your data as a jumbled mess of
thousands of JSONs, HTML and media files.
SnapXO sorts all of it, converts it, and hands it to you as a well-structured, normal folder.
But it also offers you a neat user interface that's nice to look at and familiar to Snapchat users.

The user interface part is what this page shows: the archive itself, one HTML page
called `index.html`. Double-click it and it opens, straight from disk, natively.
You can run it without internet and without any software. Or run `snapxo docker` and serve the same page on your
home network, so you can even use and browse it on your phone. Same file either way.

Below, screenshots and files from a demo archive generated with SnapXO,
from both desktop and smartphone.

> **This is a demo archive.** The account is invented. Every name is a standard
> placeholder, and the chats, statistics, friend list, snap history and locations
> were all generated. Nothing here belongs to a real person.

- [Overview](#overview)
- [Chats](#chats)
- [Media](#media)
- [Stats](#stats)
- [Charts](#charts)
- [SnapMap: Locations](#snapmap-locations)
- [SnapMap: Memories](#snapmap-memories)
- [What comes out of it](#what-comes-out-of-it)

## Overview

The tab it opens on. It offers a quick look at your stats, the busiest chats and the newest media, each
one a hyperlink into the tab it belongs to.

<table>
<tr>
<td align="center"><b>Desktop</b></td>
<td align="center"><b>Phone</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Desktop/desktop-overview.png" width="546" alt="Overview on a desktop"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Smartphone/smartphone-overview.png" width="137" alt="Overview on a phone"></td>
</tr>
</table>

## Chats

The chat list and the conversation you picked. One search matches chat names and
message text at once. A second search filters inside the open chat. Runs of
expired snaps collapse into a single line, so they do not bury what was written.

<table>
<tr>
<td align="center"><b>Desktop</b></td>
<td align="center"><b>Phone, the chat list</b></td>
<td align="center"><b>Phone, an open chat</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Desktop/desktop-chats.png" width="547" alt="Chats on a desktop"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Smartphone/smartphone-chats.png" width="136" alt="Chat list on a phone"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Smartphone/smartphone-chats-2.png" width="139" alt="An open conversation on a phone"></td>
</tr>
</table>

## Media

The gallery. Filter by type, jump by year, open a details panel on any file to
see its date, size, length and encoding. More loads as you scroll.

<table>
<tr>
<td align="center"><b>Desktop</b></td>
<td align="center"><b>Phone</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Desktop/desktop-media.png" width="540" alt="Media gallery on a desktop"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Smartphone/smartphone-media.png" width="137" alt="Media gallery on a phone"></td>
</tr>
</table>

## Stats

The numbers as a grouped table: memories, chat media, friends, calls, searches,
Snapscore. Every one has a table behind it.

<table>
<tr>
<td align="center" colspan="2"><b>Desktop</b></td>
</tr>
<tr>
<td colspan="2"><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Desktop/desktop-stats.png" width="686" alt="Stats on a desktop"></td>
</tr>
<tr>
<td align="center"><b>Phone</b></td>
<td align="center"><b>Phone, the tables</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Smartphone/smartphone-stats.png" width="138" alt="Stats on a phone"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Smartphone/smartphone-stats-2.png" width="137" alt="Stats tables on a phone"></td>
</tr>
</table>

## Charts

Messages, chat media, snaps, friends and story views over time. Activity by hour
and by weekday. Type distribution. Who writes you most. Every chart has an info
button saying what it leaves out, because an export only holds the messages that
were saved.

<table>
<tr>
<td align="center"><b>Desktop</b></td>
<td align="center"><b>Phone</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Desktop/desktop-charts.png" width="541" alt="Charts on a desktop"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Smartphone/smartphone-charts.png" width="138" alt="Charts on a phone"></td>
</tr>
<tr>
<td align="center" colspan="2"><b>Desktop, the rest of the charts</b></td>
</tr>
<tr>
<td colspan="2"><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Desktop/desktop-charts-2.png" width="540" alt="More charts on a desktop"></td>
</tr>
</table>

## SnapMap: Locations

Your location history as a route, drawn point by point, with the accuracy
Snapchat recorded for each one.

<table>
<tr>
<td align="center"><b>Desktop</b></td>
<td align="center"><b>Phone</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Desktop/desktop-locations.png" width="544" alt="Location history on a desktop"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Smartphone/smartphone-locations.png" width="136" alt="Location history on a phone"></td>
</tr>
</table>

## SnapMap: Memories

The other mode. Every place something was saved, clustered. A click opens what is
there.

<table>
<tr>
<td align="center"><b>Desktop</b></td>
<td align="center"><b>Phone</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Desktop/desktop-snapmap.png" width="547" alt="Snap Map on a desktop"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Smartphone/smartphone-snapmap.png" width="139" alt="Snap Map on a phone"></td>
</tr>
</table>

## What comes out of it

The archive is not the only output. The files below are real, and they sit in
[.github/assets/Previews/Files](https://github.com/posch-dev/snapxo/tree/main/.github/assets/Previews/Files) if you want to
open them yourself.

### Statistics as a PDF

`snapxo pdf` prints the numbers and charts in colours meant for paper.

<table>
<tr>
<td align="center"><b>Cover page, every PDF gets one</b></td>
<td align="center"><b>The numbers</b></td>
<td align="center"><b>Messages and activity</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/stats-page-01.png" width="283" alt="stats.pdf cover page"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/stats-page-02.png" width="283" alt="stats.pdf numbers"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/stats-page-03.png" width="283" alt="stats.pdf messages over time and activity"></td>
</tr>
<tr>
<td align="center"><b>Snaps, friends, chat media</b></td>
<td align="center"><b>Story views and the rankings</b></td>
<td align="center"><b>The tables behind the numbers</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/stats-page-04.png" width="283" alt="stats.pdf snaps, friends and chat media over time"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/stats-page-05.png" width="283" alt="stats.pdf story views, who writes you most, most interacted with"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/stats-page-07.png" width="283" alt="stats.pdf friends table"></td>
</tr>
</table>

and many more in [stats.pdf](https://github.com/posch-dev/snapxo/blob/main/.github/assets/Previews/Files/stats.pdf) (34 pages)

### Media as a PDF, two ways

`media-details.pdf` puts every file next to its filename, date, size, length and
encoding, etc.. `media-plain.pdf` is a picture book: uncropped, nothing under it but
the date and filename.

<table>
<tr>
<td align="center"><b>media-details.pdf</b></td>
<td align="center"><b>media-plain.pdf</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/media-details-page-04.png" width="283" alt="media-details.pdf"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/media-plain-page-04.png" width="283" alt="media-plain.pdf"></td>
</tr>
</table>

[media-details.pdf](https://github.com/posch-dev/snapxo/blob/main/.github/assets/Previews/Files/media-details.pdf) and
[media-plain.pdf](https://github.com/posch-dev/snapxo/blob/main/.github/assets/Previews/Files/media-plain.pdf)

### Chats, on paper and on their own

`snapxo pdf` writes one PDF per conversation, attachments printed with their
details beside them. `snapxo html` writes the same chat as a single HTML file.

<table>
<tr>
<td align="center"><b>The conversation as a PDF</b></td>
<td align="center"><b>The conversation as one HTML file</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/erika.mustermann-page-07.png" width="283" alt="A conversation as a PDF"></td>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/chat-html.png" width="403" alt="A conversation as a single HTML file"></td>
</tr>
</table>

[erika.mustermann.pdf](https://github.com/posch-dev/snapxo/blob/main/.github/assets/Previews/Files/erika.mustermann.pdf) and
[erika.mustermann.html](https://github.com/posch-dev/snapxo/blob/main/.github/assets/Previews/Files/erika.mustermann.html)

> **Download the HTML on its own and the pictures stay empty.** The page finds
> its media through relative paths like `../2026/photo.jpg`, so the images and
> the voice notes only load from inside the archive they were written in. The
> text and the layout work anywhere. The PDF carries its pictures inside it, so
> that one works on its own. This only applies to this demo content; it works when you use the tool.

### The numbers as a spreadsheet

`snapxo spreadsheet` writes XLSX, ODS or CSV. The XLSX charts are real Excel
charts, not pictures of charts: recolour them, change their type, point them at
other cells.

<table>
<tr>
<td align="center"><b>The statistics workbook in Excel</b></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/posch-dev/snapxo/main/.github/assets/Previews/Files/excel-preview.png" width="880" alt="The statistics workbook open in Excel"></td>
</tr>
</table>

[snapxo-stats-2026-08-24.xlsx](https://github.com/posch-dev/snapxo/blob/main/.github/assets/Previews/Files/snapxo-stats-2026-08-24.xlsx), 11 sheets

> You only get editable Excel charts when using the CLI, though. Using the UI export, you can only get PNGs of the charts.
> You can still export all the data behind the charts through the UI tho.