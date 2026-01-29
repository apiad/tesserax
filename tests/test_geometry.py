import pytest
from tesserax.core import Point, Bounds


def test_point_arithmetic() -> None:
    """Tests basic point addition and subtraction."""
    p1 = Point(10, 20)
    p2 = Point(5, 5)

    assert p1 + p2 == Point(15, 25)
    assert p1 - p2 == Point(5, 15)


def test_point_transform_apply() -> None:
    """Tests applying transforms to points, including scaling and rotation."""
    p = Point(10, 0)
    # Rotate 90 degrees and scale by 2
    transformed = p.apply(tx=5, ty=5, r=90, s=2)

    # After scale: (20, 0)
    # After 90 deg rotation: (0, 20)
    # After translation: (5, 25)
    assert transformed.x == pytest.approx(5)
    assert transformed.y == pytest.approx(25)


def test_bounds_properties() -> None:
    """Verifies anchor point calculations on a bounding box."""
    b = Bounds(0, 0, 100, 50)
    assert b.center == Point(50, 25)
    assert b.top == Point(50, 0)
    assert b.bottom == Point(50, 50)
    assert b.left == Point(0, 25)
    assert b.right == Point(100, 25)


def test_bounds_union() -> None:
    """Ensures multiple bounds are correctly unified."""
    b1 = Bounds(0, 0, 10, 10)
    b2 = Bounds(20, 20, 10, 10)
    union = Bounds.union(b1, b2)

    assert union == Bounds(0, 0, 30, 30)
