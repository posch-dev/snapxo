import json

from conftest import write_image

from snapxo.manifest import write_manifest
from snapxo.verify import load_checksums, verify_folder, write_checksums


def _folder(tmp_path, names=("2026-05-01_0001.jpg", "2026-05-02_0002.jpg")):
    out = tmp_path / "out"
    file_index = []
    for name in names:
        path = write_image(out / "2026" / name, "red")
        file_index.append({
            "dest": str(path), "new_name": name, "subfolder": "2026", "date": name[:10],
            "type": "image", "ext": ".jpg", "source": "memory", "original_name": name,
        })
    write_manifest(out, file_index)
    return out, file_index


def test_a_clean_folder_reports_no_problems(tmp_path):
    out, _ = _folder(tmp_path)

    report, computed = verify_folder(out)

    assert report.ok
    assert report.checked == 2
    assert computed == {}


def test_a_missing_file_is_found_without_hashing(tmp_path):
    out, _ = _folder(tmp_path)
    (out / "2026" / "2026-05-01_0001.jpg").unlink()

    report, _ = verify_folder(out)

    assert not report.ok
    assert report.missing == ["2026/2026-05-01_0001.jpg"]


def test_a_truncated_file_is_found_by_size(tmp_path):
    out, _ = _folder(tmp_path)
    (out / "2026" / "2026-05-02_0002.jpg").write_bytes(b"cut")

    report, _ = verify_folder(out)

    assert report.wrong_size == ["2026/2026-05-02_0002.jpg"]


def test_hashing_writes_and_then_compares_a_baseline(tmp_path):
    out, _ = _folder(tmp_path)

    report, computed = verify_folder(out, hashes=True)
    assert report.ok
    assert not report.has_baseline
    write_checksums(out, computed)

    assert set(load_checksums(out)) == {"2026/2026-05-01_0001.jpg", "2026/2026-05-02_0002.jpg"}

    # same size, different content: only the checksum can see this
    target = out / "2026" / "2026-05-01_0001.jpg"
    data = bytearray(target.read_bytes())
    data[-1] = (data[-1] + 1) % 256
    target.write_bytes(bytes(data))

    report, _ = verify_folder(out, hashes=True)

    assert report.has_baseline
    assert report.wrong_hash == ["2026/2026-05-01_0001.jpg"]
    assert report.wrong_size == []


def test_files_outside_the_manifest_are_listed(tmp_path):
    out, _ = _folder(tmp_path)
    write_image(out / "2026" / "stray.jpg", "blue")

    report, _ = verify_folder(out)

    assert report.ok
    assert report.unlisted == ["2026/stray.jpg"]


def test_a_folder_without_a_manifest_says_so(tmp_path):
    out = tmp_path / "out"
    out.mkdir()

    report, _ = verify_folder(out)

    assert not report.has_manifest
    assert not report.ok


def test_an_old_manifest_without_the_new_fields_still_loads(tmp_path):
    out, _ = _folder(tmp_path)
    manifest = json.loads((out / "_meta" / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        entry.pop("integrity", None)
    (out / "_meta" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report, _ = verify_folder(out)

    assert report.ok
    assert report.checked == 2
