# The sidecar data files the app loads.

from pathlib import Path

from snapxo.app.data import build_chats_payload, build_media_payload, write_chats_data


def _json_data() -> dict:
    return {
        "account": {"Basic Information": {"Username": "testuser"}},
        "chat_history": {
            "friend_one": [
                {"From": "friend_one", "IsSender": False, "Media Type": "TEXT",
                 "Created": "2026-05-01 12:00:00 UTC", "Content": "first hello"},
                {"From": "testuser", "IsSender": True, "Media Type": "TEXT",
                 "Created": "2026-05-01 12:01:00 UTC", "Content": "hi there"},
            ],
            "friend_two": [
                {"From": "friend_two", "IsSender": False, "Media Type": "TEXT",
                 "Created": "2026-07-01 12:00:00 UTC", "Content": "later message"},
            ],
        },
    }


def test_every_chat_carries_its_rendered_messages():
    chats = build_chats_payload(_json_data())["chats"]

    assert len(chats) == 2
    assert "first hello" in "".join(chat["b"] for chat in chats)


def test_chats_are_ordered_by_last_activity():
    chats = build_chats_payload(_json_data())["chats"]

    assert [chat["t"] for chat in chats] == ["friend_two", "friend_one"]


def test_the_search_index_carries_anchors_that_exist_in_the_body():
    chat = build_chats_payload(_json_data())["chats"][1]

    for entry in chat["x"]:
        assert f'id="{entry["a"]}"' in chat["b"]


def test_media_paths_are_relative_to_the_output_root():
    media_map = {"mediaidone": {"subfolder": "2026", "new_name": "2026-05-01_0001.jpg",
                                "type": "image", "thumb": "_meta/thumbs/a.jpg"}}
    data = {"chat_history": {"friend_one": [
        {"From": "friend_one", "IsSender": False, "Media Type": "MEDIA",
         "Created": "2026-05-01 12:00:00 UTC", "Media IDs": "mediaidone"},
    ]}}

    body = build_chats_payload(data, media_map)["chats"][0]["b"]

    # the app sits at the root, unlike conversations/*.html which need ../
    assert 'src="_meta/thumbs/a.jpg"' in body
    assert 'href="2026/2026-05-01_0001.jpg"' in body
    assert "../" not in body


def test_the_data_file_is_javascript_not_json(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    write_chats_data(output_dir, _json_data())

    written = (output_dir / "_meta" / "app-chats.js").read_text(encoding="utf-8")
    assert written.startswith("window.SNAPXO_CHATS=")


def test_closing_script_tags_in_a_message_cannot_end_the_script(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    data = {"chat_history": {"friend_one": [
        {"From": "friend_one", "IsSender": False, "Media Type": "TEXT",
         "Created": "2026-05-01 12:00:00 UTC", "Content": "</script> gotcha"},
    ]}}

    write_chats_data(output_dir, data)

    written = (output_dir / "_meta" / "app-chats.js").read_text(encoding="utf-8")
    assert "</script>" not in written
    assert "<\\/script>" in written


def test_an_export_without_chats_writes_an_empty_payload(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    assert write_chats_data(output_dir, {})["chats"] == []
    assert (output_dir / "_meta" / "app-chats.js").is_file()


def test_media_items_are_newest_first_and_keep_their_year():
    file_index = [
        {"subfolder": "2025", "new_name": "old.jpg", "type": "image", "date": "2025-01-01"},
        {"subfolder": "2026", "new_name": "new.jpg", "type": "image", "date": "2026-01-01"},
    ]

    items = build_media_payload(file_index, {1: "_meta/thumbs/new.jpg"})["items"]

    assert [item["f"] for item in items] == ["2026/new.jpg", "2025/old.jpg"]
    assert items[0]["y"] == "2026"
    assert items[0]["t"] == "_meta/thumbs/new.jpg"
    assert items[1]["t"] == ""


def test_media_entries_without_a_name_are_dropped():
    assert build_media_payload([{"subfolder": "2026", "type": "image"}], {})["items"] == []
