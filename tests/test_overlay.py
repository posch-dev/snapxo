from pathlib import Path

from conftest import write_image

from snapxo.overlay import copy_unmatched_overlays, match_overlays
from snapxo.scanner import MediaFile


def mf(name: str, date: str, uuid: str | None, is_overlay: bool = False, ext: str = ".jpg"):
    return MediaFile(path=Path(name), date=date, uuid=uuid, ext=ext,
                     source="memory", original_name=name, is_overlay=is_overlay)


UUID_A = "11111111-2222-3333-4444-555555555555"
UUID_B = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_overlay_matches_its_main_file_by_date_and_uuid():
    main = mf("main.jpg", "2026-05-01", UUID_A)
    overlay = mf("overlay.png", "2026-05-01", UUID_A, is_overlay=True)

    matched, unmatched = match_overlays([main], [overlay])

    assert matched == [(main, overlay)]
    assert unmatched == []


def test_the_same_uuid_on_another_day_does_not_match():
    main = mf("main.jpg", "2026-05-01", UUID_A)
    overlay = mf("overlay.png", "2026-05-02", UUID_A, is_overlay=True)

    matched, unmatched = match_overlays([main], [overlay])

    assert matched == []
    assert unmatched == [overlay]


def test_a_different_uuid_does_not_match():
    main = mf("main.jpg", "2026-05-01", UUID_A)
    overlay = mf("overlay.png", "2026-05-01", UUID_B, is_overlay=True)

    assert match_overlays([main], [overlay]) == ([], [overlay])


def test_an_overlay_without_a_uuid_stays_unmatched():
    main = mf("main.jpg", "2026-05-01", UUID_A)
    overlay = mf("overlay.png", "2026-05-01", None, is_overlay=True)

    assert match_overlays([main], [overlay]) == ([], [overlay])


def test_main_files_without_a_uuid_are_not_matched_against():
    main = mf("main.jpg", "2026-05-01", None)
    overlay = mf("overlay.png", "2026-05-01", UUID_A, is_overlay=True)

    assert match_overlays([main], [overlay]) == ([], [overlay])


def test_matching_several_overlays_at_once():
    a = mf("a.jpg", "2026-05-01", UUID_A)
    b = mf("b.jpg", "2026-05-02", UUID_B)
    oa = mf("a-overlay.png", "2026-05-01", UUID_A, is_overlay=True)
    ob = mf("b-overlay.png", "2026-05-02", UUID_B, is_overlay=True)
    orphan = mf("c-overlay.png", "2026-05-03", UUID_A, is_overlay=True)

    matched, unmatched = match_overlays([a, b], [oa, ob, orphan])

    assert matched == [(a, oa), (b, ob)]
    assert unmatched == [orphan]


def test_unmatched_overlays_are_copied_to_their_own_folder(tmp_path: Path):
    src = write_image(tmp_path / "src" / "orphan-overlay.png", "white")
    overlay = MediaFile(path=src, date="2026-05-01", uuid=None, ext=".png",
                        source="memory", original_name="orphan-overlay.png", is_overlay=True)

    copy_unmatched_overlays([overlay], tmp_path / "out")

    assert (tmp_path / "out" / "_overlays" / "orphan-overlay.png").is_file()


def test_no_overlays_folder_is_created_when_there_is_nothing_to_copy(tmp_path: Path):
    copy_unmatched_overlays([], tmp_path / "out")

    assert not (tmp_path / "out" / "_overlays").exists()


def test_dry_run_copies_nothing(tmp_path: Path):
    src = write_image(tmp_path / "src" / "orphan-overlay.png", "white")
    overlay = MediaFile(path=src, date="2026-05-01", uuid=None, ext=".png",
                        source="memory", original_name="orphan-overlay.png", is_overlay=True)

    copy_unmatched_overlays([overlay], tmp_path / "out", dry_run=True)

    assert not (tmp_path / "out" / "_overlays").exists()
