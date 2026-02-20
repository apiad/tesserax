import pytest
from tesserax.core import Point, Bounds
from tesserax.base import Group, Rect
from tesserax.path import Grid

def test_grid_rasterize():
    g = Group()
    r = Rect(20, 20).translated(10, 10) # Bounds (0,0,20,20)
    g.add(r)
    
    grid = Grid(g, size=10)
    # At size 10, bounds (0,0,20,20) should occupy (0,0), (1,0), (2,0), (0,1), (1,1), (2,1), (0,2), (1,2), (2,2)
    # approx. 
    assert (0, 0) in grid.occupied
    assert (1, 1) in grid.occupied
    assert (2, 2) in grid.occupied

def test_path_simple():
    g = Group()
    grid = Grid(g, size=10)
    start = Point(0, 0)
    end = Point(50, 0)
    
    path = grid.trace(start, end)
    assert len(path) >= 2
    assert path[0] == start
    assert path[-1] == end

def test_path_with_obstacle():
    g = Group()
    # Obstacle in the middle of (0,0) to (100,0)
    # Place a large rect at (50, 0)
    r = Rect(20, 100).translated(50, 0) # Bounds (40, -50, 20, 100)
    g.add(r)
    
    grid = Grid(g, size=10)
    start = Point(0, 0)
    end = Point(100, 0)
    
    path = grid.trace(start, end)
    
    # Path should not go through the obstacle (40 <= x <= 60)
    for p in path:
        # If it's a point inside the rect, it's bad
        # Note: path simplification might have points outside but segments might cross.
        # But here we just check if any vertex is inside the occupancy grid
        gx, gy = grid._to_grid(p.x, p.y)
        assert (gx, gy) not in grid.occupied or p == start or p == end

def test_snap_to_free():
    g = Group()
    # Fill a large area
    r = Rect(100, 100).translated(0, 0) # (-50,-50, 100, 100)
    g.add(r)
    
    grid = Grid(g, size=10)
    # (0,0) is occupied. Snap should find something outside.
    gx, gy = grid._snap_to_free(0, 0, 10, 10)
    assert (gx, gy) not in grid.occupied

def test_resolve_elbow():
    grid = Grid(Group(), size=10)
    p_user = Point(0, 0)
    p_grid = Point(10, 10)
    p_next = Point(20, 10) # Horizontal movement
    
    # Path moving horizontally (dx > dy), we want to exit horizontally
    # Elbow should have same Y as p_grid (10), same X as p_user (0)
    elbow = grid._resolve_elbow(p_user, p_grid, p_next)
    assert elbow == Point(0, 10)
