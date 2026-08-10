from pathlib import Path

from conftest import write_image

from snapxo.scanner import MediaFile, scan_export


def test_scan_sorts_memories_overlays_chat_and_unknown(export_dir: Path):
    memories = export_dir / "memories"
    write_image(memories / "2026-05-05_1200-abc-overlay.png", "white")
    (memories / "2026-05-06_1200-media.unknown").write_bytes(b"???")

    scan = scan_export(export_dir)

    assert len(scan.memories) == 4
    assert [o.original_name for o in scan.overlays] == ["2026-05-05_1200-abc-overlay.png"]
    assert [c.original_name for c in scan.chat_media] == ["2026-05-04_1400-chatmediaid.jpg"]
    assert [u.name for u in scan.unknown_files] == ["2026-05-06_1200-media.unknown"]


def test_all_media_is_memories_plus_chat_without_overlays(export_dir: Path):
    write_image(export_dir / "memories" / "2026-05-05_1200-abc-overlay.png", "white")

    scan = scan_export(export_dir)

    assert len(scan.all_media) == len(scan.memories) + len(scan.chat_media)
    assert all(not mf.is_overlay for mf in scan.all_media)


def test_scan_reads_date_and_uuid_from_the_name(export_dir: Path):
    uuid = "11111111-2222-3333-4444-555555555555"
    write_image(export_dir / "memories" / f"2026-05-09_1200-{uuid}-media.jpg", "red")

    scan = scan_export(export_dir)
    entry = next(m for m in scan.memories if uuid in m.original_name)

    assert entry.date == "2026-05-09"
    assert entry.uuid == uuid
    assert entry.source == "memory"


def test_scan_falls_back_to_unknown_date(export_dir: Path):
    write_image(export_dir / "memories" / "no-date.jpg", "red")

    scan = scan_export(export_dir)
    entry = next(m for m in scan.memories if m.original_name == "no-date.jpg")

    assert entry.date == "unknown"
    assert entry.uuid is None


def test_scan_of_a_directory_without_media_folders_is_empty(tmp_path: Path):
    scan = scan_export(tmp_path)
    assert scan.memories == [] and scan.chat_media == [] and scan.overlays == []


def test_media_file_type_flags():
    video = MediaFile(path=Path("a.mp4"), date="2026-05-01", uuid=None, ext=".mp4",
                      source="memory", original_name="a.mp4")
    image = MediaFile(path=Path("a.jpg"), date="2026-05-01", uuid=None, ext=".jpg",
                      source="memory", original_name="a.jpg")

    assert video.is_video and not video.is_image
    assert image.is_image and not image.is_video
