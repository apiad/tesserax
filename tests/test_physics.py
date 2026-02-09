import math
from tesserax.core import Point, Shape
from tesserax.base import Circle, Rect
from tesserax.physics.colliders import CircleCollider
from tesserax.physics.core import Body
from tesserax.physics.collisions import Collision

# --- Helpers ---


def create_body(shape_cls, *args, pos=(0, 0), rotation=0, **kwargs):
    """Factory to create a physics body at a specific location/rotation."""
    shape: Shape = shape_cls(*args, **kwargs)

    shape.move_to(Point(*pos))

    if rotation != 0:
        shape.rotated(math.radians(rotation))

    collider = CircleCollider(*args, **kwargs) if shape_cls is Circle else None
    return Body(shape, collider=collider)


def assert_collides(a: Body, b: Body):
    """Asserts that A and B logicially intersect."""
    collision = Collision.solve(a, b)
    assert (
        collision is not None
    ), f"Expected collision between {a} and {b}, but found None."


def assert_separate(a: Body, b: Body):
    """Asserts that A and B are logically separated."""
    collision = Collision.solve(a, b)
    assert collision is None, f"Expected no collision, but found {collision}."


# --- 1. Circle vs Circle Logic ---


def test_circles_intersecting():
    # Two circles (r=10) placed 10 units apart.
    # They should overlap significantly.
    a = create_body(Circle, 10, pos=(0, 0))
    b = create_body(Circle, 10, pos=(10, 0))
    assert_collides(a, b)


def test_circles_separated():
    # Two circles (r=10) placed 100 units apart.
    a = create_body(Circle, 10, pos=(0, 0))
    b = create_body(Circle, 10, pos=(100, 0))
    assert_separate(a, b)


def test_circles_touching_barely():
    # Radius 10. Centers at 0 and 19. Overlap is 1.0.
    # Should collide.
    a = create_body(Circle, 10, pos=(0, 0))
    b = create_body(Circle, 10, pos=(19, 0))
    assert_collides(a, b)


# --- 2. Box vs Box Logic ---


def test_boxes_intersecting_aabb():
    # Two 20x20 boxes overlapping.
    a = create_body(Rect, 20, 20, pos=(0, 0))
    b = create_body(Rect, 20, 20, pos=(10, 5))
    assert_collides(a, b)


def test_boxes_separated_aabb():
    # Two 20x20 boxes far apart.
    a = create_body(Rect, 20, 20, pos=(0, 0))
    b = create_body(Rect, 20, 20, pos=(50, 50))
    assert_separate(a, b)


def test_boxes_intersecting_rotated():
    # Box A is axis-aligned.
    # Box B is rotated 45 degrees and its corner pokes into A.
    a = create_body(Rect, 100, 100, pos=(0, 0))

    # Place B such that its center is outside, but rotation makes it hit.
    # Center X=60 (outside A's extent of 50).
    # But rotated corner should reach back into A.
    b = create_body(Rect, 40, 40, pos=(60, 0), rotation=45)

    assert_collides(a, b)


def test_boxes_separated_rotated():
    # Same setup, but B is moved further away so even the corner doesn't reach.
    a = create_body(Rect, 100, 100, pos=(0, 0))
    b = create_body(Rect, 40, 40, pos=(100, 0), rotation=45)
    assert_separate(a, b)


# --- 3. Circle vs Box Logic ---


def test_circle_inside_box():
    # Circle completely swallowed by box.
    a = create_body(Rect, 50, 50, pos=(0, 0))
    b = create_body(Circle, 5, pos=(0, 0))
    assert_collides(a, b)


def test_circle_hits_box_corner():
    # Box at origin (extents +/- 10).
    # Circle (r=5) at (12, 12).
    # Corner is at (10, 10). Dist to circle center is sqrt(2^2 + 2^2) = 2.82.
    # Radius is 5. 2.82 < 5. They collide.
    a = create_body(Rect, 20, 20, pos=(0, 0))
    b = create_body(Circle, 5, pos=(12, 12))
    assert_collides(a, b)


def test_circle_misses_box_corner():
    # Same setup but circle moved to (16, 16).
    # Dist to corner (10,10) is sqrt(6^2 + 6^2) = 8.48.
    # Radius is 5. 8.48 > 5. No collision.
    a = create_body(Rect, 20, 20, pos=(0, 0))
    b = create_body(Circle, 5, pos=(16, 16))
    assert_separate(a, b)
