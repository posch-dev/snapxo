from pathlib import Path

from conftest import write_image

from snapxo.checkpoint import Checkpoint
from snapxo.organizer import organize_into_folders
from snapxo.scanner import MediaFile


def media(tmp_path: Path, name: str, date: str, source: str = "memory", ext: str = ".jpg"):
    path = tmp_path / "src" / name
    if ext in (".mp4", ".mov"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x00\x00\x00\x18ftypmp42not-a-real-video")
    else:
        write_image(path, "red")
    return MediaFile(path=path, date=date, uuid=None, ext=ext,
                     source=source, original_name=name)


def test_files_land_in_year_folders_with_sequential_names(tmp_path: Path):
    files = [
        media(tmp_path, "b.jpg", "2026-05-02"),
        media(tmp_path, "a.jpg", "2026-05-01"),
        media(tmp_path, "c.jpg", "2025-01-01"),
    ]

    index = organize_into_folders(files, tmp_path / "out")

    assert [(e["subfolder"], e["new_name"]) for e in index] == [
        ("2025", "2025-01-01_0001.jpg"),
        ("2026", "2026-05-01_0001.jpg"),
        ("2026", "2026-05-02_0002.jpg"),
    ]
    for entry in index:
        assert Path(entry["dest"]).is_file()


def test_year_month_structure(tmp_path: Path):
    files = [
        media(tmp_path, "a.jpg", "2026-05-01"),
        media(tmp_path, "b.jpg", "2026-06-01"),
    ]

    index = organize_into_folders(files, tmp_path / "out", folder_structure="year-month")

    assert [e["subfolder"] for e in index] == ["2026-05", "2026-06"]
    # counters restart per folder
    assert [e["new_name"] for e in index] == ["2026-05-01_0001.jpg", "2026-06-01_0001.jpg"]


def test_unknown_dates_get_their_own_folder(tmp_path: Path):
    index = organize_into_folders([media(tmp_path, "a.jpg", "unknown")], tmp_path / "out")

    assert index[0]["subfolder"] == "unknown"
    assert index[0]["year"] == "unknown"


def test_videos_are_renamed_to_mp4(tmp_path: Path):
    mf = media(tmp_path, "a.mov", "2026-05-01", ext=".mov")

    index = organize_into_folders([mf], tmp_path / "out")

    assert index[0]["new_name"].endswith(".mp4")
    assert index[0]["type"] == "video"


def test_media_id_is_only_read_for_chat_media(tmp_path: Path):
    chat = media(tmp_path, "2026-05-04_b~someid.jpg", "2026-05-04", source="chat")
    memory = media(tmp_path, "2026-05-04_b~otherid.jpg", "2026-05-04", source="memory")

    index = organize_into_folders([chat, memory], tmp_path / "out")
    by_source = {e["source"]: e for e in index}

    assert by_source["chat"]["media_id"] == "b~someid"
    assert by_source["memory"]["media_id"] is None


def test_dry_run_builds_the_index_without_copying(tmp_path: Path):
    index = organize_into_folders([media(tmp_path, "a.jpg", "2026-05-01")],
                                  tmp_path / "out", dry_run=True)

    assert len(index) == 1
    assert not (tmp_path / "out").exists()


def test_checkpoint_skips_files_that_were_already_copied(tmp_path: Path):
    out = tmp_path / "out"
    mf = media(tmp_path, "a.jpg", "2026-05-01")
    checkpoint = Checkpoint(out, enabled=False)

    first = organize_into_folders([mf], out, checkpoint=checkpoint)
    dest = Path(first[0]["dest"])

    # Stand in for an encode that ran after the copy: re-copying would undo it.
    dest.write_bytes(b"encoded")
    second = organize_into_folders([mf], out, checkpoint=checkpoint)

    assert second[0]["dest"] == str(dest)
    assert dest.read_bytes() == b"encoded"


def test_without_a_checkpoint_the_copy_happens_again(tmp_path: Path):
    out = tmp_path / "out"
    mf = media(tmp_path, "a.jpg", "2026-05-01")

    dest = Path(organize_into_folders([mf], out)[0]["dest"])
    dest.write_bytes(b"encoded")
    organize_into_folders([mf], out)

    assert dest.read_bytes() != b"encoded"
