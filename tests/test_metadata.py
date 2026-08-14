from pathlib import Path

import pytest
from conftest import write_image

from snapxo.metadata import _decimal_to_dms, _parse_location_string, apply_gps_metadata, write_exif_gps


@pytest.mark.parametrize("text,expected", [
    ("Latitude, Longitude: 48.2, 16.3", (48.2, 16.3)),
    ("Latitude, Longitude: -48.87667, -123.39333", (-48.87667, -123.39333)),
    ("Latitude,Longitude:48.2,16.3", (48.2, 16.3)),
])
def test_parses_snapchat_location_strings(text, expected):
    assert _parse_location_string(text) == expected


def test_null_island_is_treated_as_no_location():
    # Snapchat writes 0,0 for entries it has no position for.
    assert _parse_location_string("Latitude, Longitude: 0.0, 0.0") is None


@pytest.mark.parametrize("text", ["", "somewhere", "Latitude, Longitude: n/a, n/a"])
def test_unparseable_locations_return_none(text):
    assert _parse_location_string(text) is None


def test_decimal_to_dms_splits_degrees_minutes_seconds():
    assert _decimal_to_dms(48.5) == ((48, 1), (30, 1), (0, 100))


def test_decimal_to_dms_uses_the_absolute_value():
    assert _decimal_to_dms(-48.5) == _decimal_to_dms(48.5)


def test_write_exif_gps_on_a_jpeg(tmp_path: Path):
    f = write_image(tmp_path / "a.jpg", "red")

    assert write_exif_gps(f, 48.2, 16.3, "2026-05-01") is True

    import piexif
    gps = piexif.load(str(f))["GPS"]
    assert gps[piexif.GPSIFD.GPSLatitudeRef] == b"N"
    assert gps[piexif.GPSIFD.GPSLongitudeRef] == b"E"


def test_write_exif_gps_records_the_southern_and_western_hemisphere(tmp_path: Path):
    f = write_image(tmp_path / "a.jpg", "red")

    write_exif_gps(f, -48.87667, -123.39333, "2026-05-01")

    import piexif
    gps = piexif.load(str(f))["GPS"]
    assert gps[piexif.GPSIFD.GPSLatitudeRef] == b"S"
    assert gps[piexif.GPSIFD.GPSLongitudeRef] == b"W"


def test_write_exif_gps_declines_unsupported_types(tmp_path: Path):
    f = tmp_path / "a.mp4"
    f.write_bytes(b"not an image")

    assert write_exif_gps(f, 48.2, 16.3) is False


def index_entry(tmp_path: Path, date: str, source: str = "memory", kind: str = "image") -> dict:
    dest = write_image(tmp_path / f"{date}.jpg", "red")
    return {"date": date, "type": kind, "source": source, "dest": str(dest)}


def test_gps_is_matched_to_images_by_date(tmp_path: Path):
    index = [index_entry(tmp_path, "2026-05-01")]
    history = [{"Date": "2026-05-01 12:00:00 UTC", "Location": "Latitude, Longitude: 48.2, 16.3"}]

    assert apply_gps_metadata(index, history) == 1


def test_images_without_a_matching_date_are_left_alone(tmp_path: Path):
    index = [index_entry(tmp_path, "2026-05-09")]
    history = [{"Date": "2026-05-01 12:00:00 UTC", "Location": "Latitude, Longitude: 48.2, 16.3"}]

    assert apply_gps_metadata(index, history) == 0


def test_videos_and_chat_media_are_skipped(tmp_path: Path):
    history = [{"Date": "2026-05-01 12:00:00 UTC", "Location": "Latitude, Longitude: 48.2, 16.3"}]

    video = [{"date": "2026-05-01", "type": "video", "source": "memory", "dest": "x.mp4"}]
    chat = [index_entry(tmp_path, "2026-05-01", source="chat")]

    assert apply_gps_metadata(video, history) == 0
    assert apply_gps_metadata(chat, history) == 0


def test_dry_run_counts_without_touching_files(tmp_path: Path):
    index = [index_entry(tmp_path, "2026-05-01")]
    before = Path(index[0]["dest"]).read_bytes()
    history = [{"Date": "2026-05-01 12:00:00 UTC", "Location": "Latitude, Longitude: 48.2, 16.3"}]

    assert apply_gps_metadata(index, history, dry_run=True) == 1
    assert Path(index[0]["dest"]).read_bytes() == before


def test_file_dates_come_from_the_capture_date(tmp_path):
    from datetime import datetime

    from snapxo.metadata import apply_file_times

    media = tmp_path / "2026" / "2026-05-01_0001.jpg"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"data")
    entry = {"dest": str(media), "date": "2026-05-01"}

    assert apply_file_times([entry]) == 1

    stamp = datetime.fromtimestamp(media.stat().st_mtime)
    assert (stamp.year, stamp.month, stamp.day) == (2026, 5, 1)


def test_undated_and_missing_files_are_left_alone(tmp_path):
    from snapxo.metadata import apply_file_times

    media = tmp_path / "a.jpg"
    media.write_bytes(b"data")
    before = media.stat().st_mtime_ns

    assert apply_file_times([{"dest": str(media), "date": ""},
                             {"dest": str(tmp_path / "gone.jpg"), "date": "2026-05-01"}]) == 0
    assert media.stat().st_mtime_ns == before
