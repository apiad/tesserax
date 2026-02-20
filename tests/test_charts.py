from tesserax.chart import LinearScale, BandScale, Chart
from tesserax import Point


def test_linear_scale():
    scale = LinearScale((0, 100), (0, 10))
    assert scale.map(0) == 0
    assert scale.map(50) == 5
    assert scale.map(100) == 10


def test_band_scale():
    # 3 bands in 300 units. Step = 300 / (3 - 0.1) = 300 / 2.9 approx 103.4
    # bandwidth = 103.4 * 0.9 approx 93.1
    scale = BandScale(["A", "B", "C"], (0, 290), padding=0.1)
    assert scale.bandwidth == 90.0
    assert scale.map("A") == 0
    assert scale.map("B") == 100
    assert scale.map("C") == 200


def test_chart_bar_logic():
    data = [{"x": "A", "y": 10}, {"x": "B", "y": 20}]
    chart = Chart(data, width=200, height=100).mark_bar().encode(x="x", y="y")
    shape = chart._build()

    assert len(shape.shapes) == 2
    # First bar: y=10 maps to bh=50 (since max_y=20, height=100)
    # Center y in chart space is 25.
    # Center y in SVG space is 100 - 25 = 75.
    bar1 = shape.shapes[0]
    assert bar1.transform.ty == 75.0

    # Second bar: y=20 maps to bh=100
    # Center y in chart space is 50.
    # Center y in SVG space is 100 - 50 = 50.
    bar2 = shape.shapes[1]
    assert bar2.transform.ty == 50.0
