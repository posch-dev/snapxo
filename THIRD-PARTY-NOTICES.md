# Third party notices

SnapXO couldnt have been built without these precious tools. This file lists all of it, what it is
used for, and the licence it comes under.

SnapXO itself is GPL-3.0-only, see [LICENSE](https://github.com/posch-dev/snapxo/blob/main/LICENSE).

## Python packages

Installed with SnapXO.

| Package | Licence | Used for |
|---|---|---|
| [click](https://github.com/pallets/click) | BSD-3-Clause | the command line interface |
| [rich](https://github.com/Textualize/rich) | MIT | everything printed to the terminal, including the questions `-i` asks |
| [Pillow](https://github.com/python-pillow/Pillow) | MIT-CMU | reading images, writing thumbnails, burning overlays |
| [piexif](https://github.com/hMatoba/Piexif) | MIT | writing the capture date into the EXIF of a photo |
| [playwright](https://github.com/microsoft/playwright-python) | Apache-2.0 | driving the browser that renders the PDFs |
| [tzdata](https://github.com/python/tzdata) | Apache-2.0 | the timezone database, on Windows only, where the system ships none |

Optional, each installed only for the feature that needs it.

| Package | Licence | Installed by |
|---|---|---|
| [openpyxl](https://foss.heptapod.net/openpyxl/openpyxl) | MIT | `snapxo[spreadsheet]`, for XLSX with real Excel charts |
| [bcrypt](https://github.com/pyca/bcrypt) | Apache-2.0 | `snapxo[docker]`, for hashing the password |
| [PyYAML](https://github.com/yaml/pyyaml) | MIT | `snapxo[docker]`, for merging into an existing compose file |
| [static-ffmpeg](https://github.com/zackees/static_ffmpeg) | MIT | `snapxo[ffmpeg]`, ships ffmpeg binaries for systems without them |

## External programs

Not installed by SnapXO, called when they are there.

| Program | Licence | Used for |
|---|---|---|
| [FFmpeg](https://ffmpeg.org/) | LGPL-2.1-or-later, GPL-2.0-or-later for some builds | encoding videos, burning overlays, reading media details, detecting voice messages |
| [Chromium](https://www.chromium.org/) | BSD-3-Clause and others | rendering the PDFs, installed by `playwright install chromium` |
| [nginx](https://nginx.org/) | BSD-2-Clause | serving an archive, as the `nginx:alpine` image `snapxo docker` writes into the compose file |
| [Apache httpd](https://httpd.apache.org/) | Apache-2.0 | its `htpasswd`, from the `httpd:alpine` image, when bcrypt is not installed |

## In the generated pages

The map page loads these from unpkg, with subresource integrity hashes. Every
other page works with no network at all.

| Library | Licence | Used for |
|---|---|---|
| [Leaflet](https://leafletjs.com/) | BSD-2-Clause | the map itself |
| [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) | MIT | grouping thousands of points into clusters |
| [noUiSlider](https://refreshless.com/nouislider/) | MIT | the time range slider under the map |

Map tiles come from [OpenStreetMap](https://www.openstreetmap.org/copyright).
The map data is ODbL, the tiles are served under the OpenStreetMap Foundation's
tile usage policy.

> **SnapXO itself never connects to the network.** 
>
> The requests above are not SnapXO asking for anything. They happen in your
> browser, when you open `map.html`, and they go to unpkg for the three
> libraries and to OpenStreetMap for the map tiles. Those are the external projects
> listed here. Building the map makes no requests at all, and a `map.html` you
> never open makes none either.
>
> To read further: the licence links in the tables above,
> [OpenStreetMap's copyright page](https://www.openstreetmap.org/copyright), and
> the Privacy section in the [README](https://github.com/posch-dev/snapxo/blob/main/README.md#privacy) and in
> [DOCUMENTATION.md](https://github.com/posch-dev/snapxo/blob/main/DOCUMENTATION.md#privacy).

## Icons

The icon paths in `snapxo/parts/icons.py` follow
[Lucide](https://lucide.dev/) and are stored as bare SVG path data. Lucide is ISC licensed and the
notice is reproduced in full below, as that licence requires.

```
ISC License

Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part
of Feather (MIT). All other copyright (c) for Lucide are held by Lucide
Contributors 2022.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
```

## Not affiliated with Snapchat

SnapXO reads the data export Snapchat hands you. It is not made by, endorsed by
or connected to Snap Inc. Snapchat is their trademark.
