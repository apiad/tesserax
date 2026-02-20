import pytest
import math
from tesserax import Circle, Point
from tesserax.physics.core import Body
from tesserax.physics.constraints import Rod, Spring

def test_rod_constraint():
    b1 = Body(Circle(5))
    b2 = Body(Circle(5))
    b1.pos = Point(0, 0)
    b2.pos = Point(100, 0) # Distance 100
    
    # Rod keeps fixed distance 50
    c = Rod(b1, b2, length=50)
    c.solve()
    
    # Should have moved towards each other
    dist = b1.pos.distance(b2.pos)
    assert math.isclose(dist, 50.0)

def test_spring_constraint():
    b1 = Body(Circle(5))
    b2 = Body(Circle(5))
    b1.pos = Point(0, 0)
    b2.pos = Point(100, 0)
    
    # Spring with rest length 50
    c = Spring(b1, b2, length=50, k=0.1)
    c.solve()
    
    # Spring applies forces
    assert b1.acc.x > 0
    assert b2.acc.x < 0

def test_spring_damping():
    b1 = Body(Circle(5))
    b2 = Body(Circle(5))
    b1.pos = Point(0, 0)
    b2.pos = Point(50, 0)
    b1.vel = Point(10, 0)
    b2.vel = Point(0, 0)
    
    # Rest length 50, so force_mag is 0. Only damping should act.
    c = Spring(b1, b2, length=50, k=1.0, damping=0.5)
    c.solve()
    
    # b1 moves towards b2, damping should oppose this (negative x force on b1)
    assert b1.acc.x < 0

def test_rod_static():
    b1 = Body(Circle(5), static=True)
    b2 = Body(Circle(5))
    b1.pos = Point(0, 0)
    b2.pos = Point(100, 0)
    
    c = Rod(b1, b2, length=50)
    c.solve()
    
    # b1 is static, so only b2 should move
    assert b1.pos == Point(0, 0)
    assert b2.pos == Point(50, 0)
