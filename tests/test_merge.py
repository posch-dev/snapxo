import json

import pytest
from conftest import write_image

from snapxo.manifest import write_manifest
from snapxo.merge import merge_outputs
from snapxo.verify import load_checksums, load_integrity, write_checksums


def _output_folder(root, name, files):
    # files: {filename: (color, media_id)}
    folder = root / name
    file_index = []
    for filename, (color, media_id) in files.items():
        path = write_image(folder / "2026" / filename, color)
        file_index.append({
            "dest": str(path), "new_name": filename, "subfolder": "2026", "date": filename[:10],
            "type": "image", "ext": ".jpg", "source": "chat", "original_name": f"orig_{media_id}.jpg",
            "media_id": media_id, "media_ids": [media_id],
        })
    write_manifest(folder, file_index)
    (folder / "_meta" / "json").mkdir(parents=True, exist_ok=True)
    (folder / "_meta" / "json" / "account.json").write_text(
        json.dumps({"Basic Information": {"Username": "testuser"}}), encoding="utf-8")
    return folder


def _truncate(folder, rel):
    (folder / rel).write_bytes(b"cut")


def test_a_clean_merge_fingerprints_the_result(tmp_path):
    a = _output_folder(tmp_path, "a", {"2026-05-01_0001.jpg": ("red", "idone")})
    b = _output_folder(tmp_path, "b", {"2026-05-02_0001.jpg": ("blue", "idtwo")})
    out = tmp_path / "merged"

    assert merge_outputs([a, b], out) == 2
    assert len(load_checksums(out)) == 2
    assert load_integrity(out) == []


def test_a_damaged_input_stops_the_merge(tmp_path):
    a = _output_folder(tmp_path, "a", {"2026-05-01_0001.jpg": ("red", "idone")})
    b = _output_folder(tmp_path, "b", {"2026-05-02_0001.jpg": ("blue", "idtwo")})
    _truncate(b, "2026/2026-05-02_0001.jpg")
    out = tmp_path / "merged"

    with pytest.raises(SystemExit):
        merge_outputs([a, b], out)

    assert not out.exists()


def test_no_verify_takes_damaged_files_along_marked(tmp_path):
    a = _output_folder(tmp_path, "a", {"2026-05-01_0001.jpg": ("red", "idone")})
    b = _output_folder(tmp_path, "b", {"2026-05-02_0001.jpg": ("blue", "idtwo")})
    _truncate(b, "2026/2026-05-02_0001.jpg")
    out = tmp_path / "merged"

    assert merge_outputs([a, b], out, verify=False) == 2

    marked = load_integrity(out)
    assert len(marked) == 1
    assert marked[0]["reason"] == "wrong size"
    assert marked[0]["folder"] == "b"

    manifest = json.loads((out / "_meta" / "manifest.json").read_text(encoding="utf-8"))
    damaged = [e for e in manifest["files"] if e.get("integrity")]
    assert len(damaged) == 1
    # the gallery has to show it as damaged
    assert "damaged" in (out / "index.html").read_text(encoding="utf-8")


def test_skip_damaged_leaves_them_out(tmp_path):
    a = _output_folder(tmp_path, "a", {"2026-05-01_0001.jpg": ("red", "idone")})
    b = _output_folder(tmp_path, "b", {"2026-05-02_0001.jpg": ("blue", "idtwo")})
    _truncate(b, "2026/2026-05-02_0001.jpg")
    out = tmp_path / "merged"

    assert merge_outputs([a, b], out, verify=False, skip_damaged=True) == 1
    assert load_integrity(out) == []


def test_an_intact_copy_beats_the_damaged_one(tmp_path):
    a = _output_folder(tmp_path, "a", {"2026-05-01_0001.jpg": ("red", "idone")})
    b = _output_folder(tmp_path, "b", {"2026-05-01_0001.jpg": ("red", "idone")})
    _truncate(b, "2026/2026-05-01_0001.jpg")
    out = tmp_path / "merged"

    assert merge_outputs([a, b], out, verify=False) == 1

    assert load_integrity(out) == []
    kept = out / "2026" / "2026-05-01_0001.jpg"
    assert kept.stat().st_size > 3


def test_changed_content_is_caught_through_the_checksums(tmp_path):
    a = _output_folder(tmp_path, "a", {"2026-05-01_0001.jpg": ("red", "idone")})
    b = _output_folder(tmp_path, "b", {"2026-05-02_0001.jpg": ("blue", "idtwo")})
    # fingerprint b, then change a file without changing its size
    write_checksums(b, {"2026/2026-05-02_0001.jpg": "0" * 32})
    out = tmp_path / "merged"

    assert merge_outputs([a, b], out, verify=False) == 2

    marked = load_integrity(out)
    assert len(marked) == 1
    assert marked[0]["reason"] == "changed content"
