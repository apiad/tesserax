import math
import pytest
from tesserax.core import Point, Transform, Bounds, deg

# --- Fixtures for Random Data ---


@pytest.fixture
def random_point():
    return Point(10, 20)  # In real testing, use hypothesis or random values


@pytest.fixture
def identity_transform():
    return Transform.identity()


# --- Point Tests ---


def test_additive_identity():
    p = Point(12.5, -4.0)
    assert p + Point(0, 0) == p
    assert p - Point(0, 0) == p


def test_commutativity():
    p1 = Point(1, 5)
    p2 = Point(-2, 3)
    assert p1 + p2 == p2 + p1


def test_normalization_contract():
    p = Point(3, 4)  # Magnitude 5
    norm = p.normalize()
    assert math.isclose(norm.magnitude(), 1.0)
    assert math.isclose(norm.x, 0.6)
    assert math.isclose(norm.y, 0.8)


def test_zero_vector_safety():
    # Should not raise division by zero
    zero = Point(0, 0)
    assert zero.normalize() == zero
    assert zero.magnitude() == 0.0


def test_lerp_boundaries():
    start = Point(0, 0)
    end = Point(10, 10)
    assert start.lerp(end, 0.0) == start
    assert start.lerp(end, 1.0) == end
    assert start.lerp(end, 0.5) == Point(5, 5)


def test_distance_to_segment():
    p = Point(5, 5)
    s1 = Point(0, 0)
    s2 = Point(10, 0)
    # distance to horizontal segment at y=0 is 5
    assert math.isclose(Point.distance_to_segment(p, s1, s2), 5.0)

    # distance to a point (degenerate segment)
    assert math.isclose(Point.distance_to_segment(p, s1, s1), p.magnitude())


# --- Transform Tests ---


def test_identity_mapping():
    t = Transform.identity()
    p = Point(42, -99)
    assert t.map(p) == p


def test_translation_equivalence():
    t = Transform().translate(5, -5)
    p = Point(10, 10)
    # Translation should be simple addition
    assert t.map(p) == p + Point(5, -5)


def test_rotation_cyclicity():
    p = Point(10, 0)
    # Rotate 360 degrees (2pi radians)
    t = Transform().rotate(2 * math.pi)
    result = t.map(p)

    # Use simple epsilon check
    assert math.isclose(result.x, p.x, abs_tol=1e-9)
    assert math.isclose(result.y, p.y, abs_tol=1e-9)


def test_application_order():
    """Invariant: Scale -> Rotate -> Translate"""
    # Scale x2, Translate +10
    t = Transform(tx=10, sx=2)
    p = Point(1, 0)

    # Expected: (1 * 2) + 10 = 12
    # Incorrect (Translate first): (1 + 10) * 2 = 22
    assert t.map(p).x == 12


def test_immutability_copy():
    t1 = Transform(tx=10)
    t2 = t1.copy()
    t2.translate(5, 0)
    assert t1.tx == 10
    assert t2.tx == 15


# --- Bounds Tests ---


def test_union_containment():
    b1 = Bounds(0, 0, 10, 10)
    b2 = Bounds(20, 20, 10, 10)
    u = Bounds.union(b1, b2)

    # Union must start at min x/y and end at max right/bottom
    assert u.x <= b1.x and u.y <= b1.y
    assert (u.right.x >= b2.right.x) and (u.bottom.y >= b2.bottom.y)


def test_anchor_consistency():
    b = Bounds(0, 0, 100, 100)
    center = b.anchor("center")
    assert center == Point(50, 50)
    assert center == (b.topleft + b.bottomright) / 2


def test_padding_invariant():
    b = Bounds(10, 10, 50, 50)
    padded = b.padded(5)

    # X/Y move out by padding
    assert padded.x == b.x - 5
    assert padded.y == b.y - 5
    # Width/Height grow by 2x padding
    assert padded.width == b.width + 10
    assert padded.height == b.height + 10


def test_transform_reset_and_lerp():
    t = Transform(tx=10, ty=20, rotation=1, sx=2, sy=2)
    t.reset()
    assert t.tx == 0 and t.ty == 0 and t.rotation == 0 and t.sx == 1 and t.sy == 1

    t1 = Transform(tx=0)
    t2 = Transform(tx=100)
    t3 = t1.lerp(t2, 0.5)
    assert t3.tx == 50


def test_transform_fluent_mutators():
    t = Transform()
    t.translate(10, 20).rotate(math.pi).scale(2, 3)
    assert t.tx == 10
    assert t.ty == 20
    assert t.rotation == math.pi
    assert t.sx == 2
    assert t.sy == 3


def test_shape_align_to():
    from tesserax.base import Rect

    r1 = Rect(10, 10).translated(0, 0)
    r2 = Rect(10, 10).translated(100, 100)

    r2.align_to(r1, "left", "right")
    # r1 right is at x=5
    # r2 left is at x=5
    # r2 width is 10, so r2 center tx should be 10
    assert r2.transform.tx == 10


def test_deg_function():
    assert math.isclose(deg(180), math.pi)
    assert math.isclose(deg(90), math.pi / 2)


def test_point_class_methods():
    assert Point.zero() == Point(0, 0)
    assert Point.up() == Point(0, -1)
    assert Point.down() == Point(0, 1)
    assert Point.left() == Point(-1, 0)
    assert Point.right() == Point(1, 0)


def test_point_math_more():
    p = Point(10, 20)
    assert p / 2 == Point(5, 10)
    assert p.dx(5) == Point(15, 20)

    # Point.apply (direct method)
    p2 = Point(1, 0).apply(tx=10, ty=10, r=90, s=2)
    # Scale 2: (2,0) -> Rotate 90: (0,2) -> Translate (10,10): (10, 12)
    assert math.isclose(p2.x, 10.0, abs_tol=1e-9)
    assert math.isclose(p2.y, 12.0, abs_tol=1e-9)


def test_bounds_union_empty():
    assert Bounds.union() == Bounds(0, 0, 0, 0)


def test_shape_base_methods():
    from tesserax.base import Rect

    r = Rect(10, 10)
    # resolve without parent
    assert r.resolve(Point(0, 0)) == Point(0, 0)

    # align_to default other_anchor
    r2 = Rect(10, 10).translated(100, 100)
    r2.align_to(r, "center")
    assert r2.transform.tx == 0
    assert r2.transform.ty == 0


def test_component_base_render():
    from tesserax.core import Component
    from tesserax.base import Rect

    class MyComp(Component):
        def _build(self):
            return Rect(10, 10)

    c = MyComp()
    assert "<rect" in c._render()
