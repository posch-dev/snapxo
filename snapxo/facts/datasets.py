# One definition of every chart and table, so the page, the info box and the
# spreadsheet can never disagree.

from .series import HOUR_LABELS, WEEKDAY_LABELS

# One paragraph per entry, the page makes each its own block.
EXPIRED_NOTE = [
    "Snapchat deletes messages after 24 hours.",
    "An export only has the messages that were saved, or that were still new when "
    "you asked for it. Everything else was already gone.",
    "Older months lost more than recent ones. That makes a line like this look like "
    "it is going up, even when you did not actually write more.",
]

UTC_NOTE = ("Every time in the export is UTC. Unless this archive was built with a "
            "timezone, the hours here are UTC too, not your local time.")


def _labelled(name: str, username: str) -> str:
    # A spreadsheet cell holds one value, so both names go in together.
    return f"{name} ({username})" if username else name


def _months_dataset(key: str, title: str, series: dict, values_key: str, column: str,
                    info: list[str]) -> dict:
    return {
        "key": key,
        "title": title,
        "columns": ["Month", column],
        "rows": [[month, count] for month, count in zip(series["months"], series[values_key], strict=False)],
        "info": info,
        "chart": "line",
    }


def stats_datasets(series: dict) -> list[dict]:
    if not series.get("months"):
        return []

    sets = [
        _months_dataset("messages-over-time", "Messages over time", series,
                        "messages_per_month", "Messages",
                        ["How many messages are in the archive each month."] + EXPIRED_NOTE),
        {
            "key": "activity-by-hour",
            "title": "Activity by time of day",
            "columns": ["Hour", "Messages"],
            "rows": [[label, count] for label, count in zip(HOUR_LABELS, series["messages_by_hour"], strict=False)],
            "info": ["Which hour of the day you were busiest.", UTC_NOTE] + EXPIRED_NOTE,
            "chart": "bar",
        },
        {
            "key": "activity-by-weekday",
            "title": "Activity by weekday",
            "columns": ["Weekday", "Messages"],
            "rows": [[label, count] for label, count in
                     zip(WEEKDAY_LABELS, series["messages_by_weekday"], strict=False)],
            "info": ["Which day of the week you were busiest.", UTC_NOTE] + EXPIRED_NOTE,
            "chart": "bar",
        },
        {
            "key": "snaps-over-time",
            "title": "Snaps over time",
            "columns": ["Month", "Sent", "Received"],
            "rows": [[month, sent, received] for month, sent, received in
                     zip(series["months"], series["snaps_sent_per_month"],
                         series["snaps_received_per_month"], strict=False)],
            "info": ["Snaps you sent and got, month by month.",
                     "This one comes from snap_history.json, which lists every snap even "
                     "if the picture itself is long gone.",
                     "So unlike the message charts, this one is complete."],
            "chart": "line",
        },
        {
            "key": "friends-over-time",
            "title": "Friends over time",
            "columns": ["Month", "Friends"],
            "rows": [[month, count] for month, count in
                     zip(series["months"], series["friends_per_month"], strict=False)],
            "info": ["How many friends you had over time.",
                     "Snapchat does not export this. It is worked out from the dates on your "
                     "friends list and your deleted friends list.",
                     "Anyone who is on neither list any more is missing from the count."],
            "chart": "line",
        },
        _months_dataset("chat-media-over-time", "Chat media over time", series,
                        "chat_media_per_month", "Files",
                        ["Messages that came with a photo, video or voice note."] + EXPIRED_NOTE),
    ]

    if any(series["story_views_per_month"]):
        sets.append(_months_dataset(
            "story-views-over-time", "Story views over time", series,
            "story_views_per_month", "Views",
            ["How often your own stories were watched, from the story history."],
        ))

    sets.append({
        "key": "who-writes-you-most",
        "title": "Who writes you most",
        "columns": ["Person", "Messages"],
        "rows": [[_labelled(name, username), count]
                 for name, username, count in series["top_senders"]],
        "info": ["Messages other people sent you, across all your chats.",
                 "Your own messages are not in this list. They are counted under the line at "
                 "the bottom, because otherwise you would be first by a mile."] + EXPIRED_NOTE,
        "chart": "",
    })
    sets.append({
        "key": "most-interacted-with",
        "title": "Most interacted with",
        "columns": ["Conversation", "Messages and snaps"],
        "rows": [[_labelled(name, username), count]
                 for name, username, count in series["most_interacted"]],
        "info": ["Your busiest conversations, messages and snaps added together.",
                 "This counts per chat, not per person. A group is one entry, however many "
                 "people are in it."],
        "chart": "",
    })
    sets.append({
        "key": "type-distribution",
        "title": "Type distribution",
        "columns": ["Type", "Count"],
        "rows": [[name, count] for name, count in series["type_distribution"]],
        "info": ["What this archive is made of.",
                 "Snaps are counted from the snap history, memories from the files you "
                 "saved. A snap you saved shows up in both."],
        "chart": "donut",
    })
    return sets


def numbers_dataset(card_values: list[tuple[str, object]]) -> dict:
    return {
        "key": "numbers",
        "title": "Numbers",
        "columns": ["Name", "Value"],
        "rows": [[label, value] for label, value in card_values],
        "info": ["Every number from the top of the Stats tab, in one table."],
        "chart": "",
    }
