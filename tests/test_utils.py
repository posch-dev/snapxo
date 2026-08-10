from pathlib import Path

import pytest

from snapxo.utils import (
    extract_date_from_filename,
    extract_media_id,
    extract_uuid_from_name,
    file_hash,
    format_size,
    is_image,
    is_video,
    safe_filename,
)


def test_file_hash_matches_for_identical_content(tmp_path: Path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"snapxo" * 1000)
    b.write_bytes(b"snapxo" * 1000)
    assert file_hash(a) == file_hash(b)


def test_file_hash_differs_for_different_content(tmp_path: Path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"one")
    b.write_bytes(b"two")
    assert file_hash(a) != file_hash(b)


def test_file_hash_reads_across_chunk_boundaries(tmp_path: Path):
    # The reader loops in 64 KB chunks, so a file larger than one chunk has to
    # produce the same digest as reading it in one go.
    f = tmp_path / "big.bin"
    f.write_bytes(bytes(range(256)) * 1000)
    assert file_hash(f, chunk_size=7) == file_hash(f, chunk_size=1 << 20)


@pytest.mark.parametrize("size,expected", [
    (0, "0 B"),
    (512, "512 B"),
    (1024, "1.0 KB"),
    (1024 * 1024, "1.0 MB"),
    (1024 * 1024 * 1024, "1.00 GB"),
])
def test_format_size(size, expected):
    assert format_size(size) == expected


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
    # Media IDs are base64-ish and the extension is only the last dot group.
    assert extract_media_id("2026-07-20_b~with.dots.jpg") == "b~with.dots"


def test_extract_media_id_without_date_prefix():
    assert extract_media_id("plain.jpg") is None


@pytest.mark.parametrize("name", ["a.JPG", "a.jpeg", "a.png", "a.webp", "a.avif"])
def test_is_image(name):
    assert is_image(Path(name))


@pytest.mark.parametrize("name", ["a.mp4", "a.MOV"])
def test_is_video(name):
    assert is_video(Path(name))


def test_mp3_is_neither_image_nor_video():
    assert not is_image(Path("a.mp3"))
    assert not is_video(Path("a.mp3"))


def test_safe_filename_replaces_reserved_characters():
    assert safe_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_safe_filename_leaves_ordinary_names_alone():
    assert safe_filename("john-doe_2026.html") == "john-doe_2026.html"
