# Nothing here uninstalls anything, the check is patched to report it missing.

from pathlib import Path

import pytest

from snapxo import pipeline
from snapxo.config import Config
from snapxo.tools.deps import ffmpeg_missing_message, playwright_missing_message


class NoFFmpeg:
    def check(self):
        return False


def test_encoding_without_ffmpeg_stops_and_says_how_to_install(capsys):
    with pytest.raises(SystemExit):
        pipeline._check_external_tools(Config(), NoFFmpeg())

    printed = capsys.readouterr().out
    assert "ffmpeg is not installed" in printed
    assert "install" in printed.lower()


def test_photos_only_needs_no_ffmpeg_at_all(capsys):
    config = Config(media_types=["photos"], no_encode=True, no_overlay=True)

    pipeline._check_external_tools(config, NoFFmpeg())

    assert "not installed" not in capsys.readouterr().out


def test_asking_for_voice_without_ffprobe_stops(capsys):
    # Without ffprobe every MP4 looks like a video, so nothing would be found.
    config = Config(media_types=["voice"], no_encode=True, no_overlay=True)

    with pytest.raises(SystemExit):
        pipeline._check_external_tools(config, NoFFmpeg())

    printed = capsys.readouterr().out
    assert "--types voice needs ffprobe" in printed


def test_videos_without_ffprobe_only_warns(capsys):
    config = Config(media_types=["videos"], no_encode=True, no_overlay=True)

    pipeline._check_external_tools(config, NoFFmpeg())

    assert "stay MP4 video files" in capsys.readouterr().out


def test_the_install_advice_points_at_flags_that_exist():
    ffmpeg = ffmpeg_missing_message()
    assert "--types photos" in ffmpeg
    assert "--only-videos" not in ffmpeg

    for reason in ("package", "browser"):
        browser = playwright_missing_message(reason)
        assert "snapxo html" in browser

        assert "--conversation-format" not in browser


def test_organize_checks_before_it_extracts(export_dir: Path, output_dir: Path,
                                             monkeypatch: pytest.MonkeyPatch):
    # First, or a missing tool is only found after unpacking gigabytes.
    monkeypatch.setattr(pipeline.FFmpeg, "check", lambda self: False)
    reached = []
    monkeypatch.setattr(pipeline, "scan_export",
                        lambda *a, **kw: reached.append("scan"))

    with pytest.raises(SystemExit):
        pipeline.run_pipeline(Config(inputs=[export_dir], output=output_dir, yes=True))

    assert reached == []
