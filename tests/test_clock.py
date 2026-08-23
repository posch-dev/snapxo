# Turning the export's UTC timestamps into the archive's timezone.

from snapxo.clock import convert_stamp, is_known, load_zone, localize


def _vienna():
    return load_zone("Europe/Vienna")


def test_utc_needs_no_zone_at_all():
    assert load_zone("") is None
    assert load_zone("UTC") is None


def test_an_unknown_zone_is_rejected():
    assert is_known("Middle/Earth") is False
    assert load_zone("Middle/Earth") is None
    assert is_known("Europe/Vienna") is True


def test_summer_time_shifts_by_two_hours():
    assert convert_stamp("2026-07-20 20:00:00 UTC", _vienna()) == "2026-07-20 22:00:00"


def test_winter_time_shifts_by_one():
    assert convert_stamp("2026-01-20 20:00:00 UTC", _vienna()) == "2026-01-20 21:00:00"


def test_a_late_message_moves_to_the_next_day():
    assert convert_stamp("2026-07-20 23:30:00 UTC", _vienna()) == "2026-07-21 01:30:00"


def test_anything_that_is_not_a_timestamp_is_left_alone():
    zone = _vienna()

    assert convert_stamp("hello", zone) == "hello"
    assert convert_stamp("2026-07-20", zone) == "2026-07-20"
    assert convert_stamp("", zone) == ""


def test_every_timestamp_in_the_export_is_converted_wherever_it_sits():
    data = {
        "chat_history": {"friend_one": [{"Created": "2026-07-20 20:00:00 UTC", "Content": "hey"}]},
        "location_history": {"Location History": [["2026-07-20 20:00:00 UTC", "48.2, 16.3"]]},
    }

    localized = localize(data, _vienna())

    assert localized["chat_history"]["friend_one"][0]["Created"] == "2026-07-20 22:00:00"
    assert localized["location_history"]["Location History"][0][0] == "2026-07-20 22:00:00"
    assert localized["chat_history"]["friend_one"][0]["Content"] == "hey"


def test_without_a_zone_the_data_comes_back_untouched():
    data = {"chat_history": {"a": [{"Created": "2026-07-20 20:00:00 UTC"}]}}

    assert localize(data, None) is data
