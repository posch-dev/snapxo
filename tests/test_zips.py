import zipfile

from snapxo.read.zips import (
    RATIO_MIN_UNCOMPRESSED,
    looks_like_zip_bomb,
    safe_extract,
    zip_payload,
)


def _zip_with(tmp_path, entries):
    path = tmp_path / "export.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries:
            zf.writestr(name, content)
    return path


def test_normal_entries_are_extracted(tmp_path):
    src = _zip_with(tmp_path, [("json/chat_history.json", "{}"), ("memories/a.jpg", "data")])
    dest = tmp_path / "out"
    dest.mkdir()

    written, problems = safe_extract(src, dest)

    assert written == 2
    assert problems == []
    assert (dest / "json" / "chat_history.json").read_text() == "{}"


def test_traversal_entries_are_refused(tmp_path):
    src = _zip_with(tmp_path, [
        ("../escaped.txt", "nope"),
        ("json/../../escaped2.txt", "nope"),
        ("json/ok.json", "{}"),
    ])
    dest = tmp_path / "out"
    dest.mkdir()

    written, problems = safe_extract(src, dest)

    assert written == 1
    assert {p["reason"] for p in problems} == {"path traversal"}
    assert not (tmp_path / "escaped.txt").exists()
    assert not (tmp_path / "escaped2.txt").exists()


def test_absolute_entries_are_refused(tmp_path):
    src = _zip_with(tmp_path, [("/etc/passwd", "nope"), ("C:\\Windows\\evil.dll", "nope")])
    dest = tmp_path / "out"
    dest.mkdir()

    written, problems = safe_extract(src, dest)

    assert written == 0
    assert {p["reason"] for p in problems} == {"absolute path"}


def test_a_broken_entry_costs_only_that_file(tmp_path):
    src = _zip_with(tmp_path, [("json/ok.json", "{}"), ("memories/bad.jpg", "x" * 500)])
    # Corrupt the stored bytes so the CRC no longer matches the header.
    raw = bytearray(src.read_bytes())
    marker = raw.find(b"x" * 500)
    raw[marker:marker + 10] = b"y" * 10
    src.write_bytes(bytes(raw))

    dest = tmp_path / "out"
    dest.mkdir()
    written, problems = safe_extract(src, dest)

    assert written == 1
    assert (dest / "json" / "ok.json").exists()
    assert len(problems) == 1
    assert problems[0]["entry"] == "memories/bad.jpg"
    assert not (dest / "memories" / "bad.jpg").exists()


def test_payload_is_read_without_extracting(tmp_path):
    src = tmp_path / "export.zip"
    with zipfile.ZipFile(src, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("json/a.json", "a" * 1000)

    uncompressed, compressed = zip_payload(src)

    assert uncompressed == 1000
    assert compressed < uncompressed


# The check reads two numbers from the central directory, so no disk is filled.
def test_a_real_export_is_not_mistaken_for_a_bomb():
    # 6 GB of already compressed media barely shrinks
    assert not looks_like_zip_bomb(6 * 1024 ** 3, int(5.9 * 1024 ** 3))


def test_a_small_archive_is_never_refused():
    assert not looks_like_zip_bomb(RATIO_MIN_UNCOMPRESSED - 1, 1)


def test_a_large_high_ratio_archive_is_refused():
    assert looks_like_zip_bomb(50 * 1024 ** 3, 4 * 1024 ** 2)
    assert looks_like_zip_bomb(2 * 1024 ** 3, 0)
