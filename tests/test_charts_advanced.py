import pytest
import math
from tesserax import Chart, Point, Colors, Group
from tesserax.chart import LinearScale, BandScale, X, Y, Axis, BarMark, PointMark


def test_linear_scale_ticks():
    scale = LinearScale((0, 100), (0, 400))
    ticks = scale.ticks(count=5)
    # [(0, '0'), (25, '25'), (50, '50'), (75, '75'), (100, '100')]
    assert len(ticks) == 5
    assert ticks[0][0] == 0
    assert ticks[4][0] == 100


def test_chart_point_mark():
    data = [{"val": 10, "cat": "A"}]
    chart = Chart(data, width=200, height=100).point(size=10).encode(x="cat", y="val")
    main_group = chart._shape
    plot_group = main_group.shapes[0]

    # Check that a Circle is created
    from tesserax.base import Circle

    assert isinstance(plot_group.shapes[0], Circle)
    assert plot_group.shapes[0].r == 10


def test_chart_axis_config():
    data = [{"x": 1, "y": 2}]
    chart = Chart(data)
    chart.axis("x", title="X Title", grid=True)
    assert "x" in chart._axes
    assert chart._axes["x"].title == "X Title"
    assert chart._axes["x"].grid == True


def test_chart_structured_encoding():
    data = [{"x": 1, "y": 2}]
    chart = Chart(data)
    chart.encode(x=X("field_x", axis=Axis(title="Custom X")))
    assert chart._get_field("x") == "field_x"
    assert chart._axes["x"].title == "Custom X"


def test_chart_margins():
    data = [{"x": "A", "y": 10}]
    # No axes
    c1 = Chart(data, width=200, height=100).bar().encode(x="x", y="y")
    g1 = c1._shape
    # margin_left=10, margin_top=10
    assert g1.shapes[0].transform.tx == 10

    # With axes
    c2 = (
        Chart(data, width=200, height=100)
        .bar()
        .encode(x="x", y="y")
        .axis("x")
        .axis("y")
    )
    g2 = c2._shape
    # margin_left=60, margin_top=20
    assert g2.shapes[0].transform.tx == 60


def test_chart_axis_rendering():
    data = [{"x": "A", "y": 10}]
    chart = Chart(data, width=200, height=100).bar().encode(x="x", y="y")
    chart.axis("x", title="X Axis")
    chart.axis("y", title="Y Axis")

    main_group = chart._shape
    # main_group should have: plot_group, x_axis, y_axis
    assert len(main_group.shapes) == 3

    # Check for text in axes
    svg = main_group.render()
    assert "X Axis" in svg
    assert "Y Axis" in svg
    assert "A" in svg  # Label for X
    assert "10" in svg  # Label for Y


def test_chart_animate_data_diff():
    data1 = [{"id": 1, "v": 10}]
    data2 = [{"id": 2, "v": 20}]  # 1 exits, 2 enters

    chart = Chart(data1, width=100, height=100).bar().encode(x="id", y="v")
    chart._shape  # initial

    anim = chart.animate.data(data2)
    from tesserax.animation import Sequence

    assert isinstance(anim, Sequence)
    # Stage 1: Exit, Stage 2: Enter
    assert len(anim.children) == 2


def test_chart_point_mark_animations():
    data1 = [{"id": 1, "v": 10}]
    data2 = [{"id": 1, "v": 20}]  # 1 updates

    chart = Chart(data1, width=100, height=100).point().encode(x="id", y="v")
    chart._shape

    anim = chart.animate.data(data2)
    # Update stage
    assert len(anim.children) == 1


def test_chart_animate_enter_logic():
    data1 = []
    data2 = [{"id": "A", "v": 10}]

    chart = Chart(data1, width=100, height=100).bar().encode(x="id", y="v")
    chart._shape

    # This should not crash and should add shape to plot_group
    anim = chart.animate.data(data2)
    assert "A" in chart._marks
    assert chart._marks["A"] in chart._plot_group.shapes


def test_animation_then_callback():
    from tesserax import Rect

    r = Rect(10, 10)
    anim = r.animate.translate(10, 10)

    finished = False

    def callback(a):
        nonlocal finished
        finished = True

    anim.then(callback)
    anim.finish()
    assert finished == True


def test_chart_axis_transitions():
    data1 = [{"id": 1, "v": 10}]
    data2 = [{"id": 2, "v": 20}]  # 1 exits, 2 enters

    chart = Chart(data1).bar().encode(x="id", y="v").axis("x").axis("y")
    chart._shape  # force build

    anim = chart.animate.data(data2)
    from tesserax.animation import Sequence

    assert isinstance(anim, Sequence)
    # Stage 1: Exit, Stage 2: Enter
    assert len(anim.children) == 2

    exit_stage = anim.children[0]
    from tesserax.animation import Parallel

    assert isinstance(exit_stage, Parallel)
    assert len(exit_stage.children) >= 1


def test_chart_color_encoding():
    data = [{"cat": "A", "v": 10}, {"cat": "B", "v": 20}]
    chart = Chart(data).bar().encode(x="cat", y="v", color="cat")
    main_group = chart._shape
    plot_group = main_group.shapes[0]

    # Check that bars have different colors
    bar1 = plot_group.shapes[0]
    bar2 = plot_group.shapes[1]
    assert bar1.fill != bar2.fill


def test_chart_quantitative_detection():
    data = [{"v": 10}, {"v": "A"}]
    chart = Chart(data)
    chart.encode(x="v")
    assert chart._is_quantitative(chart.data, "x") == True

    data2 = [{"v": "A"}]
    chart2 = Chart(data2)
    chart2.encode(x="v")
    assert chart2._is_quantitative(chart2.data, "x") == False


def test_chart_axis_options():
    data = [{"x": "A", "y": 10}]
    chart = Chart(data).bar().encode(x="x", y="y")
    # Disable labels, add specific tick count
    chart.axis("x", labels=False, ticks=3)
    chart._shape
    svg = chart.render()
    assert "A" not in svg  # Labels disabled


def test_scale_linear_ticks_edge():
    s = LinearScale((0, 0), (0, 100))
    assert len(s.ticks(count=1)) == 1
    assert s.ticks(count=5)[0][0] == 0


def test_scale_edge_cases():
    # Linear scale with same min/max
    s = LinearScale((10, 10), (0, 100))
    assert s.map(10) == 0

    # Band scale with missing value
    bs = BandScale(["A", "B"], (0, 100))
    assert bs.map("C") == 0

    # Color scale fallback
    from tesserax.chart import ColorScale

    cs = ColorScale(["A", "B"])
    assert cs.map("C") == Colors.Gray


def test_linear_scale_zero_division():
    s = LinearScale((10, 10), (0, 100))
    assert s.map(10) == 0
    assert s.map(20) == 0


def test_chart_numerical_x_axis():
    # Test scatter plot with numerical X
    data = [{"x": 10, "y": 100}, {"x": 20, "y": 200}]
    chart = Chart(data).point().encode(x="x", y="y").axis("x")
    main_group = chart._shape
    svg = main_group.render()
    assert "10" in svg
    assert "20" in svg


def test_chart_y_axis_transitions():
    data1 = [{"id": 1, "v": 10}]
    data2 = [{"id": 1, "v": 100}]  # Scale changes significantly

    chart = Chart(data1).bar().encode(x="id", y="v").axis("y")
    chart._shape

    anim = chart.animate.data(data2)
    # y-axis transition should be present in the Sequence
    from tesserax.animation import Sequence

    assert isinstance(anim, Sequence)
    assert len(anim.children) > 0


def test_chart_animate_no_changes():
    data = [{"id": 1, "v": 10}]
    chart = Chart(data).bar().encode(x="id", y="v")
    chart._shape

    anim = chart.animate.data(data)
    from tesserax.animation import Wait, Sequence, Parallel

    assert isinstance(anim, Sequence)
    # It returns Sequence(*stages).then(finalize), so it's a Sequence.
    # Actually, it returns Sequence(*stages).then(finalize), and Sequence.then returns self.
    # If no stages, it returns Wait(0).then(finalize) which is a Wrapped.
    # Let's check.
    from tesserax.animation import Wrapped

    assert isinstance(anim, Wrapped) or isinstance(anim, Sequence)


def test_chart_empty_encoding():
    chart = Chart([{"x": 1}])
    # No encode() called
    g = chart._shape
    assert isinstance(g, Group)
    assert len(g.shapes) == 0  # Empty data/encoding returns empty group


def test_chart_methods_coverage():
    data = [{"x": 1, "y": 2}]
    chart = Chart(data)
    chart.mark_bar(padding=0.2)
    chart.mark_point(size=10)
    # Just ensure these aliases and methods work
    assert chart._mark is not None

    from tesserax.chart import BarMark

    chart.mark(BarMark())
    assert isinstance(chart._mark, BarMark)


def test_chart_bar_point_aliases():
    data = [{"x": 1, "y": 2}]
    chart = Chart(data).bar()
    assert isinstance(chart._mark, BarMark)
    chart.point()
    from tesserax.chart import PointMark

    assert isinstance(chart._mark, PointMark)
    chart.mark_bar()
    assert isinstance(chart._mark, BarMark)
    chart.mark_point()
    assert isinstance(chart._mark, PointMark)


def test_chart_mark_setter():
    data = [{"x": 1, "y": 2}]
    chart = Chart(data)
    from tesserax.chart import PointMark

    m = PointMark(size=20)
    chart.mark(m)
    assert chart._mark == m


def test_chart_y_axis_categorical():
    data = [{"x": "A", "y": "Low"}, {"x": "B", "y": "High"}]
    # Y is categorical
    chart = Chart(data).bar().encode(x="x", y="y").axis("y")
    chart._shape
    svg = chart.render()
    assert "Low" in svg
    assert "High" in svg


def test_mark_missing_fields():
    data = [{"x": 1, "y": 2}]
    # PointMark with missing Y
    chart = Chart(data).point().encode(x="x")
    chart._shape

    # BarMark with missing X
    chart2 = Chart(data).bar().encode(y="y")
    chart2._shape
