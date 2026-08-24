# Finding the archive from whatever path was typed.

from pathlib import Path

from snapxo.archive.folder import (
    FOLDER_BUDGET,
    find_archives,
    is_archive,
    resolve_many,
    resolve_one,
)


def make_archive(where: Path) -> Path:
    (where / "_meta").mkdir(parents=True)
    (where / "_meta" / "manifest.json").write_text("{}", encoding="utf-8")
    return where


def test_the_archive_itself_is_returned_unchanged(tmp_path: Path):
    archive = make_archive(tmp_path / "archive")

    assert is_archive(archive)
    assert find_archives(archive) == [archive]


def test_pointing_inside_walks_back_up(tmp_path: Path):
    archive = make_archive(tmp_path / "archive")
    (archive / "_meta" / "thumbs" / "medium").mkdir(parents=True)
    (archive / "2024").mkdir()

    for inside in (archive / "_meta", archive / "_meta" / "thumbs" / "medium", archive / "2024"):
        assert find_archives(inside) == [archive]


def test_walking_up_stops_after_three_levels(tmp_path: Path):
    archive = make_archive(tmp_path / "archive")
    deep = archive / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)

    assert find_archives(deep) == []


def test_a_parent_folder_expands_to_the_archives_in_it(tmp_path: Path):
    parent = tmp_path / "parent"
    first = make_archive(parent / "one")
    second = make_archive(parent / "two")

    assert sorted(find_archives(parent)) == sorted([first, second])


def test_an_archive_is_never_searched_for_more_archives(tmp_path: Path):
    outer = make_archive(tmp_path / "outer")
    make_archive(outer / "inner")

    assert find_archives(tmp_path) == [outer]


def test_the_search_gives_up_after_the_budget(tmp_path: Path, capsys):
    for number in range(FOLDER_BUDGET + 10):
        (tmp_path / f"folder-{number:03d}").mkdir()

    assert find_archives(tmp_path) == []
    assert "Stopped after looking through" in capsys.readouterr().out


def test_one_folder_commands_refuse_to_guess(tmp_path: Path, capsys):
    parent = tmp_path / "parent"
    make_archive(parent / "one")
    make_archive(parent / "two")

    assert resolve_one(parent) is None
    assert "Name the one you mean" in capsys.readouterr().out


def test_nothing_nearby_says_so(tmp_path: Path, capsys):
    plain = tmp_path / "plain"
    plain.mkdir()

    assert resolve_one(plain) is None
    assert "not a folder SnapXO produced" in capsys.readouterr().out


def test_many_folders_are_deduplicated(tmp_path: Path):
    parent = tmp_path / "parent"
    archive = make_archive(parent / "one")

    assert resolve_many([parent, archive, archive / "_meta"]) == [archive]


def test_a_folder_of_media_years_counts_without_a_manifest(tmp_path: Path):
    # --no-meta leaves no manifest and no pages, only the media
    bare = tmp_path / "bare"
    (bare / "2024").mkdir(parents=True)
    (bare / "2024" / "2024-01-01_snap.jpg").write_bytes(b"x")

    assert is_archive(bare)
