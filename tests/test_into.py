import json
import os
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner
from conftest import write_image

from snapxo import pipeline
from snapxo.archive import into
from snapxo.archive.into import merged_path, organize_into, organized_path
from snapxo.archive.manifest import load_manifest
from snapxo.cli import main
from snapxo.config import Config


def _organize(inputs: list[Path], **options) -> Config:
    return Config(inputs=inputs, yes=True, no_encode=True, no_overlay=True, **options)


@pytest.fixture
def archive(export_dir: Path, tmp_path: Path) -> Path:
    folder = tmp_path / "library" / "Snapchat"
    config = _organize([export_dir], timezone="Europe/Vienna")
    config.output = folder
    pipeline.run_pipeline(config)

    manifest = json.loads((folder / "_meta" / "manifest.json").read_text(encoding="utf-8"))
    manifest["sources"] = ["mydata_2025.zip"]
    (folder / "_meta" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (folder / "pdf").mkdir()
    (folder / "pdf" / "stats.pdf").write_bytes(b"%PDF-1.7 old stats")
    (folder / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    return folder


@pytest.fixture
def new_export(export_dir: Path, tmp_path: Path) -> Path:
    write_image(export_dir / "memories" / "2026-06-01_1200-media.jpg", "purple")
    path = tmp_path / "mydata_2026.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for file in export_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(export_dir).as_posix())
    return path


def _media(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.glob("20*/*.jpg"))


def _snapshot(folder: Path) -> dict:
    return {p.relative_to(folder): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


def test_into_swaps_in_the_merged_archive_and_keeps_the_previous_one(archive, new_export, capsys):
    before_media = _media(archive)

    assert organize_into(_organize([new_export]), archive) is True

    manifest = load_manifest(archive)
    assert manifest["timezone"] == "Europe/Vienna"
    assert manifest["sources"] == ["mydata_2025.zip", "mydata_2026.zip"]
    assert len(_media(archive)) == len(before_media) + 1
    assert (archive / "pdf" / "stats.pdf").read_bytes() == b"%PDF-1.7 old stats"
    assert (archive / "docker-compose.yml").is_file()

    previous = [p for p in archive.parent.iterdir() if p.name.startswith("Snapchat.before-")]
    assert len(previous) == 1
    assert _media(previous[0]) == before_media
    # hardlinked, so the previous archive costs no second copy of the media
    assert any(os.path.samefile(archive / "2026" / name, previous[0] / "2026" / name) for name in before_media)
    assert not organized_path(archive).exists()
    assert not merged_path(archive).exists()
    assert "snapxo pdf" in capsys.readouterr().out


def test_a_failed_check_leaves_the_archive_byte_identical(archive, new_export, monkeypatch, capsys):
    before = _snapshot(archive)
    real_find_losses = into.find_losses

    def lose_a_file(archive_dir, merged, seen_hashes, carried):
        next(merged.glob("20*/*.jpg")).unlink()
        return real_find_losses(archive_dir, merged, seen_hashes, carried)

    monkeypatch.setattr(into, "find_losses", lose_a_file)

    with pytest.raises(SystemExit):
        organize_into(_organize([new_export]), archive)

    assert _snapshot(archive) == before
    assert merged_path(archive).is_dir()
    assert str(merged_path(archive)) in capsys.readouterr().out


def test_a_different_timezone_is_refused_before_anything_is_written(archive, new_export, capsys):
    with pytest.raises(SystemExit):
        organize_into(_organize([new_export], timezone="Europe/London"), archive)

    assert not organized_path(archive).exists()
    assert "snapxo rebuild" in capsys.readouterr().out


def test_a_leftover_merge_stops_the_run(archive, new_export, capsys):
    merged_path(archive).mkdir()

    with pytest.raises(SystemExit):
        organize_into(_organize([new_export]), archive)

    assert "stopped before swapping" in capsys.readouterr().out


def test_a_half_done_swap_is_explained_not_guessed(archive, new_export, capsys):
    before = archive.with_name("Snapchat.before-2026-09-13")
    archive.rename(before)
    merged_path(archive).mkdir()

    with pytest.raises(SystemExit):
        organize_into(_organize([new_export]), archive)

    printed = capsys.readouterr().out
    assert f"rename {merged_path(archive).name} to Snapchat" in printed
    assert "rename Snapchat.before-2026-09-13 to Snapchat" in printed
    assert before.is_dir()


def test_delete_old_removes_the_previous_archive(archive, new_export):
    organize_into(_organize([new_export]), archive, delete_old=True)

    assert archive.is_dir()
    assert [p.name for p in archive.parent.iterdir()] == ["Snapchat"]


def test_delete_old_refuses_no_verify(archive, new_export):
    result = CliRunner().invoke(main, ["organize", str(new_export), "--into", str(archive),
                                       "--delete-old", "--no-verify", "-y"])

    assert result.exit_code == 2
    assert "--no-verify" in result.output
    assert not organized_path(archive).exists()


def test_into_and_output_exclude_each_other(archive, new_export, tmp_path):
    result = CliRunner().invoke(main, ["organize", str(new_export), "--into", str(archive),
                                       "-o", str(tmp_path / "elsewhere")])

    assert result.exit_code == 2


def test_a_dry_run_changes_nothing(archive, new_export):
    before = _snapshot(archive)

    organize_into(_organize([new_export], dry_run=True), archive)

    assert _snapshot(archive) == before
    assert sorted(p.name for p in archive.parent.iterdir()) == ["Snapchat"]


def test_the_structure_comes_from_the_archive():
    assert into.folder_structure_of({"files": [{"subfolder": "2026-05"}]}) == "year-month"
    assert into.folder_structure_of({"files": [{"subfolder": "2026"}, {"subfolder": "unknown"}]}) == "year"


def test_media_is_merged_and_everything_else_carried(archive):
    carried = into.files_to_carry(archive)

    assert "pdf/stats.pdf" in carried
    assert "docker-compose.yml" in carried
    assert not any(rel.startswith(("2026/", "_meta/")) for rel in carried)
