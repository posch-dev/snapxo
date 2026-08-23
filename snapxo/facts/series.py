from collections import Counter
from datetime import date

from ..snapchat import STATUS_TYPES
from .people import display_names, name_for

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOUR_LABELS = [f"{hour:02d}" for hour in range(24)]
TOP_LIST_LENGTH = 10


def month_of(timestamp: str) -> str:
    return timestamp[:7] if len(timestamp) >= 7 and timestamp[4] == "-" else ""


def hour_of(timestamp: str) -> int | None:
    if len(timestamp) < 13 or timestamp[10] != " ":
        return None
    try:
        return int(timestamp[11:13])
    except ValueError:
        return None


def weekday_of(timestamp: str) -> int | None:
    try:
        return date(int(timestamp[:4]), int(timestamp[5:7]), int(timestamp[8:10])).weekday()
    except (ValueError, IndexError):
        return None


def months_between(first: str, last: str) -> list[str]:
    # First to last inclusive, so a gap stays visible as a gap.
    if not first or not last:
        return []
    year, month = int(first[:4]), int(first[5:7])
    end_year, end_month = int(last[:4]), int(last[5:7])
    months = []
    while (year, month) <= (end_year, end_month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return months


def monthly_counts(timestamps: list[str], months: list[str]) -> list[int]:
    counted = Counter(month_of(stamp) for stamp in timestamps)
    return [counted.get(month, 0) for month in months]


def year_tick_marks(months: list[str]) -> list[tuple[int, str]]:
    marks = []
    seen_years = set()
    for index, month in enumerate(months):
        year = month[:4]
        if year not in seen_years:
            seen_years.add(year)
            marks.append((index, year))
    return marks


def counts_by_hour(timestamps: list[str]) -> list[int]:
    counted = Counter(hour for hour in (hour_of(s) for s in timestamps) if hour is not None)
    return [counted.get(hour, 0) for hour in range(24)]


def counts_by_weekday(timestamps: list[str]) -> list[int]:
    counted = Counter(day for day in (weekday_of(s) for s in timestamps) if day is not None)
    return [counted.get(day, 0) for day in range(7)]


def chat_messages(json_data: dict) -> list[dict]:
    chat_history = json_data.get("chat_history")
    if not isinstance(chat_history, dict):
        return []
    messages = []
    for entries in chat_history.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get("Media Type", "")).upper() not in STATUS_TYPES:
                messages.append(entry)
    return messages


def snap_entries(json_data: dict) -> list[dict]:
    snap_history = json_data.get("snap_history")
    if not isinstance(snap_history, dict):
        return []
    entries = []
    for partner_entries in snap_history.values():
        if isinstance(partner_entries, list):
            entries.extend(entry for entry in partner_entries if isinstance(entry, dict))
    return entries


def friend_headcount_by_month(json_data: dict, months: list[str]) -> list[int]:
    # Counted from when they were added, deleted ones dropping out again on their
    # last change. The closest the export gets to a running total.
    friends = json_data.get("friends")
    if not isinstance(friends, dict) or not months:
        return []

    added = Counter()
    removed = Counter()
    for entry in friends.get("Friends", []):
        if isinstance(entry, dict):
            added[month_of(entry.get("Creation Timestamp", ""))] += 1
    for entry in friends.get("Deleted Friends", []):
        if not isinstance(entry, dict):
            continue
        added[month_of(entry.get("Creation Timestamp", ""))] += 1
        removed[month_of(entry.get("Last Modified Timestamp", ""))] += 1

    # The starting headcount, or the curve begins at zero and never catches up.
    first_month = months[0]
    running = (sum(count for month, count in added.items() if month and month < first_month)
               - sum(count for month, count in removed.items() if month and month < first_month))

    headcount = []
    for month in months:
        running += added.get(month, 0) - removed.get(month, 0)
        headcount.append(max(running, 0))
    return headcount


def story_view_timestamps(json_data: dict) -> list[str]:
    story_history = json_data.get("story_history")
    if not isinstance(story_history, dict):
        return []
    return [entry.get("Story Date", "") for entry in story_history.get("Your Story Views", [])
            if isinstance(entry, dict)]


def message_type_counts(messages: list[dict], snaps: list[dict], file_index: list[dict]) -> list[tuple[str, int]]:
    by_type = Counter(str(message.get("Media Type", "")).upper() for message in messages)
    memories = sum(1 for entry in file_index if entry.get("source") == "memory")
    return [
        ("Text", by_type.get("TEXT", 0)),
        ("Snaps", len(snaps)),
        ("Memories", memories),
        ("Chat media", by_type.get("MEDIA", 0)),
        ("Voice notes", by_type.get("NOTE", 0)),
    ]


def _ranked(counted: list[tuple[str, int]], names: dict[str, str]) -> list[tuple[str, str, int]]:
    # Name and username stay separate, so a page can print the username small.
    ranked = []
    for username, count in counted:
        shown = name_for(username, names)
        ranked.append((shown, "" if shown == username else username, count))
    return ranked


def top_senders(messages: list[dict], names: dict[str, str] | None = None) -> list[tuple[str, str, int]]:
    # Your own messages would take first place by a mile and say nothing.
    counted = Counter(message.get("From", "") for message in messages
                      if message.get("From") and not message.get("IsSender"))
    return _ranked(counted.most_common(TOP_LIST_LENGTH), names or {})


def own_message_total(messages: list[dict]) -> int:
    return sum(1 for message in messages if message.get("IsSender"))


def most_interacted(json_data: dict, names: dict[str, str] | None = None) -> list[tuple[str, str, int]]:
    totals = Counter()
    chat_history = json_data.get("chat_history")
    if isinstance(chat_history, dict):
        for partner, entries in chat_history.items():
            if isinstance(entries, list):
                totals[partner] += sum(
                    1 for entry in entries
                    if isinstance(entry, dict)
                    and str(entry.get("Media Type", "")).upper() not in STATUS_TYPES
                )
    snap_history = json_data.get("snap_history")
    if isinstance(snap_history, dict):
        for partner, entries in snap_history.items():
            if isinstance(entries, list):
                totals[partner] += len(entries)
    return _ranked(totals.most_common(TOP_LIST_LENGTH), names or {})


def newest_timestamp(timestamps: list[str], file_index: list[dict]) -> str:
    days = {stamp[:10] for stamp in timestamps if len(stamp) >= 10}
    days |= {str(entry.get("date", ""))[:10] for entry in file_index}
    days.discard("")
    return max(days) if days else ""


def build_series(json_data: dict, file_index: list[dict] | None = None) -> dict:
    file_index = file_index or []
    names = display_names(json_data)
    messages = chat_messages(json_data)
    snaps = snap_entries(json_data)

    message_times = [message.get("Created", "") for message in messages]
    media_times = [message.get("Created", "") for message in messages
                   if (message.get("Media IDs") or "").strip()]
    sent_snap_times = [snap.get("Created", "") for snap in snaps if snap.get("IsSender")]
    received_snap_times = [snap.get("Created", "") for snap in snaps if not snap.get("IsSender")]
    story_times = story_view_timestamps(json_data)

    all_months = sorted({month_of(stamp) for stamp in
                         message_times + sent_snap_times + received_snap_times + story_times} - {""})
    months = months_between(all_months[0], all_months[-1]) if all_months else []

    return {
        "months": months,
        "year_ticks": year_tick_marks(months),
        "messages_per_month": monthly_counts(message_times, months),
        "chat_media_per_month": monthly_counts(media_times, months),
        "snaps_sent_per_month": monthly_counts(sent_snap_times, months),
        "snaps_received_per_month": monthly_counts(received_snap_times, months),
        "friends_per_month": friend_headcount_by_month(json_data, months),
        "story_views_per_month": monthly_counts(story_times, months),
        "messages_by_hour": counts_by_hour(message_times),
        "messages_by_weekday": counts_by_weekday(message_times),
        "type_distribution": message_type_counts(messages, snaps, file_index),
        "top_senders": top_senders(messages, names),
        "own_messages": own_message_total(messages),
        "most_interacted": most_interacted(json_data, names),
        "newest_data": newest_timestamp(message_times + sent_snap_times
                                        + received_snap_times + story_times, file_index),
        "total_messages": len(messages),
        "total_chats": len(json_data.get("chat_history") or {}),
        "total_snaps": len(snaps),
        "snaps_sent": len(sent_snap_times),
        "snaps_received": len(received_snap_times),
    }
