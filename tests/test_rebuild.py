# Rebuilding the pages of a finished folder, without the original export.

import shutil
from pathlib import Path

from snapxo import pipeline
from snapxo.archive.rebuild import rebuild_folder
from snapxo.config import Config


def organized_folder(export_dir: Path, output_dir: Path) -> Path:
    pipeline.run_pipeline(Config(inputs=[export_dir], output=output_dir, yes=True,
                                 no_encode=True, no_overlay=True))
    return output_dir


def test_rebuild_writes_the_pages_again(export_dir: Path, output_dir: Path):
    folder = organized_folder(export_dir, output_dir)
    (folder / "index.html").unlink()

    assert rebuild_folder(folder) is True

    assert (folder / "index.html").is_file()
    assert (folder / "_meta" / "app-chats.js").is_file()


def test_rebuild_leaves_the_media_untouched(export_dir: Path, output_dir: Path):
    folder = organized_folder(export_dir, output_dir)
    media = sorted((folder / "2026").glob("*.jpg"))
    before = {f.name: (f.stat().st_size, f.stat().st_mtime_ns) for f in media}

    rebuild_folder(folder)

    after = {f.name: (f.stat().st_size, f.stat().st_mtime_ns) for f in sorted((folder / "2026").glob("*.jpg"))}
    assert after == before


def test_rebuild_refuses_a_folder_it_did_not_produce(tmp_path: Path):
    stranger = tmp_path / "holiday-photos"
    stranger.mkdir()

    assert rebuild_folder(stranger) is False


def test_rebuild_without_raw_json_still_writes_the_gallery(export_dir: Path, output_dir: Path):
    folder = organized_folder(export_dir, output_dir)
    shutil.rmtree(folder / "_meta" / "json")
    (folder / "index.html").unlink()

    assert rebuild_folder(folder) is True
    assert (folder / "index.html").is_file()


def test_rebuild_refuses_when_every_listed_file_is_gone(export_dir: Path, output_dir: Path):
    folder = organized_folder(export_dir, output_dir)
    shutil.rmtree(folder / "2026")

    assert rebuild_folder(folder) is False
