import shutil
from pathlib import Path

from conftest import write_image

from snapxo.dedup import collect_media_files, find_duplicates, remove_duplicates


def test_find_duplicates_groups_identical_files(tmp_path: Path):
    a = write_image(tmp_path / "a.jpg", "red")
    b = tmp_path / "b.jpg"
    shutil.copy2(a, b)
    write_image(tmp_path / "c.jpg", "blue")

    dupes = find_duplicates([a, b, tmp_path / "c.jpg"])

    assert len(dupes) == 1
    keep, removed = dupes[0]
    assert keep.name == "a.jpg"
    assert [p.name for p in removed] == ["b.jpg"]


def test_find_duplicates_keeps_the_first_name_alphabetically(tmp_path: Path):
    first = write_image(tmp_path / "aaa.jpg", "red")
    later = tmp_path / "zzz.jpg"
    shutil.copy2(first, later)

    keep, removed = find_duplicates([later, first])[0]

    assert keep.name == "aaa.jpg"
    assert [p.name for p in removed] == ["zzz.jpg"]


def test_remove_duplicates_deletes_and_reports(tmp_path: Path):
    a = write_image(tmp_path / "a.jpg", "red")
    b = tmp_path / "b.jpg"
    shutil.copy2(a, b)
    size = b.stat().st_size

    removed, freed, alias = remove_duplicates([a, b])

    assert removed == 1
    assert freed == size
    assert a.exists()
    assert not b.exists()
    assert alias == {str(b): str(a)}


def test_remove_duplicates_dry_run_keeps_the_files(tmp_path: Path):
    a = write_image(tmp_path / "a.jpg", "red")
    b = tmp_path / "b.jpg"
    shutil.copy2(a, b)

    removed, _, alias = remove_duplicates([a, b], dry_run=True)

    assert removed == 1
    assert b.exists()
    assert alias == {str(b): str(a)}


def test_remove_duplicates_on_unique_files_does_nothing(tmp_path: Path):
    a = write_image(tmp_path / "a.jpg", "red")
    b = write_image(tmp_path / "b.jpg", "blue")

    removed, freed, alias = remove_duplicates([a, b])

    assert (removed, freed, alias) == (0, 0, {})
    assert a.exists() and b.exists()


def test_collect_media_files_walks_recursively_and_filters(tmp_path: Path):
    write_image(tmp_path / "2026" / "a.jpg")
    write_image(tmp_path / "2027" / "b.png")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
    (tmp_path / ".hidden.jpg").write_bytes(b"ignored")

    found = [p.name for p in collect_media_files(tmp_path)]

    assert found == ["a.jpg", "b.png"]
