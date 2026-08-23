from pathlib import Path

from PIL import Image

from snapxo.read.fixtypes import _detect_type, fix_unknown_files


def _as_unknown(tmp_path: Path, name: str, save) -> Path:
    real = tmp_path / "tmp_source"
    save(real)
    target = tmp_path / name
    target.write_bytes(real.read_bytes())
    real.unlink()
    return target


def test_detects_jpeg(tmp_path: Path):
    f = _as_unknown(tmp_path, "a.unknown",
                    lambda p: Image.new("RGB", (8, 8), "red").save(p, format="JPEG"))
    assert _detect_type(f) == ".jpg"


def test_detects_png(tmp_path: Path):
    f = _as_unknown(tmp_path, "a.unknown",
                    lambda p: Image.new("RGB", (8, 8), "red").save(p, format="PNG"))
    assert _detect_type(f) == ".png"


def test_detects_webp(tmp_path: Path):
    f = _as_unknown(tmp_path, "a.unknown",
                    lambda p: Image.new("RGB", (8, 8), "red").save(p, format="WEBP"))
    assert _detect_type(f) == ".webp"


def test_returns_none_for_unrecognised_content(tmp_path: Path):
    f = tmp_path / "a.unknown"
    f.write_bytes(b"this is just text, no magic bytes")
    assert _detect_type(f) is None


def test_returns_none_for_a_file_too_short_to_identify(tmp_path: Path):
    f = tmp_path / "a.unknown"
    f.write_bytes(b"ab")
    assert _detect_type(f) is None


def test_returns_none_for_an_unreadable_path(tmp_path: Path):
    assert _detect_type(tmp_path / "does-not-exist.unknown") is None


def test_fix_unknown_files_renames_and_maps(tmp_path: Path):
    f = _as_unknown(tmp_path, "2026-05-01_1200-media.unknown",
                    lambda p: Image.new("RGB", (8, 8), "red").save(p, format="PNG"))

    renamed = fix_unknown_files([f])

    new_path = tmp_path / "2026-05-01_1200-media.png"
    assert renamed == {f: new_path}
    assert new_path.is_file()
    assert not f.exists()


def test_fix_unknown_files_ignores_files_with_a_real_extension(tmp_path: Path):
    keep = tmp_path / "already.jpg"
    Image.new("RGB", (8, 8), "red").save(keep)

    assert fix_unknown_files([keep]) == {}
    assert keep.is_file()


def test_fix_unknown_files_leaves_undetectable_ones_in_place(tmp_path: Path):
    f = tmp_path / "mystery.unknown"
    f.write_bytes(b"no magic bytes here at all")

    assert fix_unknown_files([f]) == {}
    assert f.is_file()
