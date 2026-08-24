import pytest

from snapxo.config import Config
from snapxo.selection import SOURCES, TYPES, parse


def test_a_plain_config_processes_everything():
    c = Config()

    assert c.selection.is_everything
    assert c.should_process_meta()
    assert c.should_encode()
    assert c.should_overlay()
    assert c.should_exif()
    assert c.should_dedup()


def test_a_no_flag_turns_its_step_off():
    assert not Config(no_encode=True).should_encode()
    assert not Config(no_overlay=True).should_overlay()
    assert not Config(no_exif=True).should_exif()
    assert not Config(no_dedup=True).should_dedup()
    assert not Config(no_meta=True).should_process_meta()


def test_narrowing_the_media_never_costs_the_raw_export():
    # It used to: any --only flag silently skipped _meta/json, killing rebuild.
    assert Config(media_sources=["memories"]).should_process_meta()
    assert Config(media_types=["photos"]).should_process_meta()


def test_an_empty_list_means_everything_on_that_axis():
    c = Config()

    assert all(c.selection.wants_source(name) for name in SOURCES)
    assert all(c.selection.wants_type(name) for name in TYPES)


def test_a_named_list_keeps_only_what_it_names():
    c = Config(media_sources=["memories"], media_types=["photos", "voice"])

    assert c.selection.wants_source("memories")
    assert not c.selection.wants_source("chat")
    assert c.selection.wants_type("photos")
    assert c.selection.wants_type("voice")
    assert not c.selection.wants_type("videos")


def test_asking_for_photos_alone_skips_the_encoding_and_the_probing():
    c = Config(media_types=["photos"])

    assert not c.should_encode()
    # Telling a voice message from a video costs a probe of every video.
    assert not c.selection.needs_voice_detection


def test_videos_or_voice_both_need_the_probe():
    assert Config(media_types=["videos"]).selection.needs_voice_detection
    assert Config(media_types=["voice"]).selection.needs_voice_detection


def test_the_parser_keeps_the_documented_order():
    assert parse("voice,photos", TYPES, "--types") == ["photos", "voice"]
    assert parse("  Chat , memories ", SOURCES, "--media") == ["memories", "chat"]


def test_an_empty_value_parses_to_everything():
    assert parse("", TYPES, "--types") == []


def test_an_unknown_name_says_what_is_allowed():
    with pytest.raises(ValueError) as problem:
        parse("audio", TYPES, "--types")

    assert "audio" in str(problem.value)
    assert "photos, videos, voice" in str(problem.value)
