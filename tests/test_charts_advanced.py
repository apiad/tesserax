import pytest
import math
from tesserax import Chart, Point, Colors
from tesserax.chart import LinearScale, BandScale, X, Y, Axis

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
    main_group = chart._build()
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
    g1 = c1._build()
    # margin_left=10, margin_top=10
    assert g1.shapes[0].transform.tx == 10
    
    # With axes
    c2 = Chart(data, width=200, height=100).bar().encode(x="x", y="y").axis("x").axis("y")
    g2 = c2._build()
    # margin_left=60, margin_top=20
    assert g2.shapes[0].transform.tx == 60

def test_chart_axis_rendering():
    data = [{"x": "A", "y": 10}]
    chart = Chart(data, width=200, height=100).bar().encode(x="x", y="y")
    chart.axis("x", title="X Axis")
    chart.axis("y", title="Y Axis")
    
    main_group = chart._build()
    # main_group should have: plot_group, x_axis, y_axis
    assert len(main_group.shapes) == 3
    
    # Check for text in axes
    svg = main_group.render()
    assert "X Axis" in svg
    assert "Y Axis" in svg
    assert "A" in svg # Label for X
    assert "10" in svg # Label for Y

def test_chart_quantitative_detection():
    data = [{"v": 10}, {"v": "A"}]
    chart = Chart(data)
    chart.encode(x="v")
    assert chart._is_quantitative("x") == True
    
    data2 = [{"v": "A"}]
    chart2 = Chart(data2)
    chart2.encode(x="v")
    assert chart2._is_quantitative("x") == False

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
