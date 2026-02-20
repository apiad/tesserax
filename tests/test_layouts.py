import math
import pytest
from tesserax.core import Point, Bounds
from tesserax.base import Rect, Circle, Group
from tesserax.layout import RowLayout, ColumnLayout, GridLayout, ForceLayout, HierarchicalLayout

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


# --- Layout Subclasses ---


def test_row_layout():
    r1 = Rect(10, 10)
    r2 = Rect(20, 20)
    rl = RowLayout(shapes=[r1, r2], gap=10, align="start")

    # r1 at 0,0 (local centered means bounds.x = -5, bounds.y = -5)
    # distribute horizontal: r1.x = 0 - (-5) = 5. ty = 0 (reset).
    # r1.bounds() at (0, -5, 10, 10)
    # r2.x = 0 + 10 (r1.w) + 10 (gap) - (-10) = 30.
    assert math.isclose(r2.bounds().x, 20.0, abs_tol=1e-5)
    assert math.isclose(r1.bounds().y, r2.bounds().y, abs_tol=1e-5)


def test_column_layout():
    r1 = Rect(10, 10)
    r2 = Rect(20, 20)
    cl = ColumnLayout(shapes=[r1, r2], gap=10, align="start")

    # r1 at 0,0. r2 starts at r1.bottom + gap
    assert math.isclose(r2.bounds().y, 20.0, abs_tol=1e-5)
    assert math.isclose(r1.bounds().x, r2.bounds().x, abs_tol=1e-5)


def test_grid_layout():
    shapes = [Rect(10, 10) for _ in range(4)]
    gl = GridLayout(shapes=shapes, cols=2, gap=10)

    # Row 0: S0, S1. Row 1: S2, S3
    assert math.isclose(shapes[1].bounds().x, 20.0, abs_tol=1e-5)
    assert math.isclose(shapes[2].bounds().y, 20.0, abs_tol=1e-5)
    assert math.isclose(shapes[3].bounds().x, 20.0, abs_tol=1e-5)
    assert math.isclose(shapes[3].bounds().y, 20.0, abs_tol=1e-5)


def test_force_layout_smoke():
    shapes = [Circle(5) for _ in range(5)]
    fl = ForceLayout(shapes=shapes, iterations=10)
    fl.connect(shapes[0], shapes[1])
    fl.do_layout()
    # Check that they moved from origin
    for s in shapes:
        assert s.transform.tx != 0 or s.transform.ty != 0


def test_hierarchical_layout_smoke():
    s1, s2, s3 = Rect(10, 10), Rect(10, 10), Rect(10, 10)
    hl = HierarchicalLayout(shapes=[s1, s2, s3])
    hl.connect(s1, s2)
    hl.connect(s2, s3)
    hl.do_layout()

    # Should be in different layers
    assert s1.transform.ty != s2.transform.ty
    assert s2.transform.ty != s3.transform.ty


def test_layout_add_triggers_do_layout():
    rl = RowLayout(gap=10)
    r1 = Rect(10, 10)
    r2 = Rect(10, 10)
    rl.add(r1)
    rl.add(r2)
    assert math.isclose(r2.bounds().x, 20.0, abs_tol=1e-5)
