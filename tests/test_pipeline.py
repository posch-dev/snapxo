# Images only and encoding off, so nothing needs ffmpeg or a browser.

from pathlib import Path

import pytest

from snapxo import pipeline
from snapxo.archive.checkpoint import CHECKPOINT_FILE
from snapxo.config import Config
from snapxo.tools.ffmpeg import FFmpeg


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
    assert (output_dir / "map.html").is_file()
    assert (output_dir / "_meta" / "app-chats.js").is_file()
    assert (output_dir / "_meta" / "app-media.js").is_file()
    assert (output_dir / "_meta" / "manifest.json").is_file()
    assert (output_dir / "_meta" / "json").is_dir()
    assert list((output_dir / "2026").glob("*.jpg"))


def test_organize_never_writes_the_loose_pages(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir))

    assert not (output_dir / "gallery.html").exists()
    assert not (output_dir / "stats.html").exists()
    assert not (output_dir / "chats.html").exists()
    assert not (output_dir / "conversations").exists()


def test_duplicates_are_removed_before_organizing(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir))

    # four unique out of five in the fixture
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


def test_narrowing_the_media_still_writes_the_whole_app(export_dir: Path, output_dir: Path,
                                                       monkeypatch):
    # The pages come from the JSON, so leaving media out never empties them.
    # Voice is the one selection this fixture has nothing for, and telling a voice
    # message from a video needs ffprobe, which the test machines do not have. No
    # video reaches the check either way, since the fixture is images only.
    monkeypatch.setattr(FFmpeg, "check", lambda self: True)
    pipeline.run_pipeline(run_config(export_dir, output_dir, media_types=["voice"]))

    assert (output_dir / "index.html").is_file()
    assert (output_dir / "map.html").is_file()
    assert (output_dir / "_meta" / "app-chats.js").is_file()
    assert not list((output_dir / "2026").glob("*.jpg"))


def test_a_named_source_leaves_the_other_one_out(export_dir: Path, output_dir: Path):
    both = output_dir / "both"
    pipeline.run_pipeline(run_config(export_dir, both))
    memories_only = output_dir / "memories"
    pipeline.run_pipeline(run_config(export_dir, memories_only, media_sources=["memories"]))

    everything = len(list(both.rglob("*.jpg")))
    narrowed = len(list(memories_only.rglob("*.jpg")))
    assert 0 < narrowed <= everything


def test_the_raw_export_survives_a_narrowed_run(export_dir: Path, output_dir: Path):
    # An --only flag used to skip _meta/json silently, which killed rebuild.
    pipeline.run_pipeline(run_config(export_dir, output_dir, media_types=["photos"]))

    assert (output_dir / "_meta" / "json").is_dir()
    assert (output_dir / "_meta" / "manifest.json").is_file()


class Boom(Exception):
    pass


def test_an_interrupted_run_resumes_instead_of_starting_over(
    export_dir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(pipeline, "generate_map_html",
                        lambda *a, **kw: (_ for _ in ()).throw(Boom()))

    with pytest.raises(Boom):
        pipeline.run_pipeline(run_config(export_dir, output_dir))

    checkpoint = output_dir / CHECKPOINT_FILE
    assert checkpoint.is_file()

    organized = sorted((output_dir / "2026").glob("*.jpg"))
    # stands in for work a later step did, which must not be undone
    for path in organized:
        path.write_bytes(b"already processed")

    monkeypatch.undo()
    # same config, or the fingerprint changes and the checkpoint is dropped
    pipeline.run_pipeline(run_config(export_dir, output_dir))

    assert all(p.read_bytes() == b"already processed" for p in organized)
    assert not checkpoint.exists()


def test_a_run_with_different_filters_ignores_an_old_checkpoint(
    export_dir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(pipeline, "generate_map_html",
                        lambda *a, **kw: (_ for _ in ()).throw(Boom()))
    with pytest.raises(Boom):
        pipeline.run_pipeline(run_config(export_dir, output_dir))
    monkeypatch.undo()

    # a different selection, so the fingerprint no longer matches
    pipeline.run_pipeline(run_config(export_dir, output_dir, media_types=["photos"]))

    assert (output_dir / "index.html").is_file()


def test_no_resume_ignores_an_existing_checkpoint(
    export_dir: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(pipeline, "generate_map_html",
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


def test_the_raw_html_export_is_dropped_by_default(export_dir: Path, output_dir: Path):
    # Nothing reads _meta/html and the JSON holds the same data.
    pipeline.run_pipeline(run_config(export_dir, output_dir))

    assert not (output_dir / "_meta" / "html").exists()
    assert (output_dir / "_meta" / "json").is_dir()


def test_keep_raw_html_keeps_it(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir, keep_raw_html=True))

    assert (output_dir / "_meta" / "html" / "chat_history.html").is_file()


def test_the_archive_is_fingerprinted_by_default(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir))

    assert (output_dir / "_meta" / "checksums.json").is_file()


def test_no_checksums_skips_the_fingerprint(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(run_config(export_dir, output_dir, no_checksums=True))

    assert not (output_dir / "_meta" / "checksums.json").exists()
