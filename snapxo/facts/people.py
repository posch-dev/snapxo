# Usernames to the names you know, and a readable name for an untitled group.

FRIEND_SECTIONS = (
    "Friends",
    "Deleted Friends",
    "Blocked Users",
    "Friend Requests Sent",
    "Pending Requests",
    "Ignored Snapchatters",
)

NAMED_PARTICIPANTS = 3


def display_names(json_data: dict) -> dict[str, str]:
    # All friend lists at once: a deleted friend still had a display name.
    friends = json_data.get("friends")
    if not isinstance(friends, dict):
        return {}

    names: dict[str, str] = {}
    for section in FRIEND_SECTIONS:
        for entry in friends.get(section, []):
            if not isinstance(entry, dict):
                continue
            username = entry.get("Username")
            shown = str(entry.get("Display Name") or "").strip()
            if username and shown and username not in names:
                names[username] = shown
    return names


def name_for(username: str, names: dict[str, str]) -> str:
    return names.get(username) or username


def participants_of(messages: list[dict], own_username: str | None) -> list[str]:
    seen = []
    for message in messages:
        sender = message.get("sender")
        if sender and sender != own_username and sender not in seen:
            seen.append(sender)
    return seen


def group_name(participants: list[str], names: dict[str, str]) -> str:
    # A group Snapchat never titled would otherwise show its raw id.
    if not participants:
        return "Group chat"
    shown = [name_for(username, names) for username in participants[:NAMED_PARTICIPANTS]]
    remaining = len(participants) - len(shown)
    if remaining > 0:
        return f"{', '.join(shown)} and {remaining} more"
    if len(shown) == 1:
        return shown[0]
    return f"{', '.join(shown[:-1])} and {shown[-1]}"
