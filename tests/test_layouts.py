import math
import pytest
from tesserax.core import Point, Bounds
from tesserax.base import Rect, Circle, Group

# --- Fixtures ---


@pytest.fixture
def messy_group():
    """Returns a group of shapes scattered randomly."""
    g = Group()
    g.add(Rect(10, 10).translated(0, 0))
    g.add(Rect(20, 20).translated(50, 50))  # Far away
    g.add(Rect(15, 15).translated(-20, 10))  # Overlapping
    return g


@pytest.fixture
def sizes_group():
    """Group with varied sizes to test alignment robustness."""
    g = Group()
    g.add(Rect(10, 50))  # Tall
    g.add(Rect(10, 10))  # Small
    g.add(Rect(10, 30))  # Medium
    return g


# --- Alignment Invariants ---


def test_top_alignment_invariant(sizes_group: Group):
    """Invariant: After aligning top, all min_y values must be equal."""
    # Pre-condition: y values are different (implied by centered construction with different heights)

    sizes_group.align(axis="vertical", anchor="top")

    # Capture the "y" of the first element
    expected_y = sizes_group.shapes[0].bounds().y

    for s in sizes_group.shapes:
        # All shapes must match this Y
        assert math.isclose(s.bounds().y, expected_y, abs_tol=1e-9)


def test_center_alignment_invariant(sizes_group: Group):
    """Invariant: After aligning centers, midpoints must match."""
    sizes_group.align(axis="both", anchor="center")

    first_center = sizes_group.shapes[0].bounds().center

    for s in sizes_group.shapes:
        c = s.bounds().center
        assert math.isclose(c.x, first_center.x, abs_tol=1e-9)
        assert math.isclose(c.y, first_center.y, abs_tol=1e-9)


# --- Distribution Invariants ---


def test_horizontal_monotonicity(messy_group: Group):
    """Invariant: In a distributed row, Right(i) <= Left(i+1)."""
    gap = 5.0
    messy_group.distribute(axis="horizontal", gap=gap)

    shapes = messy_group.shapes
    for i in range(len(shapes) - 1):
        current = shapes[i].bounds()
        next_shape = shapes[i + 1].bounds()

        # The right edge of current + gap must equal left edge of next
        # (Use isclose because floating point math)
        assert math.isclose(current.right.x + gap, next_shape.x, abs_tol=1e-5)


def test_vertical_monotonicity(messy_group: Group):
    """Invariant: In a distributed col, Bottom(i) <= Top(i+1)."""
    gap = 10.0
    messy_group.distribute(axis="vertical", gap=gap)

    shapes = messy_group.shapes
    for i in range(len(shapes) - 1):
        current = shapes[i].bounds()
        next_shape = shapes[i + 1].bounds()

        assert math.isclose(current.bottom.y + gap, next_shape.y, abs_tol=1e-5)


def test_gap_integrity():
    """Invariant: Space between items exactly matches requested gap."""
    g = Group()
    r1 = Rect(10, 10)
    r2 = Rect(10, 10)
    g.add(r1, r2)

    target_gap = 12.345
    g.distribute(axis="horizontal", gap=target_gap)

    distance = r2.bounds().x - r1.bounds().right.x
    assert math.isclose(distance, target_gap, abs_tol=1e-9)


# --- Nesting Invariants ---


def test_group_translation_preserves_relative_layout(sizes_group: Group):
    """Invariant: Moving a Group moves its children but maintains their relative positions."""
    sizes_group.distribute(axis="horizontal", gap=5)

    # Snapshot relative distance between 0 and 1
    dist_before = sizes_group.shapes[1].bounds().x - sizes_group.shapes[0].bounds().x

    # Move the entire group massively
    sizes_group.translated(1000, 500)

    # Relative distance must be identical
    dist_after = sizes_group.shapes[1].bounds().x - sizes_group.shapes[0].bounds().x
    assert math.isclose(dist_before, dist_after, abs_tol=1e-9)
