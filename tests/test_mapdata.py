# How a memory is placed when Snapchat will not say where it belongs.

from snapxo.facts.mapdata import (
    SAME_PLACE_M,
    centre_of,
    distance_m,
    location_points,
    memory_points,
    parse_coordinates,
)


def _memory(date: str, lat: float, lon: float, kind: str = "Image") -> dict:
    return {"Date": date, "Media Type": kind,
            "Location": f"Latitude, Longitude: {lat}, {lon}"}


def test_a_plain_pair_of_coordinates_parses():
    assert parse_coordinates("48.12345, 16.54321") == (48.12345, 16.54321, 0.0)


def test_an_accuracy_suffix_does_not_break_it():
    # Snapchat writes some entries as "48.12345 ± 65.00 meters, ..."
    assert parse_coordinates("48.12345 \u00b1 65.00 meters, 16.54321 \u00b1 65.00 meters") == \
        (48.12345, 16.54321, 65.0)


def test_a_negative_coordinate_survives():
    assert parse_coordinates("-33.8, 151.2") == (-33.8, 151.2, 0.0)


def test_nonsense_and_null_island_are_dropped():
    assert parse_coordinates("somewhere nice") is None
    assert parse_coordinates("0, 0") is None
    assert parse_coordinates("48.1") is None


def test_the_accuracy_is_carried_to_the_point():
    data = {"location_history": {"Location History": [
        ["2026-05-04 10:00:00 UTC", "48.1 \u00b1 65.00 meters, 16.3 \u00b1 65.00 meters"],
        ["2026-05-04 11:00:00 UTC", "48.2, 16.4"],
    ]}}

    points = location_points(data)

    assert [point.get("acc") for point in points] == [65, None]


def test_locations_come_back_in_order():
    data = {"location_history": {"Location History": [
        ["2026-05-05 10:00:00 UTC", "48.2, 16.4"],
        ["2026-05-04 10:00:00 UTC", "48.1, 16.3"],
    ]}}

    assert [point["t"][:10] for point in location_points(data)] == ["2026-05-04", "2026-05-05"]


def test_a_day_saved_in_one_place_is_certain():
    data = {"memories_history": {"Saved Media": [
        _memory("2026-05-04 10:00:00 UTC", 48.1000, 16.3000),
        _memory("2026-05-04 11:00:00 UTC", 48.1005, 16.3005),
    ]}}

    assert all(point["sure"] for point in memory_points(data))


def test_a_day_saved_in_two_places_is_marked():
    data = {"memories_history": {"Saved Media": [
        _memory("2026-05-04 10:00:00 UTC", 48.1, 16.3),
        _memory("2026-05-04 11:00:00 UTC", 48.9, 16.9),
    ]}}

    assert not any(point["sure"] for point in memory_points(data))


def test_the_radius_that_decides_it_is_what_it_claims():
    assert distance_m(48.1, 16.3, 48.1, 16.3) == 0
    # a hundredth of a degree of latitude is a bit over a kilometre
    assert 1100 < distance_m(48.1, 16.3, 48.11, 16.3) < 1200
    assert distance_m(48.1, 16.3, 48.103, 16.3) > SAME_PLACE_M


def test_a_file_is_paired_to_a_memory_by_day_and_order():
    data = {"memories_history": {"Saved Media": [
        _memory("2026-05-04 10:00:00 UTC", 48.1, 16.3),
        _memory("2026-05-04 11:00:00 UTC", 48.1, 16.3),
    ]}}
    file_index = [
        {"source": "memory", "date": "2026-05-04", "new_name": "b.jpg",
         "subfolder": "2026", "thumb": "_meta/thumbs/b.jpg"},
        {"source": "memory", "date": "2026-05-04", "new_name": "a.jpg",
         "subfolder": "2026", "thumb": "_meta/thumbs/a.jpg"},
    ]

    points = memory_points(data, file_index)

    assert [point["file"] for point in points] == ["2026/a.jpg", "2026/b.jpg"]


def test_a_memory_without_a_file_still_gets_its_place():
    data = {"memories_history": {"Saved Media": [_memory("2026-05-04 10:00:00 UTC", 48.1, 16.3)]}}

    point = memory_points(data, [])[0]

    assert point["lat"] == 48.1 and point["file"] == "" and point["thumb"] == ""


def test_an_export_with_no_coordinates_produces_nothing():
    assert location_points({}) == []
    assert memory_points({}) == []
    assert centre_of([]) == (0.0, 0.0)


def test_the_centre_is_the_middle_of_the_points():
    assert centre_of([{"lat": 0, "lon": 0}, {"lat": 10, "lon": 20}]) == (5.0, 10.0)
