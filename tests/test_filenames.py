import pytest

from snapxo.filenames import (
    extract_date_from_filename,
    extract_media_id,
    extract_uuid_from_name,
    safe_filename,
)


@pytest.mark.parametrize("name,expected", [
    ("2026-05-08_0444.mp4", "2026-05-08"),
    ("2026-05-08_b~someid.jpg", "2026-05-08"),
    ("no-date-here.jpg", None),
    ("20260508_0444.mp4", None),
])
def test_extract_date_from_filename(name, expected):
    assert extract_date_from_filename(name) == expected


def test_extract_uuid_from_name():
    name = "2026-05-05_1200-11111111-2222-3333-4444-555555555555-media.mp4"
    assert extract_uuid_from_name(name) == "11111111-2222-3333-4444-555555555555"


def test_extract_uuid_returns_none_without_one():
    assert extract_uuid_from_name("2026-05-05_1200-media.mp4") is None


def test_extract_media_id_strips_date_and_extension():
    assert extract_media_id("2026-07-20_b~EiASFXhhbXBsZQ.jpg") == "b~EiASFXhhbXBsZQ"


def test_extract_media_id_keeps_dots_inside_the_id():
    assert extract_media_id("2026-07-20_b~with.dots.jpg") == "b~with.dots"


def test_extract_media_id_without_date_prefix():
    assert extract_media_id("plain.jpg") is None


def test_safe_filename_replaces_reserved_characters():
    assert safe_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_safe_filename_leaves_ordinary_names_alone():
    assert safe_filename("john-doe_2026.html") == "john-doe_2026.html"
