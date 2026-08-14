from conftest import write_image
from PIL import Image

from snapxo.indexer import build_file_details, build_print_index
from snapxo.thumbs import THUMB_HEIGHT, build_thumbnails, thumb_dir


def _entry(output_dir, name, subfolder="2026", ftype="image", date="2026-05-01"):
    return {
        "new_name": name,
        "subfolder": subfolder,
        "type": ftype,
        "date": date,
        "size": 1234,
        "source": "memory",
        "original_name": f"orig_{name}",
        "dest": str(output_dir / subfolder / name),
    }


def test_thumbnails_are_built_and_reused(output_dir):
    entry = _entry(output_dir, "2026-05-01_0001.jpg")
    write_image(output_dir / "2026" / "2026-05-01_0001.jpg", "red", size=(1200, 1600))

    thumbs = build_thumbnails([entry], output_dir)

    assert thumbs == {0: "_meta/thumbs/2026__2026-05-01_0001.jpg"}
    made = thumb_dir(output_dir) / "2026__2026-05-01_0001.jpg"
    with Image.open(made) as img:
        assert img.height <= THUMB_HEIGHT
    assert made.stat().st_size < (output_dir / "2026" / "2026-05-01_0001.jpg").stat().st_size

    stamp = made.stat().st_mtime_ns
    assert build_thumbnails([entry], output_dir) == thumbs
    assert made.stat().st_mtime_ns == stamp


def test_videos_are_skipped_without_ffmpeg(output_dir):
    entry = _entry(output_dir, "2026-05-01_0001.mp4", ftype="video")
    (output_dir / "2026").mkdir(parents=True)
    (output_dir / "2026" / "2026-05-01_0001.mp4").write_bytes(b"not really a video")

    assert build_thumbnails([entry], output_dir, ff=None) == {}


def test_a_missing_file_gets_no_thumbnail(output_dir):
    assert build_thumbnails([_entry(output_dir, "gone.jpg")], output_dir) == {}


def test_the_print_index_never_lazy_loads(output_dir):
    entries = [_entry(output_dir, "2026-05-01_0001.jpg"), _entry(output_dir, "2026-05-02_0002.mp4", ftype="video")]
    details = build_file_details(entries, {})

    page = build_print_index(entries, details, {0: "_meta/thumbs/a.jpg"})

    assert "loading=" not in page
    assert "<script" not in page
    assert "_meta/thumbs/a.jpg" in page
    # the video has no thumbnail here, so its tile falls back to a placeholder
    assert "Video</div>" in page


def test_the_print_index_carries_the_details_inline(output_dir):
    entry = _entry(output_dir, "2026-05-01_0001.jpg")
    entry["media_id"] = "mediaidone"
    json_data = {
        "chat_history": {
            "john-doe": [{"From": "john-doe", "Media IDs": "mediaidone",
                          "Created": "2026-05-01 14:32:05 UTC", "Conversation Title": "my-group-chat"}]
        }
    }
    details = build_file_details([entry], json_data)

    page = build_print_index([entry], details, {})

    assert "2026-05-01_0001.jpg" in page
    assert "john-doe" in page
    assert "my-group-chat" in page
    assert "2026-05-01 14:32" in page
    assert "1.2 KB" in page
