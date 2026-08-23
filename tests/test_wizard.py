# The questions are answered by feeding keystrokes, the guard is checked alone.

from pathlib import Path

import pytest

from snapxo import wizard
from snapxo.wizard import COMMANDS, NotATerminal, build_arguments, show_command

# Every organize question, in order, answered with Enter.
ORGANIZE_DEFAULTS = ["", "", "", "", "", "", ""]


@pytest.fixture
def answering(monkeypatch):
    # rich decides whether prompting is possible, so pretend it is.
    monkeypatch.setattr(wizard.console, "is_interactive", True)

    def answer(keystrokes: list[str]):
        remaining = list(keystrokes)
        monkeypatch.setattr("rich.prompt.PromptBase.get_input",
                            lambda *args, **kwargs: remaining.pop(0))
        return remaining

    return answer


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    folder = tmp_path / "archive"
    folder.mkdir()
    return folder


def organize_answers(tmp_path: Path, **replace) -> list[str]:
    answers = ["export.zip", str(tmp_path / "out"), *ORGANIZE_DEFAULTS]
    for position, value in replace.items():
        answers[int(position.removeprefix("q"))] = value
    return answers


def test_it_refuses_without_a_terminal(monkeypatch):
    monkeypatch.setattr(wizard.console, "is_interactive", False)

    with pytest.raises(NotATerminal):
        build_arguments("doctor")


def test_the_menu_offers_every_command():
    from snapxo.cli import main

    offered = {name for name, _ in COMMANDS}
    assert offered == set(main.commands)


def test_pressing_enter_through_organize_matches_the_plain_command(answering, tmp_path: Path):
    answering(organize_answers(tmp_path))

    args = build_arguments("organize")

    assert args[0] == "organize"
    assert "--media" not in args
    assert "--types" not in args
    assert "--no-encode" not in args
    assert "--timezone" not in args
    assert args[-1] == "--yes"


def test_declining_a_step_adds_its_skip_flag(answering, tmp_path: Path):
    # q4 is the encoding question, after the two media questions
    answering(organize_answers(tmp_path, q4="n"))

    assert "--no-encode" in build_arguments("organize")


def test_the_media_questions_come_before_the_encoding_one(answering, tmp_path: Path):
    # photos only, so the encoding question is never asked
    answering(["export.zip", str(tmp_path / "out"), "", "1", "", "", "", ""])

    args = build_arguments("organize")

    assert args[args.index("--types") + 1] == "photos"
    assert "--no-encode" not in args


def test_naming_one_source_passes_it_through(answering, tmp_path: Path):
    answering(organize_answers(tmp_path, q2="1"))

    args = build_arguments("organize")

    assert args[args.index("--media") + 1] == "memories"


def test_picking_everything_is_the_same_as_pressing_enter(answering, tmp_path: Path):
    answering(organize_answers(tmp_path, q2="1,2"))

    assert "--media" not in build_arguments("organize")


def test_the_checksum_question_is_gone(answering, tmp_path: Path):
    # Fingerprinting is on by default, so there is nothing left to ask.
    answering(organize_answers(tmp_path))

    args = build_arguments("organize")

    assert "--checksums" not in args
    assert "--no-checksums" not in args


def test_the_menu_picks_the_matching_command(answering, archive: Path):
    position = [name for name, _ in COMMANDS].index("rebuild") + 1
    answering([str(position), str(archive), ""])

    assert build_arguments() == ["rebuild", str(archive)]


def test_cancelling_the_menu_exits_quietly(answering):
    answering(["0"])

    with pytest.raises(SystemExit) as exit_info:
        build_arguments()
    assert exit_info.value.code == 0


def test_info_only_asks_where_the_export_is(answering):
    answering(["mydata.zip"])

    assert build_arguments("info") == ["info", "mydata.zip"]


def test_html_offers_the_filters(answering, archive: Path):
    answering([str(archive), "y", "someone,another", "5", ""])

    args = build_arguments("html")

    assert args[args.index("--chats-with") + 1] == "someone,another"
    assert args[args.index("--min-messages") + 1] == "5"


def test_html_leaves_the_filters_out_by_default(answering, archive: Path):
    answering([str(archive), "", "", ""])

    args = build_arguments("html")

    assert args == ["html", str(archive)]


def test_pdf_offers_the_picture_book(answering, archive: Path):
    from snapxo.wizard import PDF_PARTS

    assert "--media-plain" in [flag for flag, _ in PDF_PARTS]

    position = [flag for flag, _ in PDF_PARTS].index("--media-plain") + 1
    answering([str(archive), "n", str(position)])

    assert build_arguments("pdf") == ["pdf", str(archive), "--media-plain"]


def test_spreadsheet_asks_for_a_format(answering, archive: Path):
    answering([str(archive), "2", ""])

    args = build_arguments("spreadsheet")

    assert args[args.index("--format") + 1] == "ods"


def test_docker_always_ends_up_with_an_access_decision(answering, archive: Path):
    answering([str(archive), "", "", ""])

    args = build_arguments("docker")

    assert ("--password" in args) != ("--no-auth" in args)


def test_deleting_the_merge_sources_defaults_to_no(answering, archive: Path, tmp_path: Path):
    second = tmp_path / "second"
    second.mkdir()
    answering([str(archive), str(second), "", str(tmp_path / "merged"), ""])

    assert "--delete-sources" not in build_arguments("merge")


def test_a_bad_folder_is_asked_again(answering, archive: Path):
    answering(["not-a-folder", str(archive), ""])

    assert build_arguments("rebuild") == ["rebuild", str(archive)]


def test_the_equivalent_command_line_is_shown(answering, capsys, archive: Path):
    show_command(["rebuild", str(archive)])

    assert "snapxo rebuild" in capsys.readouterr().out


def test_saying_yes_to_a_timezone_adds_the_flag(answering, tmp_path: Path):
    # last two: yes to converting, then the default zone
    answering([*organize_answers(tmp_path, q8="y"), ""])

    args = build_arguments("organize")

    assert "--timezone" in args
    assert args[args.index("--timezone") + 1] == "UTC"


def test_the_zone_list_covers_more_than_europe():
    from snapxo.clock import COMMON_ZONES, is_known

    assert len(COMMON_ZONES) > 40
    for region in ("Europe/", "America/", "Asia/", "Africa/", "Australia/", "Pacific/"):
        assert any(zone.startswith(region) for zone in COMMON_ZONES), region
    # Russia end to end, since it spans eleven of them
    assert "Europe/Moscow" in COMMON_ZONES
    assert "Asia/Vladivostok" in COMMON_ZONES
    assert all(is_known(zone) for zone in COMMON_ZONES)
