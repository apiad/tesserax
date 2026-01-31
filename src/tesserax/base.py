from __future__ import annotations
from typing import Callable, Self
from .core import Point, Shape, Bounds


class Rect(Shape):
    """A rectangular shape, the foundation for arrays and memory blocks."""

    def __init__(
        self,
        w: float,
        h: float,
        stroke: str = "black",
        fill: str = "none",
    ) -> None:
        super().__init__()
        self.w, self.h = w, h
        self.stroke, self.fill = stroke, fill

    def local(self) -> Bounds:
        return Bounds(0, 0, self.w, self.h)

    def _render(self) -> str:
        return f'<rect x="0" y="0" width="{self.w}" height="{self.h}" stroke="{self.stroke}" fill="{self.fill}" />'


class Square(Rect):
    """A specialized Rect where width equals height."""

    def __init__(self, size: float, stroke: str = "black", fill: str = "none") -> None:
        super().__init__(size, size, stroke, fill)


class Circle(Shape):
    """A circle, ideal for nodes in trees or states in automata."""

    def __init__(self, r: float, stroke: str = "black", fill: str = "none") -> None:
        super().__init__()
        self.r = r
        self.stroke, self.fill = stroke, fill

    def local(self) -> Bounds:
        return Bounds(-self.r, -self.r, self.r * 2, self.r * 2)

    def _render(self) -> str:
        return f'<circle cx="0" cy="0" r="{self.r}" stroke="{self.stroke}" fill="{self.fill}" />'


class Ellipse(Shape):
    """An ellipse for when text labels are wider than they are tall."""

    def __init__(
        self,
        rx: float,
        ry: float,
        stroke: str = "black",
        fill: str = "none",
    ) -> None:
        super().__init__()
        self.rx, self.ry = rx, ry
        self.stroke, self.fill = stroke, fill

    def local(self) -> Bounds:
        return Bounds(-self.rx, -self.ry, self.rx * 2, self.ry * 2)

    def _render(self) -> str:
        return f'<ellipse cx="0" cy="0" rx="{self.rx}" ry="{self.ry}" stroke="{self.stroke}" fill="{self.fill}" />'


class Line(Shape):
    """A basic connection between two points, supports dynamic point resolution."""

    def __init__(
        self,
        p1: Point | Callable[[], Point],
        p2: Point | Callable[[], Point],
        stroke: str = "black",
        width: float = 1.0,
    ) -> None:
        super().__init__()
        self.p1, self.p2 = p1, p2
        self.stroke, self.width = stroke, width

    def _resolve(self) -> tuple[Point, Point]:
        """Resolves coordinates if they are provided as callables."""
        p1 = self.p1() if callable(self.p1) else self.p1
        p2 = self.p2() if callable(self.p2) else self.p2
        return p1, p2

    def local(self) -> Bounds:
        p1, p2 = self._resolve()
        x = min(p1.x, p2.x)
        y = min(p1.y, p2.y)
        return Bounds(x, y, abs(p1.x - p2.x), abs(p1.y - p2.y))

    def _render(self) -> str:
        p1, p2 = self._resolve()
        return (
            f'<line x1="{p1.x}" y1="{p1.y}" x2="{p2.x}" y2="{p2.y}" '
            f'stroke="{self.stroke}" stroke-width="{self.width}" />'
        )


class Arrow(Line):
    """A line with an arrowhead, resolving points dynamically during render."""

    def _render(self) -> str:
        p1, p2 = self._resolve()
        return (
            f'<line x1="{p1.x}" y1="{p1.y}" x2="{p2.x}" y2="{p2.y}" '
            f'stroke="{self.stroke}" stroke-width="{self.width}" marker-end="url(#arrowhead)" />'
        )


class Group(Shape):
    stack: list[list[Shape]] = []

    @classmethod
    def current(cls) -> list[Shape] | None:
        if cls.stack:
            return cls.stack[-1]

        return None

    """A collection of shapes that behaves as a single unit."""

    def __init__(self, shapes: list[Shape] | None = None) -> None:
        super().__init__()
        self.shapes: list[Shape] = []

        if shapes:
            self.add(*shapes)

    def add(self, *shapes: Shape) -> Group:
        """Adds a shape and returns self for chaining."""
        for shape in shapes:
            if shape.parent:
                raise ValueError("Cannot add one object to more than one group.")

            self.shapes.append(shape)
            shape.parent = self

        return self

    def local(self) -> Bounds:
        """Computes the union of all child bounds."""
        if not self.shapes:
            return Bounds(0, 0, 0, 0)

        return Bounds.union(*[s.bounds() for s in self.shapes])

    def _render(self) -> str:
        return "\n".join(s.render() for s in self.shapes)

    def __iadd__(self, other: Shape) -> Self:
        """Enables 'group += shape'."""
        self.shapes.append(other)
        return self

    def __enter__(self):
        self.stack.append([])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.add(*self.stack.pop())


class Path(Shape):
    """
    A shape defined by an SVG path data string.
    Maintains an internal cursor to support relative movements and
    layout bounding box calculations.
    """

    def __init__(self, stroke: str = "black", width: float = 1) -> None:
        super().__init__()
        self.stroke = stroke
        self.width = width
        self._reset()

    def _reset(self):
        self._commands: list[str] = []
        self._cursor: tuple[float, float] = (0.0, 0.0)

        self._min_x: float = float("inf")
        self._min_y: float = float("inf")
        self._max_x: float = float("-inf")
        self._max_y: float = float("-inf")

    def local(self) -> Bounds:
        """
        Returns the bounding box of the path in its local coordinate system.
        """
        if not self._commands:
            return Bounds(0, 0, 0, 0)

        width = self._max_x - self._min_x
        height = self._max_y - self._min_y

        return Bounds(self._min_x, self._min_y, width, height)

    def move_to(self, x: float, y: float) -> Self:
        """Moves the pen to the absolute coordinates (x, y)."""
        self._commands.append(f"M {x} {y}")
        self._update_cursor(x, y)
        return self

    def move_by(self, dx: float, dy: float) -> Self:
        """Moves the pen relative to the current position."""
        x, y = self._cursor
        return self.move_to(x + dx, y + dy)

    def line_to(self, x: float, y: float) -> Self:
        """Draws a straight line to the absolute coordinates (x, y)."""
        self._commands.append(f"L {x} {y}")
        self._update_cursor(x, y)
        return self

    def line_by(self, dx: float, dy: float) -> Self:
        """Draws a line relative to the current position."""
        x, y = self._cursor
        return self.line_to(x + dx, y + dy)

    def cubic_to(
        self,
        cp1_x: float,
        cp1_y: float,
        cp2_x: float,
        cp2_y: float,
        end_x: float,
        end_y: float,
    ) -> Self:
        """
        Draws a cubic Bezier curve to (end_x, end_y) using two control points.
        """
        self._commands.append(f"C {cp1_x} {cp1_y}, {cp2_x} {cp2_y}, {end_x} {end_y}")

        # We include control points in bounds to ensure the curve is
        # roughly contained, even though this is a loose approximation.
        self._expand_bounds(cp1_x, cp1_y)
        self._expand_bounds(cp2_x, cp2_y)
        self._update_cursor(end_x, end_y)
        return self

    def quadratic_to(self, cx: float, cy: float, ex: float, ey: float) -> Self:
        """
        Draws a quadratic Bezier curve to (ex, ey) with control point (cx, cy).
        """
        self._commands.append(f"Q {cx} {cy}, {ex} {ey}")
        self._expand_bounds(cx, cy)  # Approximate bounds including control point
        self._update_cursor(ex, ey)
        return self

    def close(self) -> Self:
        """Closes the path by drawing a line back to the start."""
        self._commands.append("Z")
        return self

    def _update_cursor(self, x: float, y: float) -> None:
        """Updates the internal cursor and expands the bounding box."""
        self._cursor = (x, y)
        self._expand_bounds(x, y)

    def _expand_bounds(self, x: float, y: float) -> None:
        """Updates the min/max bounds of the shape."""
        # Initialize bounds on first move if logic dictates,
        # or rely on 0,0 default if paths always start at origin.
        self._min_x = min(self._min_x, x)
        self._min_y = min(self._min_y, y)
        self._max_x = max(self._max_x, x)
        self._max_y = max(self._max_y, y)

    def _render(self) -> str:
        """Renders the standard SVG path element."""
        # You might want to offset commands by self.x/self.y if
        # this shape is moved by a Layout.
        d_attr = " ".join(self._commands)
        return f'<path d="{d_attr}" fill="none" stroke="{self.stroke}" stroke-width="{self.width}" />'


class Polyline(Path):
    """
    A sequence of connected lines with optional corner rounding.

    Args:
        points: List of vertices.
        smoothness: 0.0 (sharp) to 1.0 (fully rounded/spline-like).
        closed: If True, connects the last point back to the first.
    """

    def __init__(
        self,
        points: list[Point],
        smoothness: float = 0.0,
        closed: bool = False,
        stroke: str = "black",
        width: float = 1.0,
    ) -> None:
        super().__init__(stroke=stroke, width=width)

        self.points = points or []
        self.smoothness = smoothness
        self.closed = closed
        self._build()

    def add(self, p: Point) -> Self:
        self.points.append(p)
        return self

    def _build(self):
        self._reset()

        if not self.points:
            return

        # Clamp smoothness to 0-1 range
        s = max(0.0, min(1.0, self.smoothness))

        # Determine effective loop of points
        # If closed, we wrap around; if not, we handle start/end differently
        verts = self.points + ([self.points[0], self.points[1]] if self.closed else [])

        # 1. Move to the geometric start
        # If smoothing is on and not self.closed, we start exactly at P0
        # If closed, we start at the midpoint of the last segment (handled by loop)
        self.move_to(verts[0].x, verts[0].y)

        # We iterate through triplets: (Prev, Curr, Next)
        # But for an open polyline, we only round the *internal* corners.

        if len(verts) < 3:
            # Fallback for simple line
            for p in verts[1:]:
                self.line_to(p.x, p.y)

            return

        # Logic for Open Polyline
        # P0 -> ... -> Pn
        # We start at P0.
        # For every corner P_i, we draw a line to "Start of Curve", then curve to "End of Curve".

        # Start
        curr_p = verts[0]
        self.move_to(curr_p.x, curr_p.y)

        for i in range(1, len(verts) - 1):
            prev_p = verts[i - 1]
            curr_p = verts[i]
            next_p = verts[i + 1]

            # Vectors
            vec_in = curr_p - prev_p
            vec_out = next_p - curr_p

            len_in = vec_in.magnitude()
            len_out = vec_out.magnitude()

            # Corner Radius determination
            # We can't exceed 50% of the shortest leg, or curves will overlap
            max_r = min(len_in, len_out) / 2.0
            radius = max_r * s

            # Calculate geometric points
            # "Start of Curve" is back along the incoming vector
            p_start = curr_p - vec_in.normalize() * radius

            # "End of Curve" is forward along the outgoing vector
            p_end = curr_p + vec_out.normalize() * radius

            # Draw
            self.line_to(p_start.x, p_start.y)
            self.quadratic_to(curr_p.x, curr_p.y, p_end.x, p_end.y)

        # Finish at the last point
        last = verts[-1]
        self.line_to(last.x, last.y)

        if self.closed:
            self.close()

    def _render(self) -> str:
        self._build()
        return super()._render()
