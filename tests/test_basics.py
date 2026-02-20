import math
import pytest
from tesserax.core import Point, Bounds
from tesserax.base import (
    Rect,
    Square,
    Circle,
    Ellipse,
    Group,
    Polyline,
    Text,
    Path,
    Line,
    Arrow,
    Container,
    Spacer,
    Ghost,
    Spring,
)
from tesserax.color import Colors

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

    def test_square(self):
        s = Square(50)
        assert s.size == 50
        assert s.local().width == 50
        assert s.local().height == 50
        assert "<rect" in s._render()

    def test_ellipse(self):
        e = Ellipse(40, 20)
        assert e.rx == 40
        assert e.ry == 20
        assert e.local().width == 80
        assert e.local().height == 40
        assert "<ellipse" in e._render()

        def test_text(self):
            t = Text("Hello World", size=20, font="Arial")
            assert t.content == "Hello World"
            assert t.size == 20
            assert t.font == "Arial"
            assert "<text" in t._render()
            assert "Hello World" in t._render()

            # Default middle/middle
            b = t.local()
            assert b.x < 0
            assert b.width > 0

            # start anchor
            t2 = Text("Start", anchor="start")
            assert t2.local().x == 0

        # end anchor
        t3 = Text("End", anchor="end")
        assert math.isclose(t3.local().x + t3.local().width, 0, abs_tol=1e-5)

    def test_path_manual(self):
        p = Path()
        p.jump_to(0, 0).line_to(10, 10).cubic_to(20, 10, 20, 20, 30, 20).close()
        svg = p._render()
        assert 'd="M 0 0 L 10 10 C 20 10, 20 20, 30 20 Z"' in svg
        assert p.local().width == 30.0

    def test_polyline_simplify(self):
        # Line with collinear point
        p = Polyline([Point(0, 0), Point(5, 0), Point(10, 0)])
        assert len(p.points) == 3
        p.simplify(tolerance=0.1)
        assert len(p.points) == 2
        assert p.points[0] == Point(0, 0)
        assert p.points[1] == Point(10, 0)

    def test_polyline_manipulation(self):
        p = Polyline([Point(0, 0)])
        p.append(Point(10, 10))
        p.prepend(Point(-10, -10))
        p.extend([Point(20, 20), Point(30, 30)])
        assert len(p.points) == 5
        assert p.points[0] == Point(-10, -10)

        p.apply(lambda pt: pt.d(1, 1))
        assert p.points[0] == Point(-9, -9)

    def test_polyline_subdivide_multi(self):
        p = Polyline([Point(0, 0), Point(10, 0)])
        p.subdivide(2)
        # 1st: (0,0), (5,0), (10,0) -> 3 pts
        # 2nd: (0,0), (2.5,0), (5,0), (7.5,0), (10,0) -> 5 pts
        assert len(p.points) == 5

    def test_path_arc_quad(self):
        p = Path()
        p.jump_to(0, 0).arc(10, 10, 0, 0, 1, 10, 10).quadratic_to(20, 0, 30, 0)
        svg = p._render()
        assert "A 10 10 0 0 1 10 10" in svg
        assert "Q 20 0, 30 0" in svg

    def test_polyline_expand_contract(self):
        p = Polyline.poly(n=4, radius=10)  # Square
        p.center()
        initial_mag = p.points[0].magnitude()
        p.expand(5)
        assert math.isclose(p.points[0].magnitude(), initial_mag + 5)
        p.contract(2)
        assert math.isclose(p.points[0].magnitude(), initial_mag + 3)

        # Custom orientation
        p2 = Polyline.poly(n=4, radius=10, orientation=Point(1, 0))
        # Point(1,0) is 0 degrees. Points: (10,0), (0,10), (-10,0), (0,-10)
        assert math.isclose(p2.points[0].x, 10.0)

        # Error case
        with pytest.raises(ValueError):
            Polyline.poly(n=2, radius=10)

    def test_line_and_arrow(self):
        p1, p2 = Point(0, 0), Point(100, 100)
        l = Line(p1, p2)
        assert "<path" in l.render()

        # Curved line
        l2 = Line(p1, p2, curvature=0.5)
        assert "A" in l2.render()

        a = Arrow(p1, p2)
        assert 'marker-end="url(#arrow)"' in a.render()

    def test_group_manipulation(self):
        g = Group()
        r1 = Rect(10, 10)
        g += r1  # __iadd__
        assert r1 in g.shapes

        g.remove(r1)
        assert r1 not in g.shapes
        assert r1.parent is None

    def test_group_distribution_modes(self):
        g = Group()
        r1 = Rect(10, 10)
        r2 = Rect(10, 10)
        g.add(r1, r2)

        # space-between
        # size 100. r1.w=10, r2.w=10. Total rigid=20. Remaining=80. Gap=80.
        g.distribute(axis="horizontal", size=100, mode="space-between")
        assert math.isclose(r2.bounds().x, 90.0)

        # space-around
        # size 100. r1.w=10, r2.w=10. Gap = 80 / 2 = 40. Start offset = 20.
        # r1 at 20. r2 at 20 + 10 + 40 = 70.
        g.distribute(axis="horizontal", size=100, mode="space-around")
        # Center of r1: x=25. (bounds.x = 20)
        assert math.isclose(r1.bounds().x, 20.0)
        assert math.isclose(r2.bounds().x, 70.0)

    def test_container(self):
        r = Rect(50, 50)
        c = Container(shapes=[r], padding=10)

        # Rect bounds (-25, -25, 50, 50)
        # Container bounds should be (-35, -35, 70, 70)
        b = c.local()
        assert b.width == 70
        assert b.height == 70
        assert "<rect" in c._render()  # Background rect

    def test_spacer_ghost_spring(self):
        s = Spacer(10, 20)
        assert s.local().width == 10
        assert s._render() == ""

        r = Rect(100, 100)
        g = Ghost(r)
        assert g.local() == r.local()
        assert g._render() == ""

        sp = Spring(flex=2.0)
        assert sp.flex == 2.0
        assert sp.local().width == 0.0  # Initially 0

    def test_shape_traces(self):
        # Verify trace() returns a Path for each primitive
        shapes = [
            Rect(10, 10),
            Square(10),
            Circle(10),
            Ellipse(10, 5),
            Polyline([Point(0, 0), Point(10, 10)]),
            Container(padding=10),
        ]
        for s in shapes:
            p = s.trace()
            assert isinstance(p, Path)
            assert len(p._commands) > 0

    def test_group_context_manager(self):
        with Group() as g:
            r = Rect(10, 10)
            c = Circle(5)

        assert r.parent == g
        assert c.parent == g
        assert len(g.shapes) == 2

    def test_shape_lifecycle_methods(self):
        g = Group()
        r = Rect(10, 10)
        g.add(r)

        r.detach()
        assert r.parent is None
        assert r not in g.shapes

        with g:
            r.attach()
        assert r.parent == g

        r.hide()
        assert r.hidden == True
        assert r.render() == ""

        r.show()
        assert r.hidden == False
        assert r.render() != ""

    def test_fluent_transform_methods(self):
        r = Rect(10, 10)
        r.translated(10, 20).rotated(1).scaled(2)
        assert r.transform.tx == 10
        assert r.transform.ty == 20
        assert r.transform.rotation == 1
        assert r.transform.sx == 2


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

        # Loose mode should work
        g2.add(r, mode="loose")
        assert r.parent == g2
        assert r not in g1.shapes

    def test_group_with_springs(self):
        g = Group()
        r1 = Rect(10, 10)
        s1 = Spring(flex=1.0)
        r2 = Rect(10, 10)
        g.add(r1, s1, r2)

        # Total size 100. r1.w=10, r2.w=10. Total rigid=20. Remaining=80.
        # Spring should take 80 units.
        g.distribute(axis="horizontal", size=100)
        assert s1._size == 80.0
        assert math.isclose(r2.bounds().x, 90.0)


def test_path_relative_commands():
    p = Path()
    p.jump_to(10, 10).jump_by(10, 10).line_by(10, 10)
    # Should be at (30, 30)
    assert p._cursor == (30.0, 30.0)


def test_polyline_smoothing_branches():
    # Open polyline with smoothness
    p = Polyline([Point(0, 0), Point(10, 10), Point(20, 0)], smoothness=0.5)
    svg = p._render()
    assert "Q" in svg

    # Closed polyline with smoothness
    p2 = Polyline(
        [Point(0, 0), Point(10, 10), Point(20, 0)], smoothness=0.5, closed=True
    )
    svg2 = p2._render()
    assert "Q" in svg2
    assert "Z" in svg2


def test_polyline_empty_center():
    p = Polyline([])
    p.center()
    assert len(p.points) == 0


def test_visual_identity_render():
    # Test render with identity transform and opacity 1.0
    r = Rect(10, 10)
    assert "<rect" in r.render()
    # Identity means no <g> tag usually
    assert "<g" not in r.render()


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
