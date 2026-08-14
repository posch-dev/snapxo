import json
import re

from snapxo.chats import build_chats_html, generate_chats_html, message_anchor
from snapxo.conversations import generate_conversation_html, generate_conversations


def _records():
    return [
        {"title": "john-doe", "file": "conversations/john-doe.html", "is_group": False, "messages": 2,
         "last": "2026-07-20 14:32:05 UTC", "preview": "see you",
         "index": [{"a": "m0", "s": "john-doe", "t": "2026-07-20 14:30:00 UTC", "x": "pizza tonight"},
                   {"a": "m1", "s": "testuser", "t": "2026-07-20 14:32:05 UTC", "x": "see you"}]},
        {"title": "my-group-chat", "file": "conversations/group_my-group-chat.html", "is_group": True,
         "messages": 1, "last": "2026-05-03 10:00:00 UTC", "preview": "group hello",
         "index": [{"a": "m0", "s": "max_mustermann", "t": "2026-05-03 10:00:00 UTC", "x": "group hello"}]},
    ]


def _payload(page):
    return json.loads(re.search(r"window\.__SEO_CHATS = (\{.*?\});", page, re.S).group(1))


def test_the_list_is_sorted_by_recency(tmp_path):
    page = build_chats_html(_records())

    assert page.index("john-doe") < page.index("my-group-chat")
    assert _payload(page)["chats"][0]["t"] == "john-doe"


def test_every_message_is_searchable(tmp_path):
    data = _payload(build_chats_html(_records()))

    assert len(data["msgs"]) == 3
    assert {m["x"] for m in data["msgs"]} == {"pizza tonight", "see you", "group hello"}
    # a hit knows its chat and its anchor
    hit = next(m for m in data["msgs"] if m["x"] == "pizza tonight")
    assert data["chats"][hit["c"]]["f"] == "conversations/john-doe.html"
    assert hit["a"] == "m0"


def test_pdf_chats_say_that_anchors_do_not_work():
    records = _records()
    for r in records:
        r["file"] = r["file"].replace(".html", ".pdf")

    assert "without jumping to the message" in build_chats_html(records)
    assert "without jumping to the message" not in build_chats_html(_records())


def test_a_group_is_marked_as_one():
    page = build_chats_html(_records())

    assert 'class="group-badge">Group' in page


def test_no_page_without_chats(tmp_path):
    assert generate_chats_html([], tmp_path) is False
    assert not (tmp_path / "chats.html").exists()


def test_anchors_match_between_page_and_conversation(tmp_path, export_dir):
    json_data = {
        "account": {"Basic Information": {"Username": "testuser"}},
        "chat_history": {
            "john-doe": [
                {"From": "john-doe", "IsSender": False, "Media Type": "TEXT",
                 "Created": "2026-07-20 14:30:00 UTC", "Content": "pizza tonight"},
                {"From": "testuser", "IsSender": True, "Media Type": "TEXT",
                 "Created": "2026-07-20 14:32:05 UTC", "Content": "see you"},
            ]
        },
    }
    out = tmp_path / "out"
    out.mkdir()

    generate_conversations(json_data, out)

    page = (out / "chats.html").read_text(encoding="utf-8")
    conversation = (out / "conversations" / "john-doe.html").read_text(encoding="utf-8")
    for hit in _payload(page)["msgs"]:
        assert f'id="{hit["a"]}"' in conversation


def test_messages_carry_an_anchor():
    messages = [{"sender": "john-doe", "is_own": False, "text": "hello", "media_type": "TEXT",
                 "timestamp": "2026-07-20 14:30:00 UTC", "conversation_title": None, "media_ids": ""}]

    page = generate_conversation_html("john-doe", messages)

    assert f'id="{message_anchor(0)}"' in page


def test_conversation_images_use_the_thumbnail_but_link_the_full_file():
    from snapxo.conversations import _media_html

    entry = {"subfolder": "2026", "new_name": "2026-05-04_0005.jpg", "type": "image",
             "thumb": "_meta/thumbs/2026__2026-05-04_0005.jpg"}

    html = _media_html(entry)
    assert 'src="../_meta/thumbs/2026__2026-05-04_0005.jpg"' in html
    assert 'href="../2026/2026-05-04_0005.jpg"' in html

    # the PDF prints the image far larger than a chat bubble, so it keeps the original
    assert 'src="../2026/2026-05-04_0005.jpg"' in _media_html(entry, pdf_mode=True)


def test_an_image_without_a_thumbnail_falls_back_to_the_full_file():
    from snapxo.conversations import _media_html

    entry = {"subfolder": "2026", "new_name": "2026-05-04_0005.jpg", "type": "image"}

    assert 'src="../2026/2026-05-04_0005.jpg"' in _media_html(entry)
