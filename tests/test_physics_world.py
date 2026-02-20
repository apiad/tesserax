import pytest
from tesserax import Rect, Circle, Point
from tesserax.physics.world import World
from tesserax.physics.forces import Gravity


def test_world_init():
    w = World()
    assert len(w.bodies) == 0
    assert len(w.fields) == 0


def test_world_add_body():
    w = World()
    r = Rect(10, 10)
    body = w.add(r, mass=5.0)
    assert len(w.bodies) == 1
    assert w.bodies[0].mass == 5.0
    assert w.bodies[0].shape == r


def test_world_simulate():
    w = World()
    r = Circle(5)
    body = w.add(r)
    body.pos = Point(0, 0)
    body.vel = Point(10, 0)  # Moving right

    # 1 second simulation, 0.1 dt = 10 steps
    anim = w.simulate(duration=1.0, dt=0.1)

    assert len(anim.children) == 1
    # After 1s at vel 10, should be near 10
    assert body.pos.x > 5
    assert anim.bounds is not None
    assert anim.bounds.width >= 10


def test_world_gravity():
    w = World()
    w.fields.append(Gravity(10.0))  # Gravity down
    r = Circle(5)
    body = w.add(r)
    body.pos = Point(0, 0)

    w._step(0.1)
    # Velocity should have increased downwards
    assert body.vel.y > 0
    assert body.pos.y > 0


def test_static_bodies_dont_move():
    w = World()
    w.fields.append(Gravity(10.0))
    r = Circle(5)
    body = w.add(r, static=True)
    body.pos = Point(0, 0)

    w._step(0.1)
    assert body.pos.y == 0
    assert body.vel.y == 0


def test_collision_resolution_smoke():
    w = World()
    c1 = Circle(10)
    c2 = Circle(10)
    b1 = w.add(c1)
    b2 = w.add(c2)

    b1.pos = Point(0, 0)
    b2.pos = Point(15, 0)  # Overlapping (radius 10+10=20 > 15)

    # This should trigger collision resolution in _step
    w._step(0.01)

    # They should have been pushed apart or at least have some velocity now
    assert b1.pos.x != 0 or b2.pos.x != 15
