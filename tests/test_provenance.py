# Where the archive came from, shown on the Stats tab and on the PDF covers.

import json
from pathlib import Path

from snapxo.facts.provenance import archive_facts, fact_rows, provenance_panel


def _archive(tmp_path: Path, **manifest) -> Path:
    folder = tmp_path / "archive"
    (folder / "_meta").mkdir(parents=True)
    base = {"version": 1, "generated": "2026-08-23 10:00:00 UTC",
            "own_username": "testuser", "sources": ["mydata~one.zip"], "files": []}
    base.update(manifest)
    (folder / "_meta" / "manifest.json").write_text(json.dumps(base), encoding="utf-8")
    return folder


def test_the_facts_come_from_the_manifest(tmp_path: Path):
    facts = archive_facts(_archive(tmp_path), [], {})

    assert facts["account"] == "testuser"
    assert facts["sources"] == ["mydata~one.zip"]
    assert facts["built"] == "2026-08-23 10:00:00 UTC"


def test_the_covered_range_spans_media_and_messages(tmp_path: Path):
    file_index = [{"date": "2024-03-01"}, {"date": "2026-01-01"}]
    series = {"months": ["2023-05", "2023-06"], "newest_data": "2026-07-30"}

    facts = archive_facts(_archive(tmp_path), file_index, series)

    assert facts["covered_from"] == "2023-05"
    assert facts["covered_to"] == "2026-07-30"


def test_utc_is_the_default_timezone(tmp_path: Path):
    assert archive_facts(_archive(tmp_path), [], {})["timezone"] == "UTC"


def test_a_folder_without_a_manifest_still_produces_facts(tmp_path: Path):
    empty = tmp_path / "nothing"
    empty.mkdir()

    facts = archive_facts(empty, [], {})

    assert facts["sources"] == []
    assert facts["rendered"]


def test_the_panel_warns_about_expired_messages(tmp_path: Path):
    panel = provenance_panel(archive_facts(_archive(tmp_path), [], {}))

    assert "had not expired" in panel
    assert "About this archive" in panel


def test_sources_are_listed_for_the_reader(tmp_path: Path):
    folder = _archive(tmp_path, sources=["mydata~one.zip", "mydata~two.zip"])

    rows = dict(fact_rows(archive_facts(folder, [], {})))

    assert rows["Built from"] == "mydata~one.zip, mydata~two.zip"
