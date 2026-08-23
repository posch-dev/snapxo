import json
import os
import shutil
from pathlib import Path

# Rich wraps at the console width, and the messages carry temp paths whose length
# differs per platform. Without this the assertions about a message's text break
# wherever the wrap happens to land.
os.environ["COLUMNS"] = "1000"

import pytest
from PIL import Image


def write_image(path: Path, color: str = "red", size: tuple[int, int] = (32, 32)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


@pytest.fixture
def export_dir(tmp_path: Path) -> Path:
    # Images only, so nothing in the pipeline reaches for ffmpeg or ffprobe.
    root = tmp_path / "export"
    memories = root / "memories"
    chat = root / "chat_media"
    js = root / "json"
    html = root / "html"
    for d in (memories, chat, js, html):
        d.mkdir(parents=True)

    (html / "chat_history.html").write_text("<html>chat</html>", encoding="utf-8")

    write_image(memories / "2026-05-01_1200-media.jpg", "red")
    write_image(memories / "2026-05-02_1200-media.jpg", "green")
    write_image(memories / "2026-05-03_1200-media.jpg", "blue")
    # a copy, so dedup has something to find
    shutil.copy2(memories / "2026-05-01_1200-media.jpg", memories / "2026-05-01_1201-media.jpg")
    write_image(chat / "2026-05-04_1400-chatmediaid.jpg", "yellow")

    (js / "account.json").write_text(
        json.dumps({"Basic Information": {"Username": "testuser"}}), encoding="utf-8"
    )
    (js / "chat_history.json").write_text(
        json.dumps({
            "friend_one": [
                {"From": "friend_one", "IsSender": False, "Media Type": "TEXT",
                 "Created": "2026-05-01 12:00:00 UTC", "Content": "hey"},
                {"From": "testuser", "IsSender": True, "Media Type": "TEXT",
                 "Created": "2026-05-01 12:01:00 UTC", "Content": "hi"},
            ],
        }),
        encoding="utf-8",
    )
    (js / "memories_history.json").write_text(
        json.dumps({
            "Saved Media": [
                {"Date": "2026-05-01 12:00:00 UTC", "Media Type": "Image",
                 "Location": "Latitude, Longitude: 48.20000, 16.30000"},
            ]
        }),
        encoding="utf-8",
    )
    return root


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    return tmp_path / "out"
