from pathlib import Path

import pytest
from click.testing import CliRunner

from snapxo import __version__
from snapxo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_version_matches_the_package(runner):
    result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output


def test_group_help_lists_both_commands(runner):
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "organize" in result.output
    assert "merge" in result.output
    assert "verify" in result.output
    assert "doctor" in result.output


def test_the_epilog_is_flush_left(runner):
    # click indents epilogs by two columns, which format_epilog overrides.
    result = runner.invoke(main, ["--help"])
    lines = result.output.splitlines()

    assert "Try:" in lines
    assert any(line.startswith("snapxo organize --help") for line in lines)
    assert any(line.startswith("snapxo merge --help") for line in lines)


def test_organize_requires_an_output(runner, tmp_path: Path):
    (tmp_path / "json").mkdir()

    result = runner.invoke(main, ["organize", str(tmp_path)])

    assert result.exit_code != 0
    assert "--output" in result.output


def test_info_and_dry_run_need_no_output(runner, tmp_path: Path):
    (tmp_path / "json").mkdir()
    (tmp_path / "json" / "account.json").write_text("{}", encoding="utf-8")

    for flag in ("--info", "--dry-run"):
        result = runner.invoke(main, ["organize", str(tmp_path), flag])
        assert "-o/--output is required" not in result.output, flag


def test_merge_requires_an_output(runner, tmp_path: Path):
    result = runner.invoke(main, ["merge", str(tmp_path)])

    assert result.exit_code != 0
    assert "--output" in result.output


def test_merge_dry_run_needs_no_output(runner, tmp_path: Path):
    result = runner.invoke(main, ["merge", str(tmp_path), "--dry-run"])

    assert "-o/--output is required" not in result.output


def test_deleting_sources_cannot_skip_the_check(runner, tmp_path: Path):
    result = runner.invoke(main, ["merge", str(tmp_path), str(tmp_path), "-o", str(tmp_path / "out"),
                                  "--delete-sources", "--no-verify"])

    assert result.exit_code != 0
    assert "--delete-sources cannot be combined with --no-verify" in result.output


def test_a_malformed_date_is_rejected(runner, tmp_path: Path):
    (tmp_path / "json").mkdir()

    result = runner.invoke(main, ["organize", str(tmp_path), "-o", str(tmp_path / "out"), "--since", "20.07.2026"])

    assert result.exit_code != 0
    assert "--since must be a date" in result.output


def test_the_sticker_flags_are_gone(runner, tmp_path: Path):
    for flag in ("--only-stickers", "--no-stickers"):
        result = runner.invoke(main, ["organize", str(tmp_path), "-o", str(tmp_path / "out"), flag])
        assert result.exit_code != 0
        assert "No such option" in result.output


def test_organize_requires_an_input(runner, tmp_path: Path):
    result = runner.invoke(main, ["organize", "-o", str(tmp_path / "out")])

    assert result.exit_code != 0


def test_a_missing_input_path_is_rejected(runner, tmp_path: Path):
    result = runner.invoke(main, ["organize", str(tmp_path / "nope"), "-o", str(tmp_path / "out")])

    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_bare_arguments_fall_through_to_organize(runner, tmp_path: Path):
    # `snapxo export.zip -o out` has to keep working without naming the command.
    result = runner.invoke(main, [str(tmp_path)])

    assert result.exit_code != 0
    assert "--output" in result.output


def test_every_organize_option_documents_itself(runner):
    from snapxo.cli import organize

    for param in organize.params:
        if param.name in ("input",):
            continue
        assert param.help, f"{param.name} has no help text"
        assert param.help[0].isupper() or param.help.startswith("-"), param.name


def test_every_merge_option_documents_itself(runner):
    from snapxo.cli import merge_command

    for param in merge_command.params:
        if param.name in ("folders",):
            continue
        assert param.help, f"{param.name} has no help text"


def test_defaults_are_shown_rather_than_written_into_the_text(runner):
    result = runner.invoke(main, ["organize", "--help"])

    assert "[default: 23]" in result.output
    assert "[default: year]" in result.output
    assert "[default: html]" in result.output
    # the old style, spelled into the help string, should be gone
    assert "(default: 23" not in result.output


def test_every_command_describes_what_it_does(runner):
    for command in ("organize", "merge", "verify", "doctor"):
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
