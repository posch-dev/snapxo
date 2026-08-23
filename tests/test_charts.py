# SVG chart rendering. No data knowledge here, only shapes and edge cases.

from snapxo.parts.charts import bar_chart, donut_chart, line_chart, nice_ceiling


def test_axis_maximum_rounds_to_a_readable_number():
    assert nice_ceiling(87) == 100
    assert nice_ceiling(1200) == 2000
    assert nice_ceiling(3) == 3
    assert nice_ceiling(0) == 1


def test_a_line_chart_draws_one_polyline_per_series():
    svg = line_chart([("sent", [1, 5, 3]), ("received", [2, 2, 8])], [(0, "2026")])

    assert svg.count("<polyline") == 2
    assert "2026" in svg


def test_a_single_series_gets_a_filled_area():
    assert "chart-area" in line_chart([("messages", [1, 2, 3])], [])


def test_several_series_get_a_legend_instead_of_fills():
    svg = line_chart([("sent", [1, 2]), ("received", [2, 1])], [])

    assert "chart-legend" in svg
    assert "chart-area" not in svg


def test_a_line_chart_with_one_point_says_so_instead_of_dividing_by_zero():
    assert "Not enough data" in line_chart([("messages", [5])], [])


def test_an_empty_line_chart_says_so():
    assert "Not enough data" in line_chart([], [])
    assert "Not enough data" in line_chart([("messages", [])], [])


def test_tick_marks_outside_the_range_are_ignored():
    svg = line_chart([("messages", [1, 2, 3])], [(99, "2099")])

    assert "2099" not in svg


def test_a_bar_chart_draws_one_bar_per_value_and_highlights_the_peak():
    svg = bar_chart(["Mon", "Tue", "Wed"], [3, 9, 4])

    assert svg.count("<rect") == 3
    assert svg.count('class="chart-bar"') == 1
    assert svg.count('class="chart-bar-muted"') == 2


def test_a_bar_chart_of_only_zeroes_says_so():
    assert "Not enough data" in bar_chart(["Mon", "Tue"], [0, 0])


def test_a_donut_draws_one_path_per_non_empty_slice():
    svg = donut_chart([("Text", 10), ("Snaps", 5), ("Voice notes", 0)])

    assert svg.count("<path") == 2
    assert ">15<" in svg


def test_a_single_slice_donut_still_closes_its_ring():
    svg = donut_chart([("Text", 10)])

    assert svg.count("<path") == 1
    assert "Not enough data" not in svg


def test_an_empty_donut_says_so():
    assert "Not enough data" in donut_chart([("Text", 0)])


def test_labels_are_escaped():
    assert "<script>" not in bar_chart(["<script>"], [1])
    assert "<script>" not in donut_chart([("<script>", 1)])
