from __future__ import annotations
import math
from typing import Callable, Literal, Self
from .core import Anchor, Point, Shape, Bounds


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

    def add(self, *shapes: Shape, mode: Literal["strict", "loose"] = "strict") -> Group:
        """Adds a shape and returns self for chaining."""
        for shape in shapes:
            if shape.parent:
                if mode == "strict":
                    raise RuntimeError("This shape already has a parent")
                else:
                    continue

            self.shapes.append(shape)
            shape.parent = self

        return self

    def remove(self, shape: Shape) -> Self:
        self.shapes.remove(shape)
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
        self.add(*self.stack.pop(), mode="loose")

    def align(
        self,
        axis: Literal["horizontal", "vertical", "both"] = "both",
        anchor: Anchor = "center",
    ) -> Self:
        """
        Aligns all children in the group relative to the anchor of the first child.

        The alignment is performed in the group's local coordinate system by
        adjusting the translation (tx, ty) of each shape.
        """
        if not self.shapes:
            return self

        # The first shape acts as the reference datum for the alignment
        first = self.shapes[0]
        ref_p = first.transform.map(first.local().anchor(anchor))

        for shape in self.shapes[1:]:
            # Calculate the child's anchor point in the group's coordinate system
            curr_p = shape.transform.map(shape.local().anchor(anchor))

            if axis in ("horizontal", "both"):
                shape.transform.tx += ref_p.x - curr_p.x

            if axis in ("vertical", "both"):
                shape.transform.ty += ref_p.y - curr_p.y

        return self

    def distribute(
        self,
        axis: Literal["horizontal", "vertical"],
        size: float | None = None,
        mode: Literal["tight", "space-between", "space-around"] = "tight",
        gap: float = 0.0,
    ) -> Self:
        """
        Distributes children along an axis using rigid or flexible spacing.
        """
        if not self.shapes:
            return self

        # 1. Reset and Measure
        for s in self.shapes:
            if isinstance(s, Spring):
                s._size = 0.0

        springs = [s for s in self.shapes if isinstance(s, Spring)]
        total_flex = sum(s.flex for s in springs)
        n = len(self.shapes)

        # 2. Calculate Spacing Logic
        is_horiz = axis == "horizontal"
        rigid_total = sum(
            s.local().width if is_horiz else s.local().height
            for s in self.shapes
            if not isinstance(s, Spring)
        )

        effective_gap = gap
        start_offset = 0.0
        spring_unit = 0.0

        if size is not None:
            if springs:
                # Springs take all space not occupied by rigid shapes and fixed gaps
                remaining = size - rigid_total - (gap * (n - 1))
                spring_unit = max(0, remaining / total_flex) if total_flex > 0 else 0
            elif mode == "space-between" and n > 1:
                effective_gap = (size - rigid_total) / (n - 1)
            elif mode == "space-around":
                effective_gap = (size - rigid_total) / n
                start_offset = effective_gap / 2

        # 3. Apply Translations
        cursor = start_offset
        for s in self.shapes:
            b = s.local()

            if isinstance(s, Spring):
                s._size = s.flex * spring_unit
                cursor += s._size
            else:
                if is_horiz:
                    s.transform.tx = cursor - b.x
                    cursor += b.width + effective_gap
                else:
                    s.transform.ty = cursor - b.y
                    cursor += b.height + effective_gap

        return self


class Path(Shape):
    """
    A shape defined by an SVG path data string.
    Maintains an internal cursor to support relative movements and
    layout bounding box calculations.
    """

    def __init__(
        self,
        fill: str = "transparent",
        stroke: str = "black",
        width: float = 1,
        marker_start: str | None = None,
        marker_end: str | None = None,
    ) -> None:
        super().__init__()
        self.stroke = stroke
        self.fill = fill
        self.width = width
        self.marker_start = marker_start
        self.marker_end = marker_end
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

    def jump_to(self, x: float, y: float) -> Self:
        """Moves the pen to the absolute coordinates (x, y)."""
        self._commands.append(f"M {x} {y}")
        self._update_cursor(x, y)
        return self

    def arc(
        self,
        rx: float,
        ry: float,
        rot: float,
        large: int,
        sweep: int,
        x: float,
        y: float,
    ) -> Self:
        """
        Public Arc command matching SVG 'A'.
        """
        self._commands.append(f"A {rx} {ry} {rot} {large} {sweep} {x} {y}")
        # Note: Bounds calculation for arcs is complex; we approximate with start/end
        self._update_cursor(x, y)
        return self

    def jump_by(self, dx: float, dy: float) -> Self:
        """Moves the pen relative to the current position."""
        x, y = self._cursor
        return self.jump_to(x + dx, y + dy)

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
        d = " ".join(self._commands)
        ms = f'marker-start="url(#{self.marker_start})"' if self.marker_start else ""
        me = f'marker-end="url(#{self.marker_end})"' if self.marker_end else ""

        return (
            f'<path d="{d}" fill="{self.fill}" '
            f'stroke="{self.stroke}" stroke-width="{self.width}" '
            f"{ms} {me} />"
        )


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
        fill: str = "transparent",
        stroke: str = "black",
        width: float = 1.0,
        marker_start: str | None = None,
        marker_end: str | None = None,
    ) -> None:
        super().__init__(
            fill=fill,
            stroke=stroke,
            width=width,
            marker_start=marker_start,
            marker_end=marker_end,
        )

        self.points = points or []
        self.smoothness = smoothness
        self.closed = closed
        self._build()

    def add(self, p: Point) -> Self:
        self.points.append(p)
        return self

    def subdivide(self, times: int = 1) -> Self:
        """
        Linearly subdivides the polyline segments 'times' iterations.
        Inserts a midpoint between every pair of vertices.
        """
        for _ in range(times):
            if len(self.points) < 2:
                break

            new_pts = []
            count = len(self.points)

            # If closed, we interpolate the segment (Last -> First) too.
            # If open, we only go up to the second-to-last point.
            limit = count if self.closed else count - 1

            for i in range(limit):
                curr_p = self.points[i]
                # Modulo handles the wrap-around for the closed case
                next_p = self.points[(i + 1) % count]

                # Calculate midpoint
                mid = (curr_p + next_p) / 2

                new_pts.append(curr_p)
                new_pts.append(mid)

            # For open lines, we must manually append the final tip
            if not self.closed:
                new_pts.append(self.points[-1])

            self.points = new_pts

        self._build()  # Reconstruct SVG commands
        return self

    def apply(self, func: Callable[[Point], Point]) -> Self:
        """
        Applies a transformation function to every point in the polyline.
        Useful for non-affine transforms like sine waves or noise.
        """
        self.points = [func(p) for p in self.points]
        self._build()
        return self

    def _build(self) -> None:
        self._reset()

        if len(self.points) < 2:
            return

        s = max(0.0, min(1.0, self.smoothness))

        if self.closed:
            # CLOSED LOOP STRATEGY:
            # 1. Start at the midpoint of the segment connecting Last -> First.
            # 2. Iterate through ALL vertices (P0...Pn) and draw their rounded corners.
            # 3. Close the path, which connects the last corner's exit to the start midpoint.

            p_last = self.points[-1]
            p_first = self.points[0]

            # Move to the safe "middle" ground
            start_pt = p_last.lerp(p_first, 0.5)
            self.jump_to(start_pt.x, start_pt.y)

            n = len(self.points)
            for i in range(n):
                # Wrap indices to get neighbors
                prev = self.points[(i - 1) % n]
                curr = self.points[i]
                next = self.points[(i + 1) % n]

                v_in = curr - prev
                v_out = next - curr

                # Calculate radius (max is 50% of the shortest adjacent leg)
                radius = min(v_in.magnitude(), v_out.magnitude()) / 2.0 * s

                if radius < 1e-6:
                    # Sharp corner if radius is negligible
                    self.line_to(curr.x, curr.y)
                else:
                    # Round corner
                    p_start = curr - v_in.normalize() * radius
                    p_end = curr + v_out.normalize() * radius

                    self.line_to(p_start.x, p_start.y)
                    self.quadratic_to(curr.x, curr.y, p_end.x, p_end.y)

            self.close()

        else:
            # OPEN POLYLINE STRATEGY:
            # Start at P0, round internal corners, end at Pn.
            self.jump_to(self.points[0].x, self.points[0].y)

            for i in range(1, len(self.points) - 1):
                prev_p = self.points[i - 1]
                curr_p = self.points[i]
                next_p = self.points[i + 1]

                vec_in = curr_p - prev_p
                vec_out = next_p - curr_p

                radius = min(vec_in.magnitude(), vec_out.magnitude()) / 2.0 * s

                if radius < 1e-6:
                    self.line_to(curr_p.x, curr_p.y)
                else:
                    p_start = curr_p - vec_in.normalize() * radius
                    p_end = curr_p + vec_out.normalize() * radius

                    self.line_to(p_start.x, p_start.y)
                    self.quadratic_to(curr_p.x, curr_p.y, p_end.x, p_end.y)

            self.line_to(self.points[-1].x, self.points[-1].y)

    def _render(self) -> str:
        self._build()
        return super()._render()


class Text(Shape):
    """
    A text primitive with heuristic-based bounding box calculation.
    """

    def __init__(
        self,
        content: str,
        size: float = 12,
        font: str = "sans-serif",
        fill: str = "black",
        anchor: Literal["start", "middle", "end"] = "middle",
        baseline: Literal["top", "middle", "bottom"] = "middle",
    ) -> None:
        super().__init__()
        self.content = content
        self.size = size
        self.font = font
        self.fill = fill
        self._anchor = anchor
        self._baseline = baseline

    def local(self) -> Bounds:
        # Heuristic: average character width is ~60% of font size
        width = len(self.content) * self.size * 0.6
        height = self.size

        match self._anchor:
            case "start":
                return Bounds(0, -height + 2, width, height)
            case "middle":
                return Bounds(-width / 2, -height + 2, width, height)
            case "end":
                return Bounds(-width, -height + 2, width, height)
            case _:
                raise ValueError(f"Invalid anchor: {self._anchor}")

    def _render(self) -> str:
        # dominant-baseline="middle" or "alphabetic" helps vertical alignment
        # but "central" is often more predictable for layout centers.
        return (
            f'<text x="0" y="0" font-family="{self.font}" font-size="{self.size}" '
            f'fill="{self.fill}" text-anchor="{self._anchor}" dominant-baseline="{self._baseline}">'
            f"{self.content}</text>"
        )


class Spacer(Shape):
    """
    An invisible rectangular shape used to reserve fixed space in layouts.
    """

    def __init__(self, w: float, h: float) -> None:
        super().__init__()
        self.w, self.h = w, h

    def local(self) -> Bounds:
        return Bounds(0, 0, self.w, self.h)

    def _render(self) -> str:
        return ""


class Ghost(Shape):
    """
    A shape that proxies the bounds of a target shape without rendering.
    """

    def __init__(self, target: Shape) -> None:
        super().__init__()
        self.target = target

    def local(self) -> Bounds:
        """Returns the current local bounds of the target shape."""
        return self.target.local()

    def _render(self) -> str:
        return ""


class Spring(Shape):
    """
    A flexible spacer that expands to fill available space in layouts.
    """

    def __init__(self, flex: float = 1.0) -> None:
        super().__init__()
        self.flex = flex
        self._size: float = 0.0

    def local(self) -> Bounds:
        # Returns a 0-width/height bound unless size is set by distribute()
        return Bounds(0, 0, self._size, self._size)

    def _render(self) -> str:
        return ""


class Line(Path):
    """
    A connection between two points with optional curvature.
    curvature: 0 = straight
               1 = semicircle (right/clockwise)
              -1 = semicircle (left/counter-clockwise)
    """

    def __init__(
        self,
        p1: Point | Callable[[], Point],
        p2: Point | Callable[[], Point],
        curvature: float = 0.0,
        stroke: str = "black",
        width: float = 1.0,
        marker_start: str | None = None,
        marker_end: str | None = None,
    ) -> None:
        super().__init__(
            stroke=stroke,
            width=width,
            fill="transparent",
            marker_start=marker_start,
            marker_end=marker_end,
        )
        self.p1 = p1
        self.p2 = p2
        self.curvature = curvature
        # We build immediately to set initial bounds, but _render will rebuild
        self._build()

    def _resolve(self) -> tuple[Point, Point]:
        p1 = self.p1() if callable(self.p1) else self.p1
        p2 = self.p2() if callable(self.p2) else self.p2
        return p1, p2

    def _build(self) -> None:
        self._reset()
        start, end = self._resolve()

        self.jump_to(start.x, start.y)

        if abs(self.curvature) < 1e-4:
            self.line_to(end.x, end.y)
        else:
            dx = end.x - start.x
            dy = end.y - start.y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist == 0:
                return

            # Math for constant curvature arc
            # Sagitta (height of arc) = curvature * (dist / 2)
            # This maps curvature=1 to a full semicircle
            s = self.curvature * (dist / 2.0)

            # Radius calculation
            # R = (s^2 + (w/2)^2) / 2|s|
            r = (s**2 + (dist / 2.0) ** 2) / (2 * abs(s))

            # SVG Flags
            large_arc = (
                0  # Since we limit curvature to [-1, 1], we never go beyond 180 deg
            )
            sweep = 1 if self.curvature > 0 else 0

            self.arc(r, r, 0, large_arc, sweep, end.x, end.y)

    def _render(self) -> str:
        # Re-build to support dynamic points (e.g. from Layouts)
        self._build()
        return super()._render()


class Arrow(Line):
    """
    A Line that defaults to having an arrow marker at the end.
    """

    def __init__(
        self,
        p1: Point | Callable[[], Point],
        p2: Point | Callable[[], Point],
        curvature: float = 0.0,
        stroke: str = "black",
        width: float = 1.0,
        marker_start: str | None = None,
        marker_end: str | None = "arrow",  # Default to standard arrow
    ) -> None:
        super().__init__(
            p1,
            p2,
            curvature,
            stroke,
            width,
            marker_start=marker_start,
            marker_end=marker_end,
        )
