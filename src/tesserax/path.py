import math
import heapq
from typing import Iterator
from tesserax.core import Point, Bounds, Shape
from tesserax.base import Group

class Grid:
    def __init__(self, group: Group, size: float = 10.0, limit: int = 10000):
        self.group = group
        self.size = size
        self.limit = limit # Prevent infinite loops
        self.occupied: set[tuple[int, int]] = set()
        self.bounds_idx: tuple[int, int, int, int] = (0, 0, 0, 0)

        self._rasterize()

    def _to_grid(self, x: float, y: float) -> tuple[int, int]:
        return (
            math.floor(x / self.size + 0.5),
            math.floor(y / self.size + 0.5)
        )

    def _to_world(self, gx: int, gy: int) -> Point:
        return Point(gx * self.size, gy * self.size)

    def _rasterize(self):
        self.occupied.clear()

        # Track min/max to define a search bounding box
        min_gx, min_gy = float('inf'), float('inf')
        max_gx, max_gy = float('-inf'), float('-inf')

        for shape in self.group.shapes:
            b = shape.bounds()
            gx1, gy1 = self._to_grid(b.x, b.y)
            gx2, gy2 = self._to_grid(b.x + b.width, b.y + b.height)

            # Update global grid bounds
            min_gx, min_gy = min(min_gx, gx1), min(min_gy, gy1)
            max_gx, max_gy = max(max_gx, gx2), max(max_gy, gy2)

            for gx in range(gx1, gx2 + 1):
                for gy in range(gy1, gy2 + 1):
                    self.occupied.add((gx, gy))

        # Save bounds with generous padding (e.g., 10 cells)
        pad = 10
        self.bounds_idx = (int(min_gx - pad), int(min_gy - pad), int(max_gx + pad), int(max_gy + pad))

    def _snap_to_free(self, gx: int, gy: int) -> tuple[int, int]:
        """If (gx, gy) is occupied, find the nearest free cell."""
        if (gx, gy) not in self.occupied:
            return (gx, gy)

        # Spiral search for nearest free neighbor
        # (Simple BFS could also work, but spiral is deterministic for grid)
        r = 1
        while r < 10: # Don't search too far
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    nx, ny = gx + dx, gy + dy
                    if (nx, ny) not in self.occupied:
                        return (nx, ny)
            r += 1
        return (gx, gy) # Give up and return original (pathfinding will likely fail)

    def _neighbors(self, gx: int, gy: int) -> Iterator[tuple[int, int]]:
        min_x, min_y, max_x, max_y = self.bounds_idx

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = gx + dx, gy + dy

            # 1. Check Scene Bounds (Stops infinite expansion)
            if not (min_x <= nx <= max_x and min_y <= ny <= max_y):
                continue

            # 2. Check Collision
            if (nx, ny) not in self.occupied:
                yield (nx, ny)

    def trace(self, start: Point, end: Point) -> list[Point]:
        """A* Pathfinding with safety limits."""
        raw_start = self._to_grid(start.x, start.y)
        raw_end = self._to_grid(end.x, end.y)

        # Fix: Ensure start/end are actually walkable
        start_node = self._snap_to_free(*raw_start)
        end_node = self._snap_to_free(*raw_end)

        open_set = []
        heapq.heappush(open_set, (0, start_node))

        came_from = {}
        g_score = {start_node: 0}

        final_node = None
        iterations = 0

        while open_set:
            # Safety Brake
            iterations += 1
            if iterations > self.limit:
                print("Warning: A* search limit reached. Returning straight line.")
                return [start, end]

            _, current = heapq.heappop(open_set)

            if current == end_node:
                final_node = current
                break

            for next_node in self._neighbors(*current):
                new_g = g_score[current] + 1

                if next_node not in g_score or new_g < g_score[next_node]:
                    g_score[next_node] = new_g
                    h = abs(end_node[0] - next_node[0]) + abs(end_node[1] - next_node[1])
                    heapq.heappush(open_set, (new_g + h, next_node))
                    came_from[next_node] = current

        if not final_node:
            return [start, end]

        # Reconstruct path
        path = []
        curr = final_node
        while curr in came_from:
            path.append(curr)
            curr = came_from[curr]
        path.append(start_node)
        path.reverse()

        # Simplify Path (Collinear Check)
        if len(path) < 3:
            return [start, end]

        simplified = [self._to_world(*path[0])] # Use exact start point
        last_dir = (path[1][0] - path[0][0], path[1][1] - path[0][1])

        for i in range(2, len(path)):
            curr_dir = (path[i][0] - path[i-1][0], path[i][1] - path[i-1][1])
            if curr_dir != last_dir:
                simplified.append(self._to_world(*path[i-1]))
                last_dir = curr_dir

        simplified.append(self._to_world(*path[-1])) # Use exact end point

        return [start] + simplified + [end]
