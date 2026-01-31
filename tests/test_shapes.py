from tesserax.base import Rect, Circle, Group
from tesserax.core import Bounds


def test_rect_rendering() -> None:
    """Verifies Rect local bounds and SVG output."""
    rect = Rect(w=50, h=30, stroke="red")
    assert rect.local() == Bounds(0, 0, 50, 30)
    assert 'width="50"' in rect._render()
    assert 'stroke="red"' in rect._render()


def test_circle_bounds() -> None:
    """Verifies Circle local bounds calculation from radius."""
    circle = Circle(r=10)
    # Circle at (0,0) with radius 10 should span -10 to 10
    assert circle.local() == Bounds(-10, -10, 20, 20)


def test_group_nesting() -> None:
    """Tests that groups correctly aggregate child bounds."""
    r1 = Rect(10, 10).translated(0, 0)
    r2 = Rect(10, 10).translated(20, 20)

    gp = Group([r1, r2])
    # Union of (0,0,10,10) and (20,20,10,10)
    assert gp.local() == Bounds(0, 0, 30, 30)
