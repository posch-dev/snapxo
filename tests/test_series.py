# Chart numbers computed from raw export JSON.

from snapxo.facts.series import (
    build_series,
    counts_by_hour,
    counts_by_weekday,
    friend_headcount_by_month,
    month_of,
    months_between,
    year_tick_marks,
)


def _chat_json(messages: list[dict]) -> dict:
    return {"chat_history": {"friend_one": messages}}


def _message(created: str, media_type: str = "TEXT", sender: str = "friend_one", media_ids: str = "") -> dict:
    return {"From": sender, "Media Type": media_type, "Created": created,
            "IsSender": sender == "testuser", "Media IDs": media_ids}


def test_months_between_fills_the_gaps():
    assert months_between("2025-11", "2026-02") == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_months_between_handles_a_single_month():
    assert months_between("2026-05", "2026-05") == ["2026-05"]


def test_month_of_rejects_junk():
    assert month_of("not a date") == ""
    assert month_of("") == ""
    assert month_of("2026-05-04 10:00:00 UTC") == "2026-05"


def test_year_ticks_mark_the_first_month_of_each_year():
    assert year_tick_marks(["2025-11", "2025-12", "2026-01"]) == [(0, "2025"), (2, "2026")]


def test_hours_and_weekdays_are_bucketed():
    # 2026-05-04 was a Monday
    stamps = ["2026-05-04 09:15:00 UTC", "2026-05-04 09:45:00 UTC", "2026-05-05 22:00:00 UTC"]

    assert counts_by_hour(stamps)[9] == 2
    assert counts_by_hour(stamps)[22] == 1
    assert counts_by_weekday(stamps)[0] == 2
    assert counts_by_weekday(stamps)[1] == 1


def test_unparseable_timestamps_are_dropped_not_counted_as_zero():
    assert sum(counts_by_hour(["", "nonsense", "2026-05-04 09:00:00 UTC"])) == 1
    assert sum(counts_by_weekday(["", "nonsense", "2026-05-04 09:00:00 UTC"])) == 1


def test_status_messages_are_left_out_of_the_totals():
    data = _chat_json([
        _message("2026-05-04 10:00:00 UTC"),
        _message("2026-05-04 10:01:00 UTC", media_type="STATUSCALLMISSEDAUDIO"),
    ])

    assert build_series(data)["total_messages"] == 1


def test_snaps_are_split_by_direction():
    data = {"snap_history": {"friend_one": [
        {"From": "friend_one", "Media Type": "IMAGE", "Created": "2026-05-04 10:00:00 UTC", "IsSender": False},
        {"From": "testuser", "Media Type": "VIDEO", "Created": "2026-05-04 11:00:00 UTC", "IsSender": True},
    ]}}

    series = build_series(data)

    assert series["total_snaps"] == 2
    assert series["snaps_sent"] == 1
    assert series["snaps_received"] == 1


def test_only_messages_carrying_media_count_as_chat_media():
    data = _chat_json([
        _message("2026-05-04 10:00:00 UTC"),
        _message("2026-05-04 10:01:00 UTC", media_type="MEDIA", media_ids="mediaidone"),
    ])

    assert sum(build_series(data)["chat_media_per_month"]) == 1


def test_the_friend_curve_ends_at_the_current_friend_count():
    data = {
        "chat_history": {"friend_one": [_message("2026-01-04 10:00:00 UTC")]},
        "friends": {"Friends": [
            {"Username": "a", "Creation Timestamp": "2025-03-01 10:00:00 UTC"},
            {"Username": "b", "Creation Timestamp": "2026-01-02 10:00:00 UTC"},
        ]},
    }

    assert build_series(data)["friends_per_month"][-1] == 2


def test_friends_added_before_the_first_month_are_the_starting_headcount():
    data = {"friends": {"Friends": [{"Username": "a", "Creation Timestamp": "2019-01-01 10:00:00 UTC"}]}}

    assert friend_headcount_by_month(data, ["2026-05", "2026-06"]) == [1, 1]


def test_a_deleted_friend_drops_out_again():
    data = {"friends": {"Friends": [], "Deleted Friends": [{
        "Username": "a",
        "Creation Timestamp": "2026-05-01 10:00:00 UTC",
        "Last Modified Timestamp": "2026-06-01 10:00:00 UTC",
    }]}}

    assert friend_headcount_by_month(data, ["2026-05", "2026-06", "2026-07"]) == [1, 0, 0]


def test_memories_come_from_the_file_index_not_the_chat_history():
    file_index = [{"source": "memory", "type": "image"}, {"source": "chat", "type": "image"}]

    distribution = dict(build_series(_chat_json([]), file_index)["type_distribution"])

    assert distribution["Memories"] == 1


def test_most_interacted_adds_messages_and_snaps_of_the_same_partner():
    data = {
        "chat_history": {"friend_one": [_message("2026-05-04 10:00:00 UTC")]},
        "snap_history": {"friend_one": [
            {"From": "friend_one", "Media Type": "IMAGE", "Created": "2026-05-04 11:00:00 UTC", "IsSender": False},
        ]},
    }

    assert build_series(data)["most_interacted"] == [("friend_one", "", 2)]


def test_an_empty_export_produces_empty_series_without_raising():
    series = build_series({})

    assert series["months"] == []
    assert series["total_messages"] == 0
    assert series["friends_per_month"] == []


def test_top_senders_leaves_your_own_messages_out():
    data = _chat_json([
        _message("2026-05-04 10:00:00 UTC", sender="friend_one"),
        _message("2026-05-04 10:01:00 UTC", sender="testuser"),
        _message("2026-05-04 10:02:00 UTC", sender="testuser"),
    ])

    series = build_series(data)

    # (display name, username, count); no display name means no username shown
    assert series["top_senders"] == [("friend_one", "", 1)]
    assert series["own_messages"] == 2


def test_snaps_and_memories_stay_separate():
    file_index = [{"source": "memory", "type": "image"}]
    data = {"snap_history": {"friend_one": [
        {"From": "friend_one", "Media Type": "IMAGE",
         "Created": "2026-05-04 10:00:00 UTC", "IsSender": False},
    ]}}

    distribution = dict(build_series(data, file_index)["type_distribution"])

    assert distribution["Snaps"] == 1
    assert distribution["Memories"] == 1


def test_the_newest_data_point_covers_messages_and_media():
    data = _chat_json([_message("2026-05-04 10:00:00 UTC")])
    file_index = [{"date": "2026-07-30", "source": "memory", "type": "image"}]

    assert build_series(data, file_index)["newest_data"] == "2026-07-30"


def test_an_empty_export_has_no_newest_data_point():
    assert build_series({})["newest_data"] == ""


def test_a_display_name_keeps_the_username_beside_it():
    data = {
        "chat_history": {"friend_one": [_message("2026-05-04 10:00:00 UTC")]},
        "friends": {"Friends": [{"Username": "friend_one", "Display Name": "Alice"}]},
    }

    assert build_series(data)["top_senders"] == [("Alice", "friend_one", 1)]
