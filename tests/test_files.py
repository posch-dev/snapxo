from pathlib import Path

import pytest

from snapxo.files import file_hash, format_size


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
    file = tmp_path / "big.bin"
    file.write_bytes(bytes(range(256)) * 1000)
    assert file_hash(file, chunk_size=7) == file_hash(file, chunk_size=1 << 20)


@pytest.mark.parametrize("size,expected", [
    (0, "0 B"),
    (512, "512 B"),
    (1024, "1.0 KB"),
    (1024 * 1024, "1.0 MB"),
    (1024 * 1024 * 1024, "1.00 GB"),
])
def test_format_size(size, expected):
    assert format_size(size) == expected


def test_format_size_says_unknown_for_a_missing_number():
    assert format_size(None) == "unknown"
