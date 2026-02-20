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
    chart = Chart(data, width=200, height=100).bar().encode(x="x", y="y")
    main_group = chart._build()

    # main_group contains the plot_group (and potentially axes)
    # Since no axes are defined, plot_group is the only child.
    plot_group = main_group.shapes[0]
    assert len(plot_group.shapes) == 2

    # plot_h = 100 - 10 (bottom) - 20 (top) = 70
    # y=10 maps to bh=35 (since max_y=20, plot_h=70)
    # Center y in chart space is 17.5.
    # Center y in plot space (SVG) is 70 - 17.5 = 52.5.
    bar1 = plot_group.shapes[0]
    assert bar1.transform.ty == 52.5

    # Second bar: y=20 maps to bh=70
    # Center y in chart space is 35.
    # Center y in plot space (SVG) is 70 - 35 = 35.
    bar2 = plot_group.shapes[1]
    assert bar2.transform.ty == 35.0
