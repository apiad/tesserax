import pytest
from tesserax import Rect, Circle, Group, Canvas, Point
from tesserax.sketch import Sketch


def test_sketch_renders_wobbly_paths():
    s = Sketch()
    with s:
        Rect(10, 10)

    # Trace of Rect(10,10) is M, L, L, L, L, Z (or similar)
    # Sketch should replace these with cubic bezier passes (C commands)
    svg = s._render()
    assert "C" in svg  # Wobbly lines are drawn as cubics
    assert "M" in svg
    # The original <rect> should NOT be here if it's traced
    assert "<rect" not in svg


def test_sketch_unwraps_groups():
    s = Sketch()
    with s:
        g = Group()
        with g:
            Rect(10, 10)

    svg = s._render()
    assert "C" in svg
    assert "<rect" not in svg


def test_sketch_handles_not_implemented_trace():
    # Spacer is invisible and trace() will raise NotImplementedError because it's not defined
    from tesserax.base import Spacer

    s = Sketch()
    with s:
        Spacer(10, 10)

    # Should not crash and should render normally (which is empty for Spacer)
    svg = s._render()
    assert svg == ""


def test_sketch_parameters():
    s = Sketch(roughness=2.0, seed=123)
    assert s.roughness == 2.0
    with s:
        Rect(10, 10)
    svg1 = s._render()

    s2 = Sketch(roughness=2.0, seed=123)
    with s2:
        Rect(10, 10)
    svg2 = s2._render()

    # With same seed, should be identical
    assert svg1 == svg2


def test_sketch_bezier():
    # Circle.trace() uses Cubic Beziers (C commands)
    s = Sketch()
    with s:
        Circle(10)

    svg = s._render()
    assert "C" in svg
    assert "<circle" not in svg


def test_sketch_very_short_line():
    # Force a very short line to trigger early return in _draw_curve_pass
    from tesserax.base import Polyline

    p = Polyline([Point(0, 0), Point(0.01, 0.01)])
    s = Sketch()
    with s:
        p

    svg = s._render()
    # Should not crash, and might be empty if all passes are too short
    assert isinstance(svg, str)
