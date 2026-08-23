# The one page per topic versions, written beside index.html.

from pathlib import Path

from snapxo import pipeline
from snapxo.config import Config
from snapxo.pages.loose import write_loose_pages


def organized_folder(export_dir: Path, output_dir: Path) -> Path:
    pipeline.run_pipeline(Config(inputs=[export_dir], output=output_dir, yes=True,
                                 no_encode=True, no_overlay=True))
    return output_dir


def test_it_writes_a_page_per_topic(export_dir: Path, output_dir: Path):
    folder = organized_folder(export_dir, output_dir)

    assert write_loose_pages(folder) is True

    assert (folder / "gallery.html").is_file()
    assert (folder / "stats.html").is_file()
    assert (folder / "chats.html").is_file()
    assert list((folder / "conversations").glob("*.html"))


def test_the_app_is_left_alone(export_dir: Path, output_dir: Path):
    folder = organized_folder(export_dir, output_dir)
    before = (folder / "index.html").read_bytes()

    write_loose_pages(folder)

    assert (folder / "index.html").read_bytes() == before


def test_a_named_contact_is_the_only_conversation_written(export_dir: Path, output_dir: Path):
    folder = organized_folder(export_dir, output_dir)

    write_loose_pages(folder, chats_with=["friend_one"])

    assert [p.name for p in (folder / "conversations").glob("*.html")] == ["friend_one.html"]


def test_a_name_nobody_has_writes_no_conversation(export_dir: Path, output_dir: Path):
    # A fresh folder, since an earlier run's files are never deleted.
    folder = organized_folder(export_dir, output_dir)

    write_loose_pages(folder, chats_with=["nobody_at_all"])

    assert not list((folder / "conversations").glob("*.html"))


def test_min_messages_drops_the_short_ones(export_dir: Path, output_dir: Path):
    folder = organized_folder(export_dir, output_dir)

    write_loose_pages(folder, min_messages=99)

    assert not list((folder / "conversations").glob("*.html"))


def test_a_dry_run_writes_nothing(export_dir: Path, output_dir: Path):
    folder = organized_folder(export_dir, output_dir)

    assert write_loose_pages(folder, dry_run=True) is True

    assert not (folder / "gallery.html").exists()
    assert not (folder / "conversations").exists()


def test_a_folder_that_is_not_an_archive_is_refused(tmp_path: Path, capsys):
    assert write_loose_pages(tmp_path) is False
    assert "no _meta/manifest.json" in capsys.readouterr().out


def test_a_no_meta_folder_says_what_is_missing(export_dir: Path, output_dir: Path, capsys):
    pipeline.run_pipeline(Config(inputs=[export_dir], output=output_dir, yes=True,
                                 no_encode=True, no_overlay=True, no_meta=True))
    capsys.readouterr()

    assert write_loose_pages(output_dir) is False
    assert "no _meta/json" in capsys.readouterr().out
