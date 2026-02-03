import math
import heapq
from typing import Iterator
from tesserax.core import Point, Bounds, Shape
from tesserax.base import Group


class Grid:
    def __init__(self, group: Group, size: float = 10.0):
        self.group = group
        self.cell_size = size
        self.occupied: set[tuple[int, int]] = set()

        # Calculate bounds immediately
        self._rasterize()

    def _to_grid(self, x: float, y: float) -> tuple[int, int]:
        """Converts world coordinates to grid coordinates."""
        return (
            math.floor(x / self.cell_size + 0.5),
            math.floor(y / self.cell_size + 0.5)
        )

    def _to_world(self, gx: int, gy: int) -> Point:
        """Converts grid coordinates to world coordinates (center of cell)."""
        return Point(gx * self.cell_size, gy * self.cell_size)

    def _rasterize(self):
        """Marks cells as occupied based on shape bounds."""
        self.occupied.clear()

        # We assume the group's shapes are already positioned (layout applied)
        for shape in self.group.shapes:
            # Get the world-space bounds of the shape
            # (In a real scenario, we might need a more precise shape.resolve() method)
            b = shape.bounds()

            # Convert bounds to grid ranges
            min_gx, min_gy = self._to_grid(b.x, b.y)
            max_gx, max_gy = self._to_grid(b.x + b.width, b.y + b.height)

            # Mark all cells in the rectangle as occupied
            # We add a small padding logic if strictly necessary,
            # but bounds-based is what you asked for.
            for gx in range(min_gx, max_gx + 1):
                for gy in range(min_gy, max_gy + 1):
                    self.occupied.add((gx, gy))

    def _neighbors(self, gx: int, gy: int) -> Iterator[tuple[int, int]]:
        """Yields valid (non-occupied) neighbors."""
        # Manhattan neighbors: Up, Down, Left, Right
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = gx + dx, gy + dy
            if (nx, ny) not in self.occupied:
                yield (nx, ny)

    def trace(self, start: Point, end: Point) -> list[Point]:
        """
        A* Pathfinding from start to end avoiding obstacles.
        Returns a simplified list of Points (corners only).
        """
        s = self._to_grid(start.x, start.y)
        t = self._to_grid(end.x, end.y)

        # Priority Queue: (f_score, gx, gy)
        open_set = []
        heapq.heappush(open_set, (0, s))

        parent = {}
        cost = {s: 0}

        final = None

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == t:
                final = current
                break

            for n in self._neighbors(*current):
                g = cost[current] + 1 # cost is always 1 for grid

                if n not in cost or g < cost[n]:
                    cost[n] = g
                    # Heuristic: Manhattan distance
                    h = abs(t[0] - n[0]) + abs(t[1] - n[1])
                    f = g + h
                    heapq.heappush(open_set, (f, n))
                    parent[n] = current

        if not final:
            return [start, end] # Fallback: straight line if no path found

        # Reconstruct path
        path = []
        curr = final

        while curr in parent:
            path.append(curr)
            curr = parent[curr]

        path.append(s)
        path.reverse()

        # Simplify Path (Collinear Check)
        if len(path) < 3:
            return [start, end]

        simplified = [self._to_world(*path[0])]
        last_dir = (path[1][0] - path[0][0], path[1][1] - path[0][1])

        for i in range(2, len(path)):
            curr_dir = (path[i][0] - path[i-1][0], path[i][1] - path[i-1][1])
            if curr_dir != last_dir:
                # Direction changed, add the turning point (previous node)
                simplified.append(self._to_world(*path[i-1]))
                last_dir = curr_dir

        simplified.append(self._to_world(*path[-1]))

        # Replace strictly grid-snapped start/end with actual user points
        simplified[0] = start
        simplified[-1] = end

        return simplified


__all__ = ["Grid"]
