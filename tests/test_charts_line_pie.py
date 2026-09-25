from tesserax.chart import Chart, Pie
from tesserax import Polyline, Path, Rect
from tesserax.color import hex as hexcolor


# ---- LineMark ---------------------------------------------------------------


def test_line_single_series_one_polyline():
    data = [{"x": "A", "y": 10}, {"x": "B", "y": 20}, {"x": "C", "y": 15}]
    chart = Chart(data, width=200, height=100).line().encode(x="x", y="y")
    main = chart._build()
    plot = main.shapes[0]
    polylines = [s for s in plot.shapes if isinstance(s, Polyline)]
    assert len(polylines) == 1
    assert len(polylines[0].points) == 3


def test_line_color_groups_one_polyline_each():
    data = [
        {"x": "A", "y": 1, "g": "u"},
        {"x": "B", "y": 2, "g": "u"},
        {"x": "A", "y": 3, "g": "v"},
        {"x": "B", "y": 4, "g": "v"},
    ]
    chart = Chart(data, width=200, height=100).line().encode(x="x", y="y", color="g")
    plot = chart._build().shapes[0]
    polylines = [s for s in plot.shapes if isinstance(s, Polyline)]
    assert len(polylines) == 2


# ---- Pie --------------------------------------------------------------------


def test_pie_slice_count():
    data = [
        {"label": "A", "value": 30},
        {"label": "B", "value": 50},
        {"label": "C", "value": 20},
    ]
    pie = Pie(data, radius=100).encode(value="value", label="label")
    group = pie._build()
    slices = [s for s in group.shapes if isinstance(s, Path)]
    assert len(slices) == 3


def test_pie_donut_has_inner_radius():
    data = [{"label": "A", "value": 1}, {"label": "B", "value": 1}]
    pie = Pie(data, radius=100, donut=0.5).encode(value="value", label="label")
    group = pie._build()
    assert len([s for s in group.shapes if isinstance(s, Path)]) == 2


# ---- explicit color ---------------------------------------------------------


def test_bar_explicit_color_overrides_default():
    c = hexcolor("#123456")
    data = [{"x": "A", "y": 5}]
    chart = Chart(data, 100, 50).bar(color=c).encode(x="x", y="y")
    rect = [s for s in chart._build().shapes[0].shapes if isinstance(s, Rect)][0]
    assert rect.fill == c
