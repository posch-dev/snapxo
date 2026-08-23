# index.html, the page with the tabs.

from pathlib import Path

from snapxo.app.shell import OVERVIEW_CARDS, generate_app, initials


def _file_stats(**overrides) -> dict:
    stats = {"images": 0, "videos": 0, "overlays": 0,
             "chat_media_img": 0, "chat_media_vid": 0, "chat_media_other": 0}
    stats.update(overrides)
    return stats


def _json_data() -> dict:
    return {
        "account": {"Basic Information": {"Username": "testuser"}},
        "chat_history": {"friend_one": [
            {"From": "friend_one", "IsSender": False, "Media Type": "TEXT",
             "Created": "2026-05-01 12:00:00 UTC", "Content": "hey"},
            {"From": "testuser", "IsSender": True, "Media Type": "TEXT",
             "Created": "2026-06-01 12:01:00 UTC", "Content": "hi"},
        ]},
        "friends": {"Friends": [{"Username": "friend_one",
                                 "Creation Timestamp": "2026-04-01 10:00:00 UTC"}]},
        "snap_history": {"friend_one": [
            {"From": "friend_one", "Media Type": "IMAGE",
             "Created": "2026-05-02 10:00:00 UTC", "IsSender": False},
        ]},
    }


def _write_app(output_dir: Path, json_data: dict, file_index=None, thumbs=None) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_app(output_dir, json_data, file_index or [], _file_stats(), thumbs=thumbs)
    return (output_dir / "index.html").read_text(encoding="utf-8")


def test_the_app_has_a_panel_for_every_tab(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    for tab in ("overview", "stats", "media", "chats"):
        assert f'id="tab-{tab}"' in page
        assert f'data-tab="{tab}"' in page


def test_only_the_dashboard_tab_starts_visible(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert page.count('class="tab-panel active"') == 1
    assert 'class="tab-panel active" id="tab-overview"' in page


def test_the_overview_shows_a_subset_of_the_stat_cards(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    overview = page.split('id="tab-stats"')[0]
    stats = page.split('id="tab-stats"')[1]
    assert "Overlays" not in overview
    assert "Overlays" in stats
    assert any(label in overview for label in OVERVIEW_CARDS)


def test_the_busiest_chats_reach_the_overview(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert 'data-open-chat="friend_one"' in page


def test_recent_media_uses_the_thumbnails(output_dir: Path):
    file_index = [{"subfolder": "2026", "new_name": "2026-05-01_0001.jpg",
                   "type": "image", "date": "2026-05-01", "source": "memory"}]

    page = _write_app(output_dir, _json_data(), file_index, thumbs={0: "_meta/thumbs/a.jpg"})

    assert 'src="_meta/thumbs/a.jpg"' in page
    assert 'href="2026/2026-05-01_0001.jpg"' in page


def test_an_export_without_snaps_friends_or_ranking_still_builds(output_dir: Path):
    minimal = {"chat_history": {"friend_one": [
        {"From": "friend_one", "IsSender": False, "Media Type": "TEXT",
         "Created": "2026-05-01 12:00:00 UTC", "Content": "hey"},
    ]}}

    page = _write_app(output_dir, minimal)

    assert 'id="tab-stats"' in page
    assert "Snapscore" not in page


def test_an_empty_export_still_builds_a_page(output_dir: Path):
    page = _write_app(output_dir, {})

    assert 'id="tab-overview"' in page
    assert "No conversations in this export." in page


def test_chat_names_are_escaped(output_dir: Path):
    data = {"chat_history": {'<script>alert(1)</script>': [
        {"From": "x", "IsSender": False, "Media Type": "TEXT",
         "Created": "2026-05-01 12:00:00 UTC", "Content": "hey"},
    ]}}

    page = _write_app(output_dir, data)

    assert "<script>alert(1)</script>" not in page


def test_initials_cope_with_the_shapes_snapchat_produces():
    assert initials("john-doe") == "JD"
    assert initials("john.doe") == "JD"
    assert initials("johndoe") == "JO"
    assert initials("") == "?"


def test_the_chats_tab_has_both_searches(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert 'id="chat-query"' in page
    assert 'id="chat-inner-query"' in page
    assert 'id="chat-list"' in page
    assert 'id="chat-body"' in page


def test_the_chat_data_travels_in_a_sidecar_file(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert '<script src="_meta/app-chats.js">' in page
    assert (output_dir / "_meta" / "app-chats.js").is_file()


def test_every_script_except_the_data_is_inlined(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    # only the bulk data is loaded, everything executable is in the page
    sources = [line for line in page.splitlines() if "<script src=" in line]
    assert sources == ['<script src="_meta/app-chats.js"></script>',
                       '<script src="_meta/app-media.js"></script>',
                       '<script src="_meta/app-stats.js"></script>']


def test_the_media_tab_has_filters_and_a_scroll_sentinel(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert 'data-media-filter="all"' in page
    assert 'data-media-filter="video"' in page
    assert 'id="media-grid"' in page
    assert 'id="media-sentinel"' in page


def test_the_details_overlay_is_in_the_page_once(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert page.count('id="detail-overlay"') == 1


def test_the_map_opens_in_a_new_tab_and_is_set_apart(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert 'class="nav-map" href="map.html" target="_blank"' in page
    assert ".nav-map {" in page


def test_the_author_is_credited_with_a_link(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert 'href="https://github.com/posch-dev" target="_blank"' in page
    assert "posch-dev</a>" in page


def test_the_nav_says_when_the_pages_were_written(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert "Last updated at" in page


def test_the_map_button_sits_with_the_tabs(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    tabs = page.split('<nav class="tab-buttons">')[1].split("</nav>")[0]
    assert 'class="nav-map"' in tabs
    assert 'data-tab="chats"' in tabs


def test_recent_media_shows_files_without_a_preview_too(output_dir: Path):
    file_index = [{"subfolder": "2026", "new_name": "voice.mp3", "type": "audio",
                   "date": "2026-09-01", "source": "chat"}]

    page = _write_app(output_dir, _json_data(), file_index, thumbs={})

    # the newest file is a voice message, and it must not be silently skipped
    assert 'href="2026/voice.mp3"' in page


def test_the_stats_tab_uses_a_grouped_table_not_tiles(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    stats = page.split('id="tab-stats"')[1]
    assert 'class="stat-table"' in stats
    assert "<h3>Messages</h3>" in stats
    assert "<h3>People</h3>" in stats


def test_one_switch_folds_all_charts_and_starts_open(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    # one details around the whole grid, not one per chart
    assert '<details class="charts-fold" open>' in page
    assert page.count('<details class="charts-fold"') == 1
    assert '<section class="chart-card">' in page


def test_the_account_row_sits_at_the_bottom_of_its_column(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert '<section class="stat-block bottom"><h3>Account</h3>' in page
    assert page.count('class="stat-column"') == 2


def test_the_stat_labels_use_icons_and_no_emoji(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    stats = page.split('id="tab-stats"')[1].split('id="tab-media"')[0]
    assert '<svg class="icon"' in stats
    assert not any(ord(character) > 0x2100 for character in stats)


def test_the_date_picker_offers_patterns_not_example_dates(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert "Date formatting" in page
    assert ">YYYY-MM-DD<" in page
    assert ">DD Month YYYY<" in page
    assert ">2026-07-20<" not in page


def test_the_details_panel_finds_the_media_data(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    # the details script reads __SEO_DETAILS, the app keeps them in SNAPXO_MEDIA
    assert "window.__SEO_DETAILS = (window.SNAPXO_MEDIA || {}).details || {};" in page
    assert page.index("app-media.js") < page.index("__SEO_DETAILS")


def test_every_chart_and_table_carries_an_info_and_export_button(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert 'data-info="messages-over-time"' in page
    assert 'data-export="messages-over-time"' in page
    assert 'data-export="who-writes-you-most"' in page
    # only the ones that really draw something offer the picture
    assert 'data-export="type-distribution" data-export-chart="1"' in page
    assert 'data-export="who-writes-you-most" title=' in page


def test_the_stats_tab_ends_with_export_all(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    stats = page.split('id="tab-stats"')[1].split('id="tab-media"')[0]
    assert "data-export-all" in stats
    assert "Export all stats" in stats


def test_the_datasets_travel_in_their_own_file(output_dir: Path):
    _write_app(output_dir, _json_data())

    written = (output_dir / "_meta" / "app-stats.js").read_text(encoding="utf-8")
    assert written.startswith("window.SNAPXO_STATS=")
    assert '"key":"messages-over-time"' in written


def test_a_way_back_to_the_top_of_a_long_tab(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert 'id="to-top"' in page
    # hidden until there is something to scroll back from
    assert ".to-top { position: fixed" in page
    assert "window.scrollY > APPEARS_AFTER" in page


def test_the_last_updated_line_follows_the_date_format(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    line = page.split('class="nav-freshness"')[1].split("</span>")[0]
    assert "data-date=" in line and "data-time=" in line


def test_a_chat_can_be_printed_with_its_own_cover(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    assert 'id="chat-export"' in page
    assert 'id="chat-cover"' in page
    # the cover is for the print only, never for the page on screen
    assert "#chat-cover { display: none; }" in page
    assert "body.printing-chat #chat-cover { display: block; }" in page
    # and the print drops everything that is not the conversation
    assert "body.printing-chat .chat-list-pane" in page


def test_the_chat_header_waits_for_a_chat(output_dir: Path):
    page = _write_app(output_dir, _json_data())

    # display:flex would otherwise beat the hidden attribute
    assert ".chat-view-head[hidden] { display: none; }" in page
