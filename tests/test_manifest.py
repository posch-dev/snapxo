from pathlib import Path

from conftest import write_image

from snapxo.archive.manifest import (
    attach_media_ids,
    build_media_id_map,
    load_manifest,
    manifest_path,
    manifest_to_file_index,
    write_manifest,
)


def entry(output_dir: Path, subfolder: str, name: str, **overrides) -> dict:
    dest = output_dir / subfolder / name
    write_image(dest, "red")
    base = {
        "date": f"{subfolder}-05-01", "year": subfolder, "subfolder": subfolder,
        "new_name": name, "original_name": name, "source": "memory",
        "type": "image", "ext": ".jpg", "uuid": None, "media_id": None,
        "dest": str(dest),
    }
    base.update(overrides)
    return base


def test_manifest_round_trips_through_disk(tmp_path: Path):
    index = [entry(tmp_path, "2026", "2026-05-01_0001.jpg")]

    write_manifest(tmp_path, index, own_username="testuser", sources=["export.zip"])
    loaded = load_manifest(tmp_path)

    assert loaded["own_username"] == "testuser"
    assert loaded["sources"] == ["export.zip"]
    assert loaded["files"][0]["name"] == "2026-05-01_0001.jpg"
    # relative and POSIX, so the folder survives moving between drives and platforms
    assert loaded["files"][0]["rel"] == "2026/2026-05-01_0001.jpg"


def test_manifest_records_sizes(tmp_path: Path):
    index = [entry(tmp_path, "2026", "2026-05-01_0001.jpg")]
    real_size = Path(index[0]["dest"]).stat().st_size

    write_manifest(tmp_path, index)

    assert load_manifest(tmp_path)["files"][0]["size"] == real_size


def test_dry_run_writes_nothing(tmp_path: Path):
    write_manifest(tmp_path, [entry(tmp_path, "2026", "a.jpg")], dry_run=True)

    assert not manifest_path(tmp_path).exists()


def test_load_manifest_returns_none_when_absent(tmp_path: Path):
    assert load_manifest(tmp_path) is None


def test_load_manifest_returns_none_when_corrupt(tmp_path: Path):
    path = manifest_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{broken", encoding="utf-8")

    assert load_manifest(tmp_path) is None


def test_file_index_is_rebuilt_from_a_manifest(tmp_path: Path):
    index = [entry(tmp_path, "2026", "2026-05-01_0001.jpg", media_id="b~someid", source="chat")]
    write_manifest(tmp_path, index)

    rebuilt = manifest_to_file_index(load_manifest(tmp_path), tmp_path)

    assert len(rebuilt) == 1
    assert rebuilt[0]["new_name"] == "2026-05-01_0001.jpg"
    assert rebuilt[0]["media_id"] == "b~someid"
    assert Path(rebuilt[0]["dest"]) == tmp_path / "2026" / "2026-05-01_0001.jpg"


def test_rebuilding_drops_entries_whose_file_is_gone(tmp_path: Path):
    index = [entry(tmp_path, "2026", "2026-05-01_0001.jpg")]
    write_manifest(tmp_path, index)
    Path(index[0]["dest"]).unlink()

    assert manifest_to_file_index(load_manifest(tmp_path), tmp_path) == []


def test_media_id_map_resolves_chat_media(tmp_path: Path):
    chat = entry(tmp_path, "2026", "2026-05-01_0001.jpg", source="chat", media_id="b~someid")

    media_map = build_media_id_map([chat])

    assert media_map["b~someid"]["dest"] == chat["dest"]


def test_media_id_map_follows_dedup_aliases(tmp_path: Path):
    # The chat copy was deleted as a duplicate, so its Media ID has to resolve
    # to the memory copy that was kept, or the message would show no media.
    kept = entry(tmp_path, "2026", "2026-05-01_0001.jpg",
                 original_name="2026-05-01_kept.jpg", source="memory")
    removed_path = tmp_path / "chat_media" / "2026-05-01_b~someid.jpg"

    media_map = build_media_id_map([kept], {str(removed_path): str(tmp_path / "2026-05-01_kept.jpg")})

    assert media_map["b~someid"]["dest"] == kept["dest"]


def test_attach_media_ids_writes_them_onto_the_entries(tmp_path: Path):
    chat = entry(tmp_path, "2026", "2026-05-01_0001.jpg", source="chat", media_id="b~someid")
    index = [chat]

    attach_media_ids(index, build_media_id_map(index))

    assert index[0]["media_ids"] == ["b~someid"]


def test_aliases_survive_a_manifest_round_trip(tmp_path: Path):
    kept = entry(tmp_path, "2026", "2026-05-01_0001.jpg",
                 original_name="2026-05-01_kept.jpg", source="chat", media_id="b~ownid")
    index = [kept]
    alias = {str(tmp_path / "2026-05-01_b~otherid.jpg"): str(tmp_path / "2026-05-01_kept.jpg")}

    attach_media_ids(index, build_media_id_map(index, alias))
    write_manifest(tmp_path, index)
    rebuilt = manifest_to_file_index(load_manifest(tmp_path), tmp_path)

    # a later --only-conversations run resolves both IDs without redoing dedup
    assert set(rebuilt[0]["media_ids"]) == {"b~ownid", "b~otherid"}
    assert set(build_media_id_map(rebuilt)) == {"b~ownid", "b~otherid"}
