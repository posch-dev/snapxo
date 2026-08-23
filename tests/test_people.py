# Display names, and naming a group that Snapchat never gave a title.

from snapxo.facts.people import display_names, group_name, name_for
from snapxo.pages.conversations import prepare_conversations


def _friends(**sections) -> dict:
    return {"friends": dict(sections)}


def _named(username: str, shown: str) -> dict:
    return {"Username": username, "Display Name": shown}


def _message(sender: str, own: bool = False, title: str | None = None) -> dict:
    return {"From": sender, "IsSender": own, "Media Type": "TEXT",
            "Created": "2026-05-04 10:00:00 UTC", "Content": "hey",
            "Conversation Title": title}


def test_names_come_from_every_friend_list():
    data = _friends(
        Friends=[_named("a", "Alice")],
        **{"Deleted Friends": [_named("b", "Bob")], "Blocked Users": [_named("c", "Carol")]},
    )

    names = display_names(data)

    assert names == {"a": "Alice", "b": "Bob", "c": "Carol"}


def test_an_unknown_username_stays_itself():
    assert name_for("stranger", {"a": "Alice"}) == "stranger"


def test_an_empty_display_name_is_ignored():
    assert display_names(_friends(Friends=[_named("a", "   ")])) == {}


def test_a_group_without_a_title_is_named_after_its_people():
    assert group_name(["a", "b"], {"a": "Alice", "b": "Bob"}) == "Alice and Bob"


def test_a_big_group_counts_the_rest():
    names = {"a": "Alice", "b": "Bob", "c": "Carol"}

    assert group_name(["a", "b", "c", "d", "e"], names) == "Alice, Bob, Carol and 2 more"


def test_a_group_with_nobody_left_still_has_a_name():
    assert group_name([], {}) == "Group chat"


def test_a_one_to_one_chat_shows_the_display_name_with_the_username():
    data = {
        "chat_history": {"friend_one": [_message("friend_one")]},
        "friends": {"Friends": [_named("friend_one", "Alice")]},
    }

    prepared, _ = prepare_conversations(data)

    assert prepared[0]["title"] == "Alice"
    assert prepared[0]["secondary"] == "friend_one"
    assert prepared[0]["is_group"] is False


def test_without_a_display_name_only_the_username_shows():
    data = {"chat_history": {"friend_one": [_message("friend_one")]}}

    prepared, _ = prepare_conversations(data)

    assert prepared[0]["title"] == "friend_one"
    assert prepared[0]["secondary"] == ""


def test_a_renamed_contact_is_not_mistaken_for_a_group():
    # Two sender names, no conversation title: one person who renamed themselves.
    data = {"chat_history": {"friend_one": [_message("old_name"), _message("new_name")]}}

    prepared, _ = prepare_conversations(data)

    assert prepared[0]["is_group"] is False


def test_several_senders_with_a_title_are_a_group():
    data = {"chat_history": {"the_chat": [
        _message("a", title="Weekend"), _message("b", title="Weekend"),
    ]}}

    prepared, _ = prepare_conversations(data)

    assert prepared[0]["is_group"] is True
    assert prepared[0]["title"] == "Weekend"


def test_a_uuid_keyed_chat_is_always_a_group():
    data = {"chat_history": {"b2dea96e-c73e-4232-bb20-88f0e1377a45": [_message("a")]}}

    prepared, _ = prepare_conversations(data)

    assert prepared[0]["is_group"] is True


def test_an_untitled_group_is_named_after_its_members():
    data = {
        "chat_history": {"b2dea96e-c73e-4232-bb20-88f0e1377a45": [_message("a"), _message("b")]},
        "friends": {"Friends": [_named("a", "Alice"), _named("b", "Bob")]},
    }

    prepared, _ = prepare_conversations(data)

    assert prepared[0]["title"] == "Alice and Bob"
    assert prepared[0]["secondary"] == "2 people"
