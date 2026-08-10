# End-to-end runs over a synthetic export. Images only and encoding off, so
# nothing here needs ffmpeg or a browser to be installed.

from pathlib import Path

import pytest

from snapxo import pipeline
from snapxo.checkpoint import CHECKPOINT_FILE
from snapxo.config import Config


def run_config(export_dir: Path, output_dir: Path, **overrides) -> Config:
    base = {
        "inputs": [export_dir], "output": output_dir, "yes": True,
        "no_encode": True, "no_overlay": True,
    }
    base.update(overrides)
    return Config(**base)


def test_a_full_run_produces_the_expected_output(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir))

    assert (output_dir / "index.html").is_file()
    assert (output_dir / "stats.html").is_file()
    assert (output_dir / "_meta" / "manifest.json").is_file()
    assert (output_dir / "_meta" / "json").is_dir()
    assert list((output_dir / "conversations").glob("*.html"))
    assert list((output_dir / "2026").glob("*.jpg"))


def test_duplicates_are_removed_before_organizing(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir))

    # four unique images out of the five in the fixture
    assert len(list((output_dir / "2026").glob("*.jpg"))) == 4


def test_the_checkpoint_is_gone_after_a_finished_run(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir))

    assert not (output_dir / CHECKPOINT_FILE).exists()


def test_info_neither_writes_nor_creates_the_output_folder(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir, info=True))

    assert not output_dir.exists()


def test_dry_run_creates_nothing(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir, dry_run=True))

    assert not output_dir.exists()


def test_dry_run_leaves_the_export_untouched(export_dir: Path, output_dir: Path):
    before = sorted(p.name for p in (export_dir / "memories").iterdir())

    pipeline.run_pipeline(run_config(export_dir, output_dir, dry_run=True))

    assert sorted(p.name for p in (export_dir / "memories").iterdir()) == before


def test_missing_output_is_refused(export_dir: Path):
    config = Config(inputs=[export_dir], output=None, yes=True, no_encode=True, no_overlay=True)

    with pytest.raises(SystemExit):
        pipeline.run_pipeline(config)


def test_an_input_without_an_export_is_refused(tmp_path: Path, output_dir: Path):
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(SystemExit):
        pipeline.run_pipeline(run_config(empty, output_dir))


def test_only_stats_writes_stats_and_nothing_else(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir, only_stats=True))

    assert (output_dir / "stats.html").is_file()
    assert not (output_dir / "conversations").exists()
    assert not (output_dir / "index.html").exists()


def test_conversations_can_be_rebuilt_from_the_written_metadata(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir))
    first = (output_dir / "conversations").glob("*.html")
    before = {p.name for p in first}

    rebuilt = output_dir / "rebuilt"
    pipeline.run_pipeline(run_config(output_dir / "_meta" / "json", rebuilt,
                                     only_conversations=True))

    assert {p.name for p in (rebuilt / "conversations").glob("*.html")} == before


class Boom(Exception):
    pass


def test_an_interrupted_run_resumes_instead_of_starting_over(
    export_dir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(pipeline, "generate_stats_html",
                        lambda *a, **kw: (_ for _ in ()).throw(Boom()))

    with pytest.raises(Boom):
        pipeline.run_pipeline(run_config(export_dir, output_dir))

    checkpoint = output_dir / CHECKPOINT_FILE
    assert checkpoint.is_file()

    organized = sorted((output_dir / "2026").glob("*.jpg"))
    # stand in for work a later step did to the files, which must not be undone
    for path in organized:
        path.write_bytes(b"already processed")

    monkeypatch.undo()
    pipeline.run_pipeline(run_config(export_dir, output_dir))

    assert all(p.read_bytes() == b"already processed" for p in organized)
    assert not checkpoint.exists()


def test_a_run_with_different_filters_ignores_an_old_checkpoint(
    export_dir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(pipeline, "generate_stats_html",
                        lambda *a, **kw: (_ for _ in ()).throw(Boom()))
    with pytest.raises(Boom):
        pipeline.run_pipeline(run_config(export_dir, output_dir))
    monkeypatch.undo()

    # different filters, so the fingerprint no longer matches
    pipeline.run_pipeline(run_config(export_dir, output_dir, only_stats=True))

    assert (output_dir / "stats.html").is_file()


def test_no_resume_ignores_an_existing_checkpoint(
    export_dir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(pipeline, "generate_stats_html",
                        lambda *a, **kw: (_ for _ in ()).throw(Boom()))
    with pytest.raises(Boom):
        pipeline.run_pipeline(run_config(export_dir, output_dir))
    monkeypatch.undo()

    organized = sorted((output_dir / "2026").glob("*.jpg"))
    for path in organized:
        path.write_bytes(b"already processed")

    pipeline.run_pipeline(run_config(export_dir, output_dir, resume=False))

    # without resume every file is copied again, overwriting the marker
    assert all(p.read_bytes() != b"already processed" for p in organized)
