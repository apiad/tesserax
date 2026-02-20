import pytest
from tesserax import Canvas, Rect, Camera, Point, Bounds, Colors
import os


def test_canvas_init():
    c = Canvas(width=500, height=400)
    assert c.width == 500
    assert c.height == 400
    assert "arrow" in c._defs


def test_canvas_fit_basic():
    c = Canvas()
    r = Rect(100, 100).translated(50, 50)
    c.add(r)

    # Rect(100,100) centered at (50,50) means bounds are (0, 0, 100, 100)
    c.fit(padding=0)
    assert c._viewbox == (0.0, 0.0, 100.0, 100.0)
    assert c.width == 100.0
    assert c.height == 100.0


def test_canvas_fit_with_padding():
    c = Canvas()
    r = Rect(10, 10).translated(5, 5)  # Bounds (0,0,10,10)
    c.add(r)
    c.fit(padding=5)
    # Padded bounds: (-5, -5, 20, 20)
    assert c._viewbox == (-5.0, -5.0, 20.0, 20.0)


def test_canvas_fit_no_crop():
    c = Canvas(width=1000, height=1000)
    r = Rect(100, 100).translated(50, 50)
    c.add(r)
    c.fit(crop=False)
    assert c._viewbox == (0.0, 0.0, 100.0, 100.0)
    assert c.width == 1000
    assert c.height == 1000


def test_canvas_fit_to_bounds():
    c = Canvas()
    b = Bounds(10, 10, 50, 50)
    c.fit(bounds=b)
    assert c._viewbox == (10.0, 10.0, 50.0, 50.0)


def test_canvas_svg_output():
    c = Canvas(width=100, height=100)
    with c:
        Rect(50, 50, fill=Colors.Red).translated(50, 50)
    svg = str(c)
    assert '<svg width="100" height="100"' in svg
    assert 'viewBox="0 0 100 100"' in svg
    assert "<rect" in svg
    assert 'fill="rgba(255,0,0,1.0)"' in svg


def test_canvas_save_svg(tmp_path):
    c = Canvas()
    with c:
        Rect(10, 10)
    path = tmp_path / "test.svg"
    c.save(path)
    assert path.exists()
    with open(path, "r") as f:
        assert "<svg" in f.read()


def test_canvas_save_png(tmp_path):
    c = Canvas()
    with c:
        Rect(10, 10)
    path = tmp_path / "test.png"
    try:
        c.save(path)
        assert path.exists()
    except ImportError:
        pytest.skip("cairosvg not installed")


def test_canvas_save_unsupported(tmp_path):
    c = Canvas()
    path = tmp_path / "test.txt"
    with pytest.raises(ValueError, match="Unsupported"):
        c.save(path)


def test_camera_active_fit():
    c = Canvas(width=1000, height=1000)
    cam = Camera(width=200, height=200, active=True).translated(500, 500)
    c.add(cam)

    # Trigger render which should trigger canvas.fit
    c._build_svg()

    # cam centered at 500,500 with size 200,200 -> bounds (400, 400, 200, 200)
    assert c._viewbox == (400.0, 400.0, 200.0, 200.0)
    assert c.width == 200.0
    assert c.height == 200.0


def test_canvas_display_no_ipython(monkeypatch):
    # Mock sys.modules to simulate IPython not being installed
    import sys

    monkeypatch.setitem(sys.modules, "IPython.display", None)
    c = Canvas()
    with pytest.raises(ImportError, match="IPython is required"):
        c.display()


def test_canvas_display_success(monkeypatch):
    from unittest.mock import MagicMock

    mock_display = MagicMock()
    mock_svg = MagicMock()

    # Create a mock module structure
    class MockIPython:
        SVG = mock_svg
        display = mock_display

    import sys

    monkeypatch.setitem(sys.modules, "IPython.display", MockIPython)

    c = Canvas()
    c.display()
    assert mock_display.called


def test_canvas_fit_empty():
    c = Canvas()
    # Should not crash and return self
    assert c.fit() == c


def test_canvas_markers():
    c = Canvas()
    r = Rect(10, 10)
    c.define("my_marker", r)
    svg = c._build_svg()
    assert '<marker id="my_marker"' in svg
    assert 'id="arrow"' in svg  # Default arrow
