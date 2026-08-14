import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()

# Parse "Latitude, Longitude: -48.87667, -123.39333"
LOCATION_RE = re.compile(r"Latitude,\s*Longitude:\s*([-\d.]+),\s*([-\d.]+)")


def apply_file_times(file_index: list[dict], dry_run: bool = False) -> int:
    # Videos carry no EXIF, so the file date is all a photo app has to sort by.
    if dry_run:
        return 0

    written = 0
    for entry in file_index:
        dest = entry.get("dest")
        date = entry.get("date") or ""
        if not dest or len(date) < 10:
            continue
        try:
            # Noon, so no timezone can push the file into the day before
            stamp = datetime.strptime(date[:10], "%Y-%m-%d").replace(hour=12).timestamp()
            os.utime(dest, (stamp, stamp))
            written += 1
        except (ValueError, OSError):
            continue
    return written


def _parse_location_string(location: str) -> tuple[float, float] | None:
    # Parse Snapchat's location format into (lat, lon) or None.
    m = LOCATION_RE.search(location)
    if m:
        try:
            lat, lon = float(m.group(1)), float(m.group(2))
            if lat != 0 or lon != 0:
                return lat, lon
        except ValueError:
            pass
    return None


def _decimal_to_dms(decimal: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    decimal = abs(decimal)
    degrees = int(decimal)
    minutes_float = (decimal - degrees) * 60
    minutes = int(minutes_float)
    seconds = int((minutes_float - minutes) * 60 * 100)
    return ((degrees, 1), (minutes, 1), (seconds, 100))


def write_exif_gps(filepath: Path, lat: float, lon: float, date_str: str | None = None) -> bool:
    ext = filepath.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return _write_exif_jpeg(filepath, lat, lon, date_str)
    elif ext == ".png":
        return _write_exif_png(filepath, lat, lon, date_str)
    return False


def _write_exif_jpeg(filepath: Path, lat: float, lon: float, date_str: str | None) -> bool:
    try:
        import piexif

        try:
            exif_dict = piexif.load(str(filepath))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        lat_ref = b"N" if lat >= 0 else b"S"
        lon_ref = b"E" if lon >= 0 else b"W"

        exif_dict["GPS"] = {
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLatitude: _decimal_to_dms(lat),
            piexif.GPSIFD.GPSLongitudeRef: lon_ref,
            piexif.GPSIFD.GPSLongitude: _decimal_to_dms(lon),
        }

        if date_str:
            exif_date = date_str[:10].replace("-", ":") + " 00:00:00"
            exif_dict["0th"][piexif.ImageIFD.DateTime] = exif_date.encode()
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = exif_date.encode()

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(filepath))
        return True
    except Exception as e:
        console.print(f"  [red]EXIF error ({filepath.name}): {e}[/red]")
        return False


def _write_exif_png(filepath: Path, lat: float, lon: float, date_str: str | None) -> bool:
    try:
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo

        img = Image.open(filepath)
        png_info = PngInfo()

        png_info.add_text("GPS:Latitude", str(lat))
        png_info.add_text("GPS:Longitude", str(lon))
        if date_str:
            png_info.add_text("DateTimeOriginal", date_str[:10].replace("-", ":") + " 00:00:00")

        if hasattr(img, "text"):
            for key, value in img.text.items():
                if not key.startswith("GPS:") and key != "DateTimeOriginal":
                    png_info.add_text(key, value)

        img.save(filepath, pnginfo=png_info)
        return True
    except Exception as e:
        console.print(f"  [red]PNG EXIF error ({filepath.name}): {e}[/red]")
        return False


def apply_gps_metadata(
    file_index: list[dict],
    memories_history: list[dict],
    dry_run: bool = False,
) -> int:
    # Match files to memories_history by date and write GPS. Entries look like
    # "Location": "Latitude, Longitude: -48.87667, -123.39333".
    # Build lookup: date -> list of GPS coords
    date_to_entries: dict[str, list[dict]] = defaultdict(list)

    for entry in memories_history:
        date_raw = entry.get("Date", "")
        location = entry.get("Location", "")
        if not date_raw or not location:
            continue

        coords = _parse_location_string(location)
        if coords:
            lat, lon = coords
            date_key = date_raw[:10]
            date_to_entries[date_key].append({
                "lat": lat, "lon": lon, "date": date_raw,
            })

    written = 0
    for entry in file_index:
        if entry["type"] not in ("image",):
            continue
        if entry["source"] != "memory":
            continue

        date = entry["date"]
        gps_entries = date_to_entries.get(date, [])
        if not gps_entries:
            continue

        gps = gps_entries[0]
        dest = Path(entry["dest"])

        if dry_run:
            written += 1
            continue

        if dest.exists() and write_exif_gps(dest, gps["lat"], gps["lon"], date):
            written += 1

    return written
