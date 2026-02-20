import pytest
from tesserax import Circle, Point
from tesserax.physics.core import Body
from tesserax.physics.forces import InverseDistanceField, Drag

def test_inverse_distance_field():
    b = Body(Circle(5))
    b.pos = Point(100, 0)
    
    # Field at (0,0) attracting things
    field = InverseDistanceField(intensity=1000, center=Point(0, 0))
    field.apply([b])
    
    # Should have acceleration towards origin (negative x)
    assert b.acc.x < 0

def test_drag():
    b = Body(Circle(5))
    b.vel = Point(100, 0)
    
    drag = Drag(k=0.1)
    drag.apply([b])
    
    # Acceleration opposite to velocity
    assert b.acc.x < 0
