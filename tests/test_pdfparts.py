from pathlib import Path

from snapxo.formats.pdfgen import MEDIA_PLAIN, _render_media
from snapxo.formats.pdfparts import part_name, plan_parts, render_group


def test_parts_close_before_they_pass_the_target():
    assert plan_parts([40, 40, 40, 10, 90], target=95) == [[0, 1], [2, 3], [4]]


def test_a_single_file_above_the_target_still_gets_a_part():
    assert plan_parts([200, 5], target=95) == [[0], [1]]


def test_part_numbers_are_padded_to_sort_right():
    assert part_name("media-plain-2023", 1, 1) == "media-plain-2023-part-1-of-1.pdf"
    assert part_name("anna", 3, 12) == "anna-part-03-of-12.pdf"


def _writer(true_sizes: list[int], calls: list[int] | None = None):
    def render_part(positions, number, total, pdf_path: Path) -> bool:
        if calls is not None:
            calls.append(total)
        pdf_path.write_bytes(b"x" * sum(true_sizes[p] for p in positions))
        return True
    return render_part


def test_an_underestimate_is_split_again_until_every_part_fits(tmp_path):
    # Every file turns out twice as big as estimated.
    estimates = [30] * 10
    calls: list[int] = []
    final = tmp_path / "2023"

    assert render_group(final, "x-2023", estimates, _writer([60] * 10, calls), limit=110, target=95)

    sizes = [pdf.stat().st_size for pdf in final.iterdir()]
    assert max(sizes) <= 110
    assert sum(sizes) == 600
    assert len(sizes) > 4
    assert sorted(p.name for p in final.iterdir())[0].endswith(f"-of-{len(sizes)}.pdf")


def test_a_failed_render_leaves_the_old_parts_alone(tmp_path):
    final = tmp_path / "2023"
    final.mkdir()
    (final / "x-2023-part-1-of-1.pdf").write_bytes(b"old")

    def failing(positions, number, total, pdf_path):
        return False

    assert not render_group(final, "x-2023", [10, 10], failing)
    assert (final / "x-2023-part-1-of-1.pdf").read_bytes() == b"old"


def test_a_rerender_replaces_the_old_parts_whole(tmp_path):
    final = tmp_path / "2023"
    final.mkdir()
    (final / "x-2023-part-1-of-2.pdf").write_bytes(b"old")

    assert render_group(final, "x-2023", [10], _writer([10]), limit=110, target=95)

    assert [p.name for p in final.iterdir()] == ["x-2023-part-1-of-1.pdf"]
    assert not list(tmp_path.glob(".*"))


def test_a_swap_cut_short_is_undone_on_the_next_run(tmp_path):
    final = tmp_path / "2023"
    stranded = tmp_path / ".2023.old"
    stranded.mkdir()
    (stranded / "x-2023-part-1-of-1.pdf").write_bytes(b"old")

    def failing(positions, number, total, pdf_path):
        return False

    render_group(final, "x-2023", [10], failing)

    assert (final / "x-2023-part-1-of-1.pdf").read_bytes() == b"old"


class _FakeRenderer:
    def __init__(self, works: bool):
        self.works = works

    def render(self, source, pdf_path, **_):
        if self.works:
            pdf_path.write_bytes(b"%PDF")
        return self.works


def _media(tmp_path: Path, works: bool) -> bool:
    file_index = [{"subfolder": "2023", "new_name": "a.jpg", "type": "image", "date": "2023-05-01"},
                  {"subfolder": "2024", "new_name": "b.jpg", "type": "image", "date": "2024-05-01"}]
    facts = {"account": "", "covered_from": "", "covered_to": "", "built": "", "rendered": "now",
             "timezone": "UTC", "sources": ["mydata~1.zip"]}
    return _render_media(MEDIA_PLAIN, "Memories", "sub", tmp_path, tmp_path / "pdf", file_index, {},
                         2048, lambda picked, cover: cover, facts, _FakeRenderer(works))


def test_the_single_pdf_of_the_old_layout_goes_only_after_a_full_success(tmp_path):
    legacy = tmp_path / "pdf" / "media-plain.pdf"
    legacy.parent.mkdir()
    legacy.write_bytes(b"2.0.0")

    assert not _media(tmp_path, works=False)
    assert legacy.exists()
    assert list(tmp_path.glob("*_print.tmp.html"))

    assert _media(tmp_path, works=True)
    assert not legacy.exists()
    assert (tmp_path / "pdf" / "media-plain" / "2024" / "media-plain-2024-part-1-of-1.pdf").is_file()
