import math
import heapq
from typing import Iterator
from tesserax.core import Point, Bounds, Shape
from tesserax.base import Group


class Grid:
    def __init__(self, group: Group, size: float = 10.0, limit: int = 10000):
        self.group = group
        self.size = size
        self.limit = limit  # Prevent infinite loops
        self.occupied: set[tuple[int, int]] = set()
        self.bounds_idx: tuple[int, int, int, int] = (0, 0, 0, 0)

        self._rasterize()

    def _to_grid(self, x: float, y: float) -> tuple[int, int]:
        return (math.floor(x / self.size + 0.5), math.floor(y / self.size + 0.5))

    def _to_world(self, gx: int, gy: int) -> Point:
        return Point(gx * self.size, gy * self.size)

    def _rasterize(self):
        self.occupied.clear()

        # Track min/max to define a search bounding box
        min_gx, min_gy = float("inf"), float("inf")
        max_gx, max_gy = float("-inf"), float("-inf")

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
        self.bounds_idx = (
            int(min_gx - pad),
            int(min_gy - pad),
            int(max_gx + pad),
            int(max_gy + pad),
        )

    def _snap_to_free(
        self, gx: int, gy: int, target_gx: int, target_gy: int
    ) -> tuple[int, int]:
        """
        Finds the nearest free cell to (gx, gy).
        Tie-breaker: Pick the cell closest to (target_gx, target_gy).
        """
        if (gx, gy) not in self.occupied:
            return (gx, gy)

        # Search in expanding rings to ensure we find the strictly nearest cells first
        r = 1
        max_r = 20  # Search radius limit

        while r < max_r:
            candidates = []

            # Iterate only the perimeter of the box at radius r
            # Top and Bottom rows
            for dx in range(-r, r + 1):
                candidates.append((gx + dx, gy - r))
                candidates.append((gx + dx, gy + r))

            # Left and Right columns (excluding corners already added)
            for dy in range(-r + 1, r):
                candidates.append((gx - r, gy + dy))
                candidates.append((gx + r, gy + dy))

            # Filter for valid (free) candidates
            valid_candidates = [c for c in candidates if c not in self.occupied]

            if valid_candidates:
                # HEURISTIC: Choose the candidate with minimum Euclidean distance to the target
                # This biases the snap to move "towards" the destination.
                return min(
                    valid_candidates,
                    key=lambda c: (c[0] - target_gx) ** 2 + (c[1] - target_gy) ** 2,
                )

            r += 1

        return (gx, gy)  # Fail-safe

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

    def _resolve_elbow(
        self, p_user: Point, p_grid: Point, p_next: Point
    ) -> Point | None:
        """
        Calculates an intermediate point (elbow) to ensure orthogonal connection.
        Strategy: Align the elbow segment with the dominant direction of the path.
        """
        # If already aligned, no elbow needed
        if abs(p_user.x - p_grid.x) < 1e-6 or abs(p_user.y - p_grid.y) < 1e-6:
            return p_grid

        # Determine flow direction of the grid path
        dx = p_next.x - p_grid.x
        dy = p_next.y - p_grid.y

        # If path is moving Horizontally, we want to enter/exit horizontally
        # to avoid Z-shapes.
        if abs(dx) > abs(dy):
            # Elbow should have same Y as p_grid, same X as p_user
            return Point(p_user.x, p_grid.y)

        # If path is moving Vertically (or stationary), enter/exit vertically
        else:
            # Elbow should have same X as p_grid, same Y as p_user
            return Point(p_grid.x, p_user.y)

    def trace(self, start: Point, end: Point, *, turn_penalty=1.0) -> list[Point]:
        """A* Pathfinding with safety limits."""
        raw_start = self._to_grid(start.x, start.y)
        raw_end = self._to_grid(end.x, end.y)

        # Fix: Ensure start/end are actually walkable
        start_node = self._snap_to_free(*raw_start, *raw_end)
        end_node = self._snap_to_free(*raw_end, *raw_start)

        # State: (x, y, dx, dy)
        # dx, dy represent the direction we ARRIVED from.
        # For start node, we infer a "virtual" arrival direction based on the User->Grid vector
        # This helps the path align immediately with the user's anchor.
        start_dx = 0
        start_dy = 0

        if start_node != raw_start:
            # If we snapped, the direction is from Raw to Snapped
            start_dx = start_node[0] - raw_start[0]
            start_dy = start_node[1] - raw_start[1]
            # Normalize to -1, 0, 1
            if start_dx != 0: start_dx //= abs(start_dx)
            if start_dy != 0: start_dy //= abs(start_dy)

        initial_state = (start_node[0], start_node[1], start_dx, start_dy)

        open_set = []
        heapq.heappush(open_set, (0, initial_state))

        came_from = {}
        g_score = {initial_state: 0.0}

        final_state = None
        iterations = 0

        while open_set:
            iterations += 1
            if iterations > self.limit:
                return [start, end]

            _, current = heapq.heappop(open_set)
            cx, cy, cdx, cdy = current

            if (cx, cy) == end_node:
                final_state = current
                break

            for nx, ny in self._neighbors(cx, cy):
                # Calculate new direction
                ndx = nx - cx
                ndy = ny - cy

                # Calculate Cost
                # Base movement cost = 1
                move_cost = 1

                # Turn Penalty
                # If we had a previous direction (cdx!=0 or cdy!=0) and it changed...
                if (cdx != 0 or cdy != 0) and (ndx != cdx or ndy != cdy):
                    move_cost += turn_penalty

                new_g = g_score[current] + move_cost
                next_state = (nx, ny, ndx, ndy)

                if next_state not in g_score or new_g < g_score[next_state]:
                    g_score[next_state] = new_g

                    # Heuristic (Manhattan)
                    h = abs(end_node[0] - nx) + abs(end_node[1] - ny)

                    heapq.heappush(open_set, (new_g + h, next_state))
                    came_from[next_state] = current

        if not final_state:
            return [start, end]

        # Reconstruct path
        path = []
        curr = final_state
        while curr in came_from:
            path.append((curr[0], curr[1]))
            curr = came_from[curr]
        path.append(start_node)
        path.reverse()

        # Simplify Path (Collinear Check)
        if len(path) < 3:
            return [start, end]

        simplified = [self._to_world(*path[0])]  # Use exact start point
        last_dir = (path[1][0] - path[0][0], path[1][1] - path[0][1])

        for i in range(2, len(path)):
            curr_dir = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
            if curr_dir != last_dir:
                simplified.append(self._to_world(*path[i - 1]))
                last_dir = curr_dir

        simplified.append(self._to_world(*path[-1]))  # Use exact end point

        if len(simplified) == 1:
            simplified = simplified * 2

        return (
            [start, self._resolve_elbow(start, simplified[0], simplified[1])]
            + simplified[1:-1]
            + [self._resolve_elbow(end, simplified[-1], simplified[-2]), end]
        )
