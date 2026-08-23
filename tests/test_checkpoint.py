import json
from dataclasses import replace
from pathlib import Path

from snapxo.archive.checkpoint import CHECKPOINT_FILE, Checkpoint, config_fingerprint
from snapxo.config import Config


def base_config(tmp_path: Path) -> Config:
    return Config(inputs=[tmp_path / "in"], output=tmp_path / "out")


def test_fingerprint_is_stable_for_the_same_config(tmp_path: Path):
    assert config_fingerprint(base_config(tmp_path)) == config_fingerprint(base_config(tmp_path))


def test_fingerprint_changes_with_the_output_folder(tmp_path: Path):
    other = replace(base_config(tmp_path), output=tmp_path / "elsewhere")
    assert config_fingerprint(base_config(tmp_path)) != config_fingerprint(other)


def test_fingerprint_changes_with_a_filter(tmp_path: Path):
    other = replace(base_config(tmp_path), media_types=["photos"])
    assert config_fingerprint(base_config(tmp_path)) != config_fingerprint(other)


def test_fingerprint_ignores_verbose_and_yes(tmp_path: Path):
    # Resuming an interrupted run with -v has to keep working.
    noisy = replace(base_config(tmp_path), verbose=True, yes=True, resume=False)
    assert config_fingerprint(base_config(tmp_path)) == config_fingerprint(noisy)


def test_steps_and_files_survive_a_reload(tmp_path: Path):
    tmp_path.mkdir(exist_ok=True)
    cp = Checkpoint(tmp_path, fingerprint="abc")
    cp.complete_step("dedup")
    cp.mark_file_done("encode", "2026/a.mp4")
    cp.flush()

    restored = Checkpoint(tmp_path, fingerprint="abc")

    assert restored.load() is True
    assert restored.is_step_done("dedup")
    assert restored.is_file_done("encode", "2026/a.mp4")
    assert not restored.is_file_done("encode", "2026/b.mp4")
    assert not restored.is_step_done("stats")


def test_a_different_fingerprint_is_not_reused(tmp_path: Path):
    cp = Checkpoint(tmp_path, fingerprint="abc")
    cp.complete_step("dedup")

    other = Checkpoint(tmp_path, fingerprint="different")

    assert other.load() is False
    assert not other.is_step_done("dedup")


def test_a_corrupt_checkpoint_is_discarded(tmp_path: Path):
    (tmp_path / CHECKPOINT_FILE).write_text("{not json", encoding="utf-8")

    cp = Checkpoint(tmp_path, fingerprint="abc")

    assert cp.load() is False
    assert not cp.is_step_done("dedup")


def test_an_older_version_is_discarded(tmp_path: Path):
    (tmp_path / CHECKPOINT_FILE).write_text(
        json.dumps({"version": 1, "completed_steps": ["all"]}), encoding="utf-8"
    )

    assert Checkpoint(tmp_path, fingerprint="abc").load() is False


def test_load_is_false_when_nothing_was_recorded(tmp_path: Path):
    Checkpoint(tmp_path, fingerprint="abc").flush()

    assert Checkpoint(tmp_path, fingerprint="abc").load() is False


def test_dup_alias_round_trips(tmp_path: Path):
    cp = Checkpoint(tmp_path, fingerprint="abc")
    cp.complete_step("dedup")
    cp.store_dup_alias({"/gone.jpg": "/kept.jpg"})

    restored = Checkpoint(tmp_path, fingerprint="abc")
    restored.load()

    assert restored.dup_alias == {"/gone.jpg": "/kept.jpg"}


def test_disabled_checkpoint_writes_nothing(tmp_path: Path):
    cp = Checkpoint(tmp_path, fingerprint="abc", enabled=False)
    cp.complete_step("dedup")
    cp.mark_file_done("encode", "a.mp4")
    cp.flush()

    assert not (tmp_path / CHECKPOINT_FILE).exists()
    # still answers from memory within the same run
    assert cp.is_step_done("dedup")


def test_remove_deletes_the_file_and_any_leftover_temp(tmp_path: Path):
    cp = Checkpoint(tmp_path, fingerprint="abc")
    cp.complete_step("dedup")
    cp.path.with_suffix(".tmp").write_text("leftover", encoding="utf-8")

    cp.remove()

    assert not cp.path.exists()
    assert not cp.path.with_suffix(".tmp").exists()


def test_remove_on_a_missing_file_is_not_an_error(tmp_path: Path):
    Checkpoint(tmp_path, fingerprint="abc").remove()


def test_summary_counts_steps_and_files(tmp_path: Path):
    cp = Checkpoint(tmp_path, fingerprint="abc")
    cp.complete_step("dedup")
    cp.mark_file_done("encode", "a.mp4")
    cp.mark_file_done("organize", "b.jpg")

    assert cp.summary() == "1 steps, 2 files already done"
