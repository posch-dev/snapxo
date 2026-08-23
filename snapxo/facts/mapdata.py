import math
import re
from collections import defaultdict

LOCATION_RE = re.compile(r"Latitude,\s*Longitude:\s*([-\d.]+),\s*([-\d.]+)")

# Some entries read "48.12345 +- 65.00 meters", so the number is picked out
# rather than parsed whole. The accuracy is worth keeping.
COORD_RE = re.compile(r"(-?\d+(?:\.\d+)?)(?:\s*[±+-]\s*(\d+(?:\.\d+)?)\s*met)?")

# A memory has a coordinate and a day, never a link to the file. Inside this
# radius the pairing does not matter, the position is right either way.
SAME_PLACE_M = 250


def parse_coordinates(text: str) -> tuple[float, float, float] | None:
    halves = str(text).split(",")
    if len(halves) != 2:
        return None

    values = []
    accuracy = 0.0
    for half in halves:
        found = COORD_RE.match(half.strip())
        if not found:
            return None
        values.append(float(found.group(1)))
        if found.group(2):
            accuracy = max(accuracy, float(found.group(2)))

    lat, lon = values
    return None if lat == 0 and lon == 0 else (lat, lon, accuracy)


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def location_points(json_data: dict) -> list[dict]:
    history = json_data.get("location_history")
    if not isinstance(history, dict):
        return []

    points = []
    for entry in history.get("Location History", []):
        if not isinstance(entry, list) or len(entry) != 2:
            continue
        found = parse_coordinates(entry[1])
        if not found:
            continue
        lat, lon, accuracy = found
        point = {"lat": lat, "lon": lon, "t": str(entry[0])}
        if accuracy:
            point["acc"] = round(accuracy)
        points.append(point)

    points.sort(key=lambda point: point["t"])
    return points


def _memory_entries(json_data: dict) -> list[dict]:
    memories = json_data.get("memories_history")
    if not isinstance(memories, dict):
        return []

    entries = []
    for entry in memories.get("Saved Media", []):
        if not isinstance(entry, dict):
            continue
        raw = entry.get("Location", "") or ""
        found = LOCATION_RE.search(raw)
        pair = parse_coordinates(f"{found.group(1)},{found.group(2)}") if found else None
        if pair:
            entries.append({
                "lat": pair[0], "lon": pair[1],
                "t": str(entry.get("Date", "")),
                "kind": str(entry.get("Media Type", "")).lower(),
            })

    entries.sort(key=lambda entry: entry["t"])
    return entries


def _day_is_one_place(points: list[dict]) -> bool:
    first = points[0]
    return all(distance_m(first["lat"], first["lon"], point["lat"], point["lon"]) <= SAME_PLACE_M
               for point in points[1:])


def memory_points(json_data: dict, file_index: list[dict] | None = None) -> list[dict]:
    # Pairing a file to a point by day and order only decides which thumbnail is
    # shown, never where the point sits. Scattered days are marked as a guess.
    entries = _memory_entries(json_data)
    if not entries:
        return []

    by_day: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        by_day[entry["t"][:10]].append(entry)

    files_by_day: dict[str, list[dict]] = defaultdict(list)
    for entry in file_index or []:
        if entry.get("source") == "memory":
            files_by_day[str(entry.get("date", ""))[:10]].append(entry)
    for day_files in files_by_day.values():
        day_files.sort(key=lambda entry: str(entry.get("new_name", "")))

    points = []
    for day, day_points in by_day.items():
        certain = _day_is_one_place(day_points)
        day_files = files_by_day.get(day, [])
        for position, point in enumerate(day_points):
            shown = day_files[position] if position < len(day_files) else None
            points.append({
                "lat": point["lat"],
                "lon": point["lon"],
                "t": point["t"],
                "kind": point["kind"],
                # False means the picture is a guess, the coordinate is not.
                "sure": certain,
                "thumb": (shown or {}).get("thumb", ""),
                "file": _relative_path(shown) if shown else "",
            })

    points.sort(key=lambda point: point["t"])
    return points


def _relative_path(entry: dict) -> str:
    subfolder = entry.get("subfolder") or entry.get("year") or "unknown"
    name = entry.get("new_name", "")
    return f"{subfolder}/{name}" if name else ""


def centre_of(points: list[dict]) -> tuple[float, float]:
    if not points:
        return 0.0, 0.0
    return (sum(point["lat"] for point in points) / len(points),
            sum(point["lon"] for point in points) / len(points))
