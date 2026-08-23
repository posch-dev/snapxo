# Measuring duration, codec and pixel size, and keeping the result.

from pathlib import Path

from conftest import write_image

from snapxo.media.mediainfo import attach, describe, human_bitrate, human_duration, measure


class FakeFfmpeg:
    def __init__(self, answer: dict):
        self.answer = answer
        self.calls = 0

    def probe(self, path: Path) -> dict:
        self.calls += 1
        return self.answer


def test_a_picture_is_measured_without_ffmpeg(output_dir: Path):
    path = write_image(output_dir / "2026" / "a.jpg", "red", size=(640, 480))
    entry = {"type": "image", "dest": str(path)}

    assert measure(entry) == {"width": 640, "height": 480, "codec": "jpeg"}


def test_a_video_goes_through_ffprobe(output_dir: Path):
    path = output_dir / "2026" / "a.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not really a video")
    ff = FakeFfmpeg({"codec": "hevc", "duration": 12.6})

    assert measure({"type": "video", "dest": str(path)}, ff) == {"codec": "hevc", "duration": 12.6}
    assert ff.calls == 1


def test_a_video_without_ffmpeg_is_left_alone(output_dir: Path):
    path = output_dir / "2026" / "a.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")

    assert measure({"type": "video", "dest": str(path)}) == {}


def test_a_missing_file_measures_to_nothing():
    assert measure({"type": "image", "dest": "nowhere/at/all.jpg"}) == {}


def test_measuring_twice_costs_nothing_the_second_time(output_dir: Path):
    path = output_dir / "2026" / "a.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    ff = FakeFfmpeg({"codec": "hevc"})
    index = [{"type": "video", "dest": str(path)}]

    assert attach(index, ff) == 1
    assert attach(index, ff) == 0
    assert ff.calls == 1


def test_durations_read_like_a_player_shows_them():
    assert human_duration(29) == "0:29"
    assert human_duration(90) == "1:30"
    assert human_duration(3725) == "1:02:05"
    assert human_duration(None) == ""


def test_a_bitrate_is_shown_in_kbit():
    assert human_bitrate(951894) == "951 kbit/s"
    assert human_bitrate(0) == ""
    assert human_bitrate("nonsense") == ""


def test_one_line_describes_a_video():
    info = {"width": 480, "height": 854, "codec": "hevc", "duration": 12.6, "bitrate": 951894}

    assert describe(info) == "480x854, hevc, 0:13, 951 kbit/s"


def test_an_empty_measurement_describes_to_nothing():
    assert describe({}) == ""
