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


def test_a_path_instead_of_a_command_is_refused(runner, tmp_path: Path):
    # There used to be a fallback to organize, which made a typo look like a path.
    result = runner.invoke(main, [str(tmp_path)])

    assert result.exit_code != 0
    assert "is not a SnapXO command" in result.output
    assert "snapxo organize" in result.output


def test_an_unknown_command_names_the_way_out(runner):
    result = runner.invoke(main, ["whatevr"])

    assert result.exit_code != 0
    assert "is not a SnapXO command" in result.output
    assert "snapxo --help" in result.output
    # no path, so no organize hint
    assert "To organize it" not in result.output


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
    # the old style, spelled into the help string, should be gone
    assert "(default: 23" not in result.output


def test_every_command_describes_what_it_does(runner):
    for command in ("organize", "merge", "verify", "doctor"):
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output


def test_no_meta_warns_and_stops_without_a_way_to_confirm(runner, export_dir: Path, tmp_path: Path):
    # CliRunner has no terminal, which is also what a script or a CI job has.
    result = runner.invoke(main, ["organize", str(export_dir), "-o", str(tmp_path / "out"),
                                  "--no-meta"])

    assert result.exit_code == 1
    assert "can never be rebuilt" in result.output
    assert "Pass -y if you meant it" in result.output
    assert not (tmp_path / "out").exists()


def test_no_meta_carries_on_with_yes(runner, export_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = runner.invoke(main, ["organize", str(export_dir), "-o", str(out),
                                  "--no-meta", "-y", "--no-encode", "--no-overlay"])

    assert result.exit_code == 0
    assert "can never be rebuilt" in result.output
    assert not (out / "_meta" / "json").exists()
    assert (out / "index.html").is_file()


def test_no_meta_on_a_dry_run_warns_but_never_asks(runner, export_dir: Path, tmp_path: Path):
    result = runner.invoke(main, ["organize", str(export_dir), "--no-meta", "--dry-run",
                                  "--no-encode", "--no-overlay"])

    assert result.exit_code == 0
    assert "can never be rebuilt" in result.output
    assert "Nothing is written on a dry run" in result.output


def test_info_is_a_command_not_a_flag(runner, export_dir: Path):
    result = runner.invoke(main, ["info", str(export_dir)])

    assert result.exit_code == 0
    assert "Step 2: Inspect" in result.output or "Inspect" in result.output

    gone = runner.invoke(main, ["organize", str(export_dir), "--info"])
    assert gone.exit_code != 0
    assert "No such option" in gone.output


def test_info_needs_no_output_folder(runner, export_dir: Path):
    result = runner.invoke(main, ["info", str(export_dir)])

    assert "-o/--output is required" not in result.output


def test_export_is_called_spreadsheet_now(runner, tmp_path: Path):
    result = runner.invoke(main, ["export", str(tmp_path)])

    assert result.exit_code != 0
    assert "is not a SnapXO command" in result.output


def test_the_spreadsheet_command_takes_an_output(runner):
    from snapxo.cli import spreadsheet_command

    assert any(param.name == "output" for param in spreadsheet_command.params)
