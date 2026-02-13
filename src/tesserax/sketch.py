from __future__ import annotations
import random
import math
from typing import Literal
from .core import Shape, Bounds, Point
from .base import Group, Path


class Sketch(Group):
    """
    A container that renders its children in a hand-drawn, "sketchy" style.
    It suppresses the default render of its children and replaces it with
    procedurally generated wobbly paths.
    """

    def __init__(
        self,
        shapes: list[Shape] | None = None,
        roughness: float = 1.0,
        bowing: float = 1.0,
        simplification: float = 0.5,
        seed: int = 42,
    ) -> None:
        super().__init__(shapes)
        self.roughness = roughness
        self.bowing = bowing
        self.simplification = simplification
        self.rng = random.Random(seed) if seed else random.Random()

    def _render(self) -> str:
        # Instead of asking children to render themselves, we trace them
        # and then render the sketchy version of that trace.

        svg_parts = []

        # We need to traverse the hierarchy manually
        queue = list(self.shapes)

        while queue:
            shape = queue.pop(0)

            # If it's a group, just unwrap it
            if isinstance(shape, Group) and not isinstance(shape, Sketch):
                # We need to apply the group's transform to the children
                # This is complex because transforms are usually applied at render time via <g transform="...">
                # Since we are hijacking render, we must manually compose transforms or wrap in <g>
                # Easier approach: Let trace() return local coords, and we wrap the result in the <g> for the child's transform.

                # However, for Sketch to work continuously across groups, we might want to flatten.
                # For V1, let's treat Group as a container and recurse.
                queue.extend(shape.shapes)
                continue

            # If it has a trace method, use it
            try:
                path = shape.trace().detach()
                sketch_path = self._sketchify(path)
                sketch_path.transform = shape.transform
                svg_parts.append(sketch_path.render())
            except NotImplementedError:
                svg_parts.append(shape.render())

        return "\n".join(svg_parts)

    def _sketchify(self, input_path: Path) -> Path:
        """
        Takes a clean Path and returns a new Path with wobbly double-strokes.
        """
        output = Path(
            fill=input_path.fill,
            stroke=input_path.stroke,
            width=input_path.width,
            marker_end=input_path.marker_end,  # Preserve markers? Maybe sketched markers later?
            marker_start=input_path.marker_start,
        )

        # Parse commands from the input path
        # This is a simple parser assuming the structure from base.Path
        # Ideally Path would expose an iterator of structured commands

        start = Point(0, 0)
        current = Point(0, 0)

        for cmd_str in input_path._commands:
            code = cmd_str[0]
            params = [float(x) for x in cmd_str[1:].replace(",", " ").split()]

            if code == "M":
                pt = Point(params[0], params[1])
                output.jump_to(pt.x, pt.y)
                start = pt
                current = pt

            elif code == "L":
                pt = Point(params[0], params[1])
                self._draw_wobbly_line(output, current, pt)
                current = pt

            elif code == "C":
                # Cubic Bezier
                cp1 = Point(params[0], params[1])
                cp2 = Point(params[2], params[3])
                end = Point(params[4], params[5])
                self._draw_wobbly_bezier(output, current, cp1, cp2, end)
                current = end

            elif code == "Z":
                self._draw_wobbly_line(output, current, start)
                current = start
                # We don't use close() because we want the hand-drawn mismatch look

            # TODO: Handle Q (Quadratic) and A (Arc) by converting to Cubic
            # For now, base.Path mostly generates Lines and Cubics (via Circle)

        return output

    def _draw_wobbly_line(self, path: Path, p1: Point, p2: Point):
        # Draw two lines with slight random offsets
        self._draw_curve_pass(path, p1, p2)
        self._draw_curve_pass(path, p1, p2)

    def _draw_curve_pass(self, path: Path, p1: Point, p2: Point):
        """
        Draws a single pass of a line, but curves it slightly using a cubic bezier.
        """
        dist = p1.distance(p2)

        if dist < 0.1:
            return

        # Roughness scaling
        r = self.roughness * 0.5

        # Random offsets for control points
        # We define a bezier that starts at p1, ends at p2,
        # but has control points shifted perpendicular to the line

        # Midpoint
        mid = (p1 + p2) / 2

        # Perpendicular vector
        perp = Point(-(p2.y - p1.y), p2.x - p1.x).normalize()

        # Random deviation
        dev1 = perp * self.rng.uniform(-r, r) * (dist * 0.1)
        dev2 = perp * self.rng.uniform(-r, r) * (dist * 0.1)

        # Add some overshoot/undershoot to endpoints
        overshoot = (p2 - p1).normalize() * self.rng.uniform(-r * 2, r * 2)

        start_pt = p1 - overshoot * 0.2
        end_pt = p2 + overshoot * 0.2

        cp1 = start_pt + (p2 - p1) * 0.3 + dev1
        cp2 = start_pt + (p2 - p1) * 0.7 + dev2

        path.jump_to(start_pt.x, start_pt.y)
        path.cubic_to(cp1.x, cp1.y, cp2.x, cp2.y, end_pt.x, end_pt.y)

    def _draw_wobbly_bezier(
        self, path: Path, start: Point, cp1: Point, cp2: Point, end: Point
    ):
        # Simplification: Just perturb the control points slightly
        # A full rough implementation estimates the curve length and subdivides

        r = self.roughness * 5

        def perturb(p):
            return Point(p.x + self.rng.uniform(-r, r), p.y + self.rng.uniform(-r, r))

        # Draw two passes
        for _ in range(2):
            path.jump_to(
                start.x, start.y
            )  # We assume start is roughly correct, or perturb it slightly
            path.cubic_to(
                perturb(cp1).x,
                perturb(cp1).y,
                perturb(cp2).x,
                perturb(cp2).y,
                perturb(end).x,
                perturb(end).y,
            )
