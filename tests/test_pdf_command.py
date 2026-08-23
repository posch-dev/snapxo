# Rendering needs a browser, so only the parts around it are exercised.

from pathlib import Path

from snapxo import pipeline
from snapxo.config import Config
from snapxo.formats.pdfgen import pdf_dir, render_pdfs


def test_pdf_refuses_a_folder_it_did_not_produce(tmp_path: Path):
    stranger = tmp_path / "holiday-photos"
    stranger.mkdir()

    assert render_pdfs(stranger) is False


def test_a_dry_run_writes_nothing_and_needs_no_browser(export_dir: Path, output_dir: Path):
    pipeline.run_pipeline(Config(inputs=[export_dir], output=output_dir, yes=True,
                                 no_encode=True, no_overlay=True))

    assert render_pdfs(output_dir, dry_run=True) is True
    assert not pdf_dir(output_dir).exists()


def test_the_output_directory_is_named_in_the_dry_run(export_dir: Path, output_dir: Path,
                                                      tmp_path: Path, capsys):
    pipeline.run_pipeline(Config(inputs=[export_dir], output=output_dir, yes=True,
                                 no_encode=True, no_overlay=True))
    elsewhere = tmp_path / "for-printing"

    render_pdfs(output_dir, target=elsewhere, dry_run=True)

    assert "for-printing" in capsys.readouterr().out
    assert not pdf_dir(output_dir).exists()


def test_html_takes_no_output_directory():
    from snapxo.cli import main

    flags = {opt for param in main.commands["html"].params for opt in param.opts}

    assert "-o" not in flags and "--output" not in flags


def test_organize_no_longer_takes_a_format_choice():
    from snapxo.config import Config as ConfigClass

    fields = ConfigClass.__dataclass_fields__
    assert "conversation_format" not in fields
    assert "index_format" not in fields
    assert "stats_format" not in fields


def test_an_attachment_prints_its_details_beside_it():
    from snapxo.parts.messages import _media_html

    entry = {"subfolder": "2026", "new_name": "a.mp4", "type": "video", "size": 2400000,
             "thumb": "_meta/thumbs/x.jpg",
             "media": {"codec": "hevc", "width": 480, "height": 854,
                       "duration": 12.6, "bitrate": 951894}}

    printed = _media_html(entry, pdf_mode=True)

    assert "media-facts" in printed
    assert "480x854" in printed and "hevc" in printed and "0:13" in printed
    # a video has no player on paper, so its still frame stands in
    assert "play-mark" in printed


def test_the_screen_version_keeps_no_details_box():
    from snapxo.parts.messages import _media_html

    entry = {"subfolder": "2026", "new_name": "a.mp4", "type": "video",
             "media": {"codec": "hevc"}}

    assert "media-facts" not in _media_html(entry)


def test_the_plain_gallery_shows_media_and_dates_only():
    from snapxo.formats.plaingallery import build_plain_gallery

    file_index = [{"subfolder": "2026", "new_name": "a.jpg", "type": "image", "date": "2026-05-01"},
                  {"subfolder": "2026", "new_name": "b.mp4", "type": "video", "date": "2026-05-02"}]

    page = build_plain_gallery(file_index, {0: "_meta/thumbs/medium/a.jpg", 1: "_meta/thumbs/b.jpg"})

    assert 'src="_meta/thumbs/medium/a.jpg"' in page
    assert "play-mark" in page
    assert "2026-05-01" in page
    # nothing written over the picture beyond its date
    assert "Encoding" not in page and "Bitrate" not in page


def test_a_file_without_any_preview_still_gets_a_place():
    from snapxo.formats.plaingallery import build_plain_gallery

    page = build_plain_gallery(
        [{"subfolder": "2026", "new_name": "v.mp3", "type": "audio", "date": "2026-05-01"}], {})

    assert "Voice message" in page


def test_the_detail_tables_are_folded_on_screen_and_open_on_paper():
    from snapxo.pages.stats import build_detail_tables

    data = {"friends": {"Friends": [{"Username": "a", "Display Name": "Alice",
                                     "Creation Timestamp": "2026-01-01 10:00:00 UTC"}]}}

    # Chromium prints a closed details as its heading alone, so the PDF gets them open
    assert "<details id=\"friends\">" in build_detail_tables(data)
    assert "<details id=\"friends\" open>" in build_detail_tables(data, expanded=True)


def test_the_plain_gallery_names_the_file_under_the_picture():
    from snapxo.formats.plaingallery import build_plain_gallery

    page = build_plain_gallery(
        [{"subfolder": "2026", "new_name": "2026-05-01_0001.jpg", "type": "image",
          "date": "2026-05-01"}], {0: "_meta/thumbs/medium/a.jpg"})

    assert "2026-05-01_0001.jpg" in page
    assert "2026-05-01" in page
