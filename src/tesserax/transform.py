from __future__ import annotations
import math
from dataclasses import dataclass
from .core import Shape, Bounds, Point


@dataclass
class Transform(Shape):
    shape: Shape
    tx: float = 0.0
    ty: float = 0.0
    rotation: float = 0.0  # Degrees
    scale: float = 1.0

    def bounds(self) -> Bounds:
        """Computes the new bounds by applying transformations to the shape's corners."""
        base = self.shape.bounds()

        # 1. Get the 4 corners of the original bounding box
        corners = [
            Point(base.x, base.y),
            Point(base.x + base.width, base.y),
            Point(base.x, base.y + base.height),
            Point(base.x + base.width, base.y + base.height),
        ]

        # 2. Apply transformations to each corner
        transformed_points = []
        rad = math.radians(self.rotation)

        for p in corners:
            # Scale
            px, py = p.x * self.scale, p.y * self.scale
            # Rotate (around the origin 0,0)
            rx = px * math.cos(rad) - py * math.sin(rad)
            ry = px * math.sin(rad) + py * math.cos(rad)
            # Translate
            transformed_points.append(Point(rx + self.tx, ry + self.ty))

        # 3. Find the new min/max to form the axis-aligned bounding box (AABB)
        xs = [p.x for p in transformed_points]
        ys = [p.y for p in transformed_points]

        return Bounds(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def render(self) -> str:
        ops = []
        if self.tx != 0 or self.ty != 0:
            ops.append(f"translate({self.tx} {self.ty})")
        if self.rotation != 0:
            ops.append(f"rotate({self.rotation})")
        if self.scale != 1.0:
            ops.append(f"scale({self.scale})")

        transform_str = " ".join(ops)
        return f'<g transform="{transform_str}">\n  {self.shape.render()}\n</g>'

    def transformed(self, dx: float = 0, dy: float = 0, r: float = 0, s: float = 1) -> Transform:
        self.tx += dx
        self.ty += dy
        self.rotation += r
        self.scale += s

        return self
