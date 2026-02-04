import math
import pytest
from tesserax.core import Point, Bounds
from tesserax.base import Rect, Circle, Group, Polyline, Text

# --- Fixtures ---


@pytest.fixture
def basic_rect():
    return Rect(100, 50)


@pytest.fixture
def basic_group():
    return Group()


@pytest.fixture
def simple_polyline():
    return Polyline([Point(0, 0), Point(10, 10), Point(20, 0)])


# --- Shape Invariants ---


class TestPrimitives:
    def test_render_contract(self, basic_rect):
        """Invariant: Shapes must produce their corresponding SVG tags."""
        svg = basic_rect._render()
        assert "<rect" in svg
        assert 'width="100"' in svg

        c = Circle(10)
        assert "<circle" in c._render()

    def test_local_dimensionality(self):
        """Invariant: Local bounds match constructor params."""
        w, h = 123.4, 56.7
        r = Rect(w, h)
        b = r.local()
        assert math.isclose(b.width, w)
        assert math.isclose(b.height, h)

        radius = 15
        c = Circle(radius)
        assert math.isclose(c.local().width, radius * 2)

    def test_transform_isolation(self, basic_rect):
        """Invariant: Transform affects global bounds, but NEVER local bounds."""
        initial_local = basic_rect.local()

        # Apply heavy transformations
        basic_rect.translated(100, 100).rotated(math.radians(45)).scaled(2.0)

        # Local bounds must remain immutable
        assert basic_rect.local() == initial_local

        # Global bounds should change
        assert basic_rect.bounds() != initial_local


# --- Group Invariants ---


class TestGroups:
    def test_parental_authority(self, basic_group, basic_rect):
        """Invariant: Adding to group sets parent."""
        assert basic_rect.parent is None
        basic_group.add(basic_rect)
        assert basic_rect.parent is basic_group

    def test_bounds_containment(self):
        """Invariant: Group bounds is union of children."""
        g = Group()
        r1 = Rect(10, 10).translated(0, 0)  # Center at 0,0
        r2 = Rect(10, 10).translated(20, 0)  # Center at 20,0
        g.add(r1, r2)

        # r1 bounds: x[-5, 5]
        # r2 bounds: x[15, 25]
        # Union x: [-5, 25], width=30
        gb = g.local()
        assert math.isclose(gb.x, -5)
        assert math.isclose(gb.width, 30)

    def test_strict_mode_reparenting(self):
        """Invariant: Strict mode prevents stealing children."""
        g1 = Group()
        g2 = Group()
        r = Rect(10, 10)

        g1.add(r)

        with pytest.raises(RuntimeError):
            g2.add(r, mode="strict")


# --- Polyline Invariants ---


class TestPolyline:
    def test_subdivide_monotonicity(self, simple_polyline):
        """Invariant: Subdivision increases resolution."""
        initial_count = len(simple_polyline.points)
        simple_polyline.subdivide(1)
        assert len(simple_polyline.points) > initial_count

    def test_centering_zerosum(self):
        """Invariant: center() moves geometric center to (0,0)."""
        # Create a line far away from origin
        p = Polyline([Point(100, 100), Point(110, 110)])

        p.center()

        # Calculate new centroid
        xs = [pt.x for pt in p.points]
        ys = [pt.y for pt in p.points]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        assert math.isclose(cx, 0, abs_tol=1e-9)
        assert math.isclose(cy, 0, abs_tol=1e-9)

    def test_topological_closure(self):
        """Invariant: Closed polyline has 'Z' command."""
        p = Polyline([Point(0, 0), Point(1, 1)], closed=True)
        assert "Z" in p._render()
