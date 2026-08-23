# The export is all UTC. This moves it to the timezone the archive was built for.

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC_NAME = "UTC"

# The only timestamp shape the export uses.
UTC_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC$")

# Offered in interactive mode. Anything zoneinfo knows can still be typed.
COMMON_ZONES = [
    # Europe
    "Europe/Vienna", "Europe/Berlin", "Europe/Zurich", "Europe/Paris",
    "Europe/Madrid", "Europe/Rome", "Europe/Amsterdam", "Europe/Brussels",
    "Europe/London", "Europe/Dublin", "Europe/Lisbon", "Europe/Stockholm",
    "Europe/Oslo", "Europe/Helsinki", "Europe/Warsaw", "Europe/Prague",
    "Europe/Budapest", "Europe/Bucharest", "Europe/Athens", "Europe/Istanbul",
    "Europe/Kyiv",
    # Russia, west to east
    "Europe/Moscow", "Asia/Yekaterinburg", "Asia/Novosibirsk", "Asia/Irkutsk",
    "Asia/Vladivostok",
    # The Americas
    "America/New_York", "America/Chicago", "America/Denver",
    "America/Los_Angeles", "America/Anchorage", "Pacific/Honolulu",
    "America/Toronto", "America/Vancouver", "America/Mexico_City",
    "America/Bogota", "America/Sao_Paulo", "America/Argentina/Buenos_Aires",
    # Asia and the Middle East
    "Asia/Jerusalem", "Asia/Dubai", "Asia/Karachi", "Asia/Kolkata",
    "Asia/Bangkok", "Asia/Singapore", "Asia/Hong_Kong", "Asia/Shanghai",
    "Asia/Seoul", "Asia/Tokyo", "Asia/Manila", "Asia/Jakarta",
    # Africa and Oceania
    "Africa/Cairo", "Africa/Lagos", "Africa/Nairobi", "Africa/Johannesburg",
    "Australia/Perth", "Australia/Brisbane", "Australia/Sydney",
    "Pacific/Auckland",
    UTC_NAME,
]


def is_known(name: str) -> bool:
    if not name or name == UTC_NAME:
        return True
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, ModuleNotFoundError):
        return False
    return True


def load_zone(name: str | None):
    # None for UTC, because then nothing has to be rewritten at all.
    if not name or name == UTC_NAME:
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, ModuleNotFoundError):
        return None


def convert_stamp(value: str, zone) -> str:
    # Drops the " UTC" suffix, because after the shift it would be a lie.
    match = UTC_STAMP.match(value)
    if not match:
        return value
    moment = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return moment.astimezone(zone).strftime("%Y-%m-%d %H:%M:%S")


def localize(data, zone):
    # Rewrites every stamp wherever it sits, beating a list of dozens of date fields.
    if zone is None:
        return data
    if isinstance(data, str):
        return convert_stamp(data, zone)
    if isinstance(data, dict):
        return {key: localize(value, zone) for key, value in data.items()}
    if isinstance(data, list):
        return [localize(value, zone) for value in data]
    return data
