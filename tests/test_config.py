from snapxo.config import Config


def test_a_plain_config_processes_everything():
    c = Config()

    assert c.has_only_filter is False
    assert c.should_process_media()
    assert c.should_process_conversations()
    assert c.should_process_stats()
    assert c.should_process_map()
    assert c.should_process_stickers()
    assert c.should_process_meta()
    assert c.should_encode()
    assert c.should_overlay()
    assert c.should_exif()
    assert c.should_dedup()
    assert c.should_index()


def test_a_no_flag_turns_its_step_off():
    assert not Config(no_encode=True).should_encode()
    assert not Config(no_overlay=True).should_overlay()
    assert not Config(no_exif=True).should_exif()
    assert not Config(no_dedup=True).should_dedup()
    assert not Config(no_index=True).should_index()
    assert not Config(no_conversations=True).should_process_conversations()
    assert not Config(no_stats=True).should_process_stats()
    assert not Config(no_map=True).should_process_map()
    assert not Config(no_stickers=True).should_process_stickers()
    assert not Config(no_meta=True).should_process_meta()


def test_only_conversations_skips_media_and_everything_else():
    c = Config(only_conversations=True)

    assert c.has_only_filter
    assert c.should_process_conversations()
    assert not c.should_process_media()
    assert not c.should_process_stats()
    assert not c.should_process_map()
    assert not c.should_encode()
    assert not c.should_index()


def test_only_filters_combine():
    # One run can rebuild several outputs, which is what the PDF example relies on.
    c = Config(only_conversations=True, only_stats=True)

    assert c.should_process_conversations()
    assert c.should_process_stats()
    assert not c.should_process_map()


def test_media_only_filters_keep_the_media_steps():
    for kwargs in ({"only_media": True}, {"only_memories": True}, {"only_chat_media": True},
                   {"only_photos": True}, {"only_videos": True}, {"only_voice": True}):
        c = Config(**kwargs)
        assert c.should_process_media(), kwargs
        assert c.should_encode(), kwargs


def test_meta_is_never_written_when_a_filter_is_set():
    # There is no --only-meta, so any filter means the raw copy is off.
    assert not Config(only_stats=True).should_process_meta()


def test_a_no_flag_wins_over_its_only_flag():
    assert not Config(only_stats=True, no_stats=True).should_process_stats()
    assert not Config(only_media=True, no_encode=True).should_encode()
