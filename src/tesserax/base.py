from __future__ import annotations
import math
from typing import Callable, Literal, Protocol, Self, TYPE_CHECKING, cast

from tesserax.color import Color, Colors
from .core import Anchor, IShape, Point, Shape, Bounds, Component

if TYPE_CHECKING:
    from .animation import StyledAnimator, TextAnimator, PolylineAnimator


class IVisual(IShape):
    fill: Color
    stroke: Color
    width: float
    opacity: float


class Visual(Shape, IVisual):
    def __init__(
        self,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
        width: float = 1.0,
        opacity: float = 1.0,
    ) -> None:
        super().__init__()
        self.fill = fill
        self.stroke = stroke
        self.width = width
        self.opacity = opacity

    @property
    def animate(self) -> StyledAnimator:
        from .animation import StyledAnimator

        if self._animator is None:
            self._animator = StyledAnimator(self)

        return cast(StyledAnimator, self._animator)

    def render(self) -> str:
        """Generates the SVG expression for this shape, including transformation and opacity."""
        if self.hidden:
            return ""

        t = self.transform
        
        # Build style string
        style_parts = []
        if self.opacity < 1.0:
            style_parts.append(f"opacity: {self.opacity};")
        
        style_attr = f' style="{" ".join(style_parts)}"' if style_parts else ""

        # Optimization: Return raw render if transform is identity
        if t.tx == 0 and t.ty == 0 and t.rotation == 0 and t.sx == 1 and t.sy == 1:
            if not style_parts:
                return self._render()
            return f"<g{style_attr}>\n{self._render()}\n</g>"

        # SVG rotate expects degrees, but Transform stores radians
        deg = math.degrees(t.rotation)

        ts = f' transform="translate({t.tx} {t.ty}) rotate({deg}) scale({t.sx} {t.sy})"'
        return f"<g{ts}{style_attr}>\n{self._render()}\n</g>"


class Rect(Visual):
    """A rectangular shape, the foundation for arrays and memory blocks."""

    def __init__(
        self,
        w: float,
        h: float,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
        width: float = 1.0,
    ) -> None:
        super().__init__(fill=fill, stroke=stroke, width=width)
        self.w, self.h = w, h

    def trace(self) -> Path:
        # A rectangle is a closed path of 4 lines
        # We start top-left (relative to center 0,0)
        hw, hh = self.w / 2, self.h / 2
        return (
            Path(fill=self.fill, stroke=self.stroke, width=self.width)
            .jump_to(-hw, -hh)
            .line_to(hw, -hh)
            .line_to(hw, hh)
            .line_to(-hw, hh)
            .close()
        )

    def local(self) -> Bounds:
        # Returns bounds centered at 0,0
        hw, hh = self.w / 2, self.h / 2
        return Bounds(-hw, -hh, self.w, self.h)

    def _render(self) -> str:
        # Render centered at 0,0
        # x and y are top-left coordinates relative to the origin
        return f'<rect x="{-self.w/2}" y="{-self.h/2}" width="{self.w}" height="{self.h}" stroke="{self.stroke}" fill="{self.fill}" />'


class Square(Visual):
    """A specialized Rect where width equals height."""

    def __init__(
        self,
        size: float,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
        width: float = 1.0,
    ) -> None:
        super().__init__(fill=fill, stroke=stroke, width=width)
        self.size = size

    def trace(self) -> Path:
        # A rectangle is a closed path of 4 lines
        # We start top-left (relative to center 0,0)
        hw, hh = self.size / 2, self.size / 2
        return (
            Path(fill=self.fill, stroke=self.stroke, width=self.width)
            .jump_to(-hw, -hh)
            .line_to(hw, -hh)
            .line_to(hw, hh)
            .line_to(-hw, hh)
            .close()
        )

    def local(self) -> Bounds:
        # Returns bounds centered at 0,0
        hw, hh = self.size / 2, self.size / 2
        return Bounds(-hw, -hh, self.size, self.size)

    def _render(self) -> str:
        # Render centered at 0,0
        # x and y are top-left coordinates relative to the origin
        return f'<rect x="{-self.size/2}" y="{-self.size/2}" width="{self.size}" height="{self.size}" stroke="{self.stroke}" fill="{self.fill}" />'


class Circle(Visual):
    """A circle, ideal for nodes in trees or states in automata."""

    def __init__(
        self,
        r: float,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
        width: float = 1.0,
    ) -> None:
        super().__init__(fill=fill, stroke=stroke, width=width)
        self.r = r

    def trace(self) -> Path:
        # Approximation of a circle using 4 cubic bezier curves
        # Kappa is the magic number for bezier circles
        kappa = 0.552284749831
        r = self.r
        k = r * kappa

        return (
            Path(fill=self.fill, stroke=self.stroke, width=self.width)
            .jump_to(r, 0)
            .cubic_to(r, k, k, r, 0, r)
            .cubic_to(-k, r, -r, k, -r, 0)
            .cubic_to(-r, -k, -k, -r, 0, -r)
            .cubic_to(k, -r, r, -k, r, 0)
            .close()
        )

    def local(self) -> Bounds:
        return Bounds(-self.r, -self.r, self.r * 2, self.r * 2)

    def _render(self) -> str:
        # cx, cy are center offsets relative to local transform (which is 0,0)
        return f'<circle cx="0" cy="0" r="{self.r}" stroke="{self.stroke}" fill="{self.fill}" />'


class Ellipse(Visual):
    """An ellipse for when text labels are wider than they are tall."""

    def __init__(
        self,
        rx: float,
        ry: float,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
        width: float = 1.0,
    ) -> None:
        super().__init__(fill=fill, stroke=stroke, width=width)
        self.rx, self.ry = rx, ry

    def trace(self) -> Path:
        # Kappa is the magic constant for approximating a quarter-circle/ellipse with a cubic Bezier
        kappa = 0.552284749831
        kx = self.rx * kappa
        ky = self.ry * kappa
        rx, ry = self.rx, self.ry

        return (
            Path(fill=self.fill, stroke=self.stroke, width=self.width)
            .jump_to(rx, 0)
            .cubic_to(rx, ky, kx, ry, 0, ry)  # Bottom-Right quadrant (0 to 90 deg)
            .cubic_to(-kx, ry, -rx, ky, -rx, 0)  # Bottom-Left quadrant (90 to 180 deg)
            .cubic_to(-rx, -ky, -kx, -ry, 0, -ry)  # Top-Left quadrant (180 to 270 deg)
            .cubic_to(kx, -ry, rx, -ky, rx, 0)  # Top-Right quadrant (270 to 360 deg)
            .close()
        )

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
                    shape.parent.remove(shape)

            self.shapes.append(shape)
            shape.parent = self

        return self

    def remove(self, shape: Shape) -> Self:
        self.shapes.remove(shape)
        shape.parent = None
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
        """
        if not self.shapes:
            return self

        first = self.shapes[0]
        # Map local anchor to parent space for comparison
        ref_p = first.transform.map(first.local().anchor(anchor))

        for shape in self.shapes[1:]:
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

        for s in self.shapes:
            if isinstance(s, Spring):
                s._size = 0.0

        springs = [s for s in self.shapes if isinstance(s, Spring)]
        total_flex = sum(s.flex for s in springs)
        n = len(self.shapes)

        is_horiz = axis == "horizontal"
        # Calculate rigid total based on children's bounds in parent space?
        # Ideally we use local size, but shapes might be scaled.
        # For now, we use local().width/height assuming no rotation/scale on children yet.
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
                remaining = size - rigid_total - (gap * (n - 1))
                spring_unit = max(0, remaining / total_flex) if total_flex > 0 else 0
            elif mode == "space-between" and n > 1:
                effective_gap = (size - rigid_total) / (n - 1)
            elif mode == "space-around":
                effective_gap = (size - rigid_total) / n
                start_offset = effective_gap / 2

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


class Text(Visual):
    """
    Text primitive. Default anchor is 'middle' for true centering.
    """

    def __init__(
        self,
        content: str,
        size: float = 12,
        font: str = "sans-serif",
        anchor: Literal["start", "middle", "end"] = "middle",
        baseline: Literal["top", "middle", "bottom"] = "middle",
        fill: Color = Colors.Black,
        stroke: Color = Colors.Transparent,
        width: float = 1.0,
    ) -> None:
        super().__init__(fill=fill, stroke=stroke, width=width)
        self.content = content
        self.size = size
        self.font = font
        self._anchor = anchor
        self._baseline = baseline

    @property
    def animate(self) -> TextAnimator:
        from .animation import TextAnimator

        if self._animator is None:
            self._animator = TextAnimator(self)

        return cast(TextAnimator, self._animator)

    def local(self) -> Bounds:
        # Heuristic: average character width is ~60% of font size
        width = len(self.content) * self.size * 0.6
        height = self.size

        # Bounds logic for "middle" anchor (which is the default now)
        # origin (0,0) is at the center of the text.
        if self._anchor == "middle":
            return Bounds(-width / 2, -height / 2, width, height)
        elif self._anchor == "start":
            return Bounds(0, -height / 2, width, height)
        elif self._anchor == "end":
            return Bounds(-width, -height / 2, width, height)
        return Bounds(0, 0, width, height)

    def _render(self) -> str:
        # Note: 'dominant-baseline="middle"' centers text vertically around y=0
        return (
            f'<text x="0" y="0" font-family="{self.font}" font-size="{self.size}" '
            f'fill="{self.fill}" text-anchor="{self._anchor}" dominant-baseline="{self._baseline}">'
            f"{self.content}</text>"
        )


class Invisible(Shape):
    def _render(self) -> str:
        return ""


class Spacer(Invisible):
    def __init__(self, w: float, h: float) -> None:
        super().__init__()
        self.w, self.h = w, h

    def local(self) -> Bounds:
        return Bounds(0, 0, self.w, self.h)


class Ghost(Invisible):
    def __init__(self, target: Shape) -> None:
        super().__init__()
        self.target = target

    def local(self) -> Bounds:
        return self.target.local()


class Spring(Invisible):
    def __init__(self, flex: float = 1.0) -> None:
        super().__init__()
        self.flex = flex
        self._size: float = 0.0

    def local(self) -> Bounds:
        return Bounds(0, 0, self._size, self._size)


class Path(Visual):
    """
    A shape defined by an SVG path data string.
    """

    def __init__(
        self,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
        width: float = 1.0,
        marker_start: str | None = None,
        marker_end: str | None = None,
    ) -> None:
        super().__init__(fill=fill, stroke=stroke, width=width)
        self.marker_start = marker_start
        self.marker_end = marker_end
        self.reset()

    def reset(self):
        self._commands: list[str] = []
        self._cursor: tuple[float, float] = (0.0, 0.0)
        self._min_x: float = float("inf")
        self._min_y: float = float("inf")
        self._max_x: float = float("-inf")
        self._max_y: float = float("-inf")

    def _trace(self) -> Path:
        # Path is already a Path, return a clone to be safe
        # We need to copy commands and style
        new_p = Path(
            fill=self.fill,
            stroke=self.stroke,
            width=self.width,
            marker_start=self.marker_start,
            marker_end=self.marker_end,
        )
        new_p._commands = list(self._commands)
        new_p._cursor = self._cursor
        # Copy bounds cache if needed, or let it recompute
        return new_p

    def local(self) -> Bounds:
        if not self._commands:
            return Bounds(0, 0, 0, 0)
        width = self._max_x - self._min_x
        height = self._max_y - self._min_y
        return Bounds(self._min_x, self._min_y, width, height)

    def jump_to(self, x: float, y: float) -> Self:
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
        self._commands.append(f"A {rx} {ry} {rot} {large} {sweep} {x} {y}")
        self._update_cursor(x, y)
        return self

    def jump_by(self, dx: float, dy: float) -> Self:
        x, y = self._cursor
        return self.jump_to(x + dx, y + dy)

    def line_to(self, x: float, y: float) -> Self:
        self._commands.append(f"L {x} {y}")
        self._update_cursor(x, y)
        return self

    def line_by(self, dx: float, dy: float) -> Self:
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
        self._commands.append(f"C {cp1_x} {cp1_y}, {cp2_x} {cp2_y}, {end_x} {end_y}")
        self._expand_bounds(cp1_x, cp1_y)
        self._expand_bounds(cp2_x, cp2_y)
        self._update_cursor(end_x, end_y)
        return self

    def quadratic_to(self, cx: float, cy: float, ex: float, ey: float) -> Self:
        self._commands.append(f"Q {cx} {cy}, {ex} {ey}")
        self._expand_bounds(cx, cy)
        self._update_cursor(ex, ey)
        return self

    def close(self) -> Self:
        self._commands.append("Z")
        return self

    def _update_cursor(self, x: float, y: float) -> None:
        self._cursor = (x, y)
        self._expand_bounds(x, y)

    def _expand_bounds(self, x: float, y: float) -> None:
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


# Path-based components start here


class Polyline(Component, IVisual):
    """
    A sequence of connected lines.
    Supports .center() to re-align points around the origin.
    """

    def __init__(
        self,
        points: list[Point],
        smoothness: float = 0.0,
        closed: bool = False,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
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

    @property
    def animate(self) -> PolylineAnimator:
        from .animation import PolylineAnimator

        if self._animator is None:
            self._animator = PolylineAnimator(self)

        return cast(PolylineAnimator, self._animator)

    def append(self, p: Point) -> Self:
        self.points.append(p)
        return self

    def prepend(self, p: Point) -> Self:
        self.points.insert(0, p)
        return self

    def extend(self, points: list[Point]) -> Self:
        self.points.extend(points)
        return self

    def center(self) -> Self:
        """
        Shifts all points so their bounding box center is at (0,0).
        Then updates the transform translation to compensate,
        keeping the shape visually in the same place.
        """
        if not self.points:
            return self

        # 1. Measure current bounds
        min_x = min(p.x for p in self.points)
        max_x = max(p.x for p in self.points)
        min_y = min(p.y for p in self.points)
        max_y = max(p.y for p in self.points)

        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2

        # 2. Shift points to center
        new_points = []
        for p in self.points:
            new_points.append(Point(p.x - cx, p.y - cy))
        self.points = new_points

        # 3. Compensate transform
        self.transform.tx += cx
        self.transform.ty += cy

        # 4. Rebuild path
        return self

    def subdivide(self, times: int = 1) -> Self:
        for _ in range(times):
            if len(self.points) < 2:
                break
            new_pts = []
            count = len(self.points)
            limit = count if self.closed else count - 1
            for i in range(limit):
                curr_p = self.points[i]
                next_p = self.points[(i + 1) % count]
                mid = (curr_p + next_p) / 2
                new_pts.append(curr_p)
                new_pts.append(mid)
            if not self.closed:
                new_pts.append(self.points[-1])
            self.points = new_pts
        return self

    def simplify(self, tolerance: float = 1e-2) -> Self:
        """
        Removes collinear points.
        If the distance of a point from the line segment connecting its neighbors
        is less than 'tolerance', the point is removed.
        """
        if len(self.points) < 3:
            return self

        # Iterative simplification
        # We create a new list and only add points that "matter"
        new_points = [self.points[0]]

        for i in range(1, len(self.points) - 1):
            prev = new_points[-1]  # Look at the last *kept* point
            curr = self.points[i]
            next_p = self.points[i + 1]

            d = Point.distance_to_segment(curr, prev, next_p)

            # If significant deviation, keep it.
            if d > tolerance:
                new_points.append(curr)

        new_points.append(self.points[-1])

        # If closed, check if start/end are collinear with the loop
        # (Omitted for brevity, but essentially check points[0] vs points[-1] and points[1])

        self.points = new_points
        return self

    def apply(self, func: Callable[[Point], Point]) -> Self:
        self.points = [func(p) for p in self.points]
        return self

    def _trace(self) -> Path:
        return cast(Path, self._build())

    def _build(self) -> Shape:
        shape = Path(**self.kwargs)
        s = max(0.0, min(1.0, self.smoothness))

        # TODO: Refactor both parts
        if self.closed:
            p_last = self.points[-1]
            p_first = self.points[0]
            start_pt = p_last.lerp(p_first, 0.5)
            shape.jump_to(start_pt.x, start_pt.y)

            n = len(self.points)
            for i in range(n):
                prev = self.points[(i - 1) % n]
                curr = self.points[i]
                next = self.points[(i + 1) % n]
                v_in = curr - prev
                v_out = next - curr
                radius = min(v_in.magnitude(), v_out.magnitude()) / 2.0 * s

                if radius < 1e-6:
                    shape.line_to(curr.x, curr.y)
                else:
                    p_start = curr - v_in.normalize() * radius
                    p_end = curr + v_out.normalize() * radius
                    shape.line_to(p_start.x, p_start.y)
                    shape.quadratic_to(curr.x, curr.y, p_end.x, p_end.y)
            shape.close()

        else:
            shape.jump_to(self.points[0].x, self.points[0].y)
            for i in range(1, len(self.points) - 1):
                prev_p = self.points[i - 1]
                curr_p = self.points[i]
                next_p = self.points[i + 1]
                vec_in = curr_p - prev_p
                vec_out = next_p - curr_p
                radius = min(vec_in.magnitude(), vec_out.magnitude()) / 2.0 * s
                if radius < 1e-6:
                    shape.line_to(curr_p.x, curr_p.y)
                else:
                    p_start = curr_p - vec_in.normalize() * radius
                    p_end = curr_p + vec_out.normalize() * radius
                    shape.line_to(p_start.x, p_start.y)
                    shape.quadratic_to(curr_p.x, curr_p.y, p_end.x, p_end.y)
            shape.line_to(self.points[-1].x, self.points[-1].y)

        return shape

    @classmethod
    def poly(
        cls, n: int, radius: float, orientation: Point | None = None, **kwargs
    ) -> Self:
        """
        Creates a regular polygon centered at (0,0).

        Args:
            n: Number of sides (3=Triangle, 4=Diamond/Square, 6=Hexagon).
            radius: Distance from center to vertex.
            orientation: Vector pointing to the first vertex. Defaults to Point.up.
        """
        if n < 3:
            raise ValueError("Polygon must have at least 3 sides")

        if orientation is None:
            orientation = Point(0, -1)  # Point.up

        # Calculate start angle from the orientation vector
        start_angle = math.atan2(orientation.y, orientation.x)
        step = 2 * math.pi / n

        points = []
        for i in range(n):
            theta = start_angle + i * step
            points.append(Point(radius * math.cos(theta), radius * math.sin(theta)))

        # Create closed polyline
        return cls(points, closed=True, **kwargs)

    def expand(self, delta: float) -> Self:
        """
        Pushes all points away from the origin (0,0) by an absolute amount.
        Useful for making a shape 'thicker' or 'larger' without scaling.

        Note: For best results, ensure the shape is centered first via .center().
        """
        new_points = []
        for p in self.points:
            mag = p.magnitude()
            if mag == 0:
                new_points.append(p)
            else:
                # P_new = P + unit_vector * delta
                # P_new = P + (P / mag) * delta
                # P_new = P * (1 + delta / mag)
                scale_factor = 1 + (delta / mag)
                new_points.append(p * scale_factor)

        self.points = new_points
        return self

    def contract(self, delta: float) -> Self:
        """
        Pulls all points towards the origin (0,0) by an absolute amount.
        Negative values will expand.
        """
        return self.expand(-delta)


class Line(Component):
    def __init__(
        self,
        p1: Point | Callable[[], Point],
        p2: Point | Callable[[], Point],
        curvature: float = 0.0,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
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
        self.p1 = p1
        self.p2 = p2
        self.curvature = curvature

        if callable(self.p1) or callable(self.p2):
            self._dynamic = True

    def _resolve(self) -> tuple[Point, Point]:
        p1 = self.p1() if callable(self.p1) else self.p1
        p2 = self.p2() if callable(self.p2) else self.p2
        return p1, p2

    def _trace(self) -> Path:
        return cast(Path, self._build())

    def _build(self) -> Shape:
        shape = Path(**self.kwargs)
        start, end = self._resolve()

        shape.jump_to(start.x, start.y)

        if abs(self.curvature) < 1e-4:
            shape.line_to(end.x, end.y)
        else:
            dx = end.x - start.x
            dy = end.y - start.y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist == 0:
                return shape

            s = self.curvature * (dist / 2.0)
            r = (s**2 + (dist / 2.0) ** 2) / (2 * abs(s))
            large_arc = 0
            sweep = 1 if self.curvature > 0 else 0
            shape.arc(r, r, 0, large_arc, sweep, end.x, end.y)

        return shape


class Arrow(Line):
    def __init__(
        self,
        p1: Point | Callable[[], Point],
        p2: Point | Callable[[], Point],
        curvature: float = 0.0,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
        width: float = 1.0,
        marker_start: str | None = None,
        marker_end: str | None = "arrow",
    ) -> None:
        super().__init__(
            p1,
            p2,
            curvature,
            fill,
            stroke,
            width,
            marker_start=marker_start,
            marker_end=marker_end,
        )


class Container(Group, Visual):
    """
    A Group that renders a background box around its children.
    Automatically calculates its bounds based on children + padding.
    """

    def __init__(
        self,
        shapes: list[Shape] | None = None,
        padding: float = 0.0,
        corner_radius: float = 0.0,
        fill: Color = Colors.Transparent,
        stroke: Color = Colors.Black,
        width: float = 1.0,
    ) -> None:
        Group.__init__(self, shapes)
        Visual.__init__(self, fill=fill, stroke=stroke, width=width)

        self.padding = padding
        self.corner_radius = corner_radius

    def local(self) -> Bounds:
        # The bounds of the container includes the padding around the children
        b = super().local()
        return b.padded(self.padding)

    def _render(self) -> str:
        # 1. Render the background Rect
        if not self.shapes:
            return ""

        # Use Group.local() to get children bounds without padding
        content_b = Group.local(self)
        bg_b = content_b.padded(self.padding)

        rx = self.corner_radius
        ry = self.corner_radius

        bg_svg = (
            f'<rect x="{bg_b.x}" y="{bg_b.y}" '
            f'width="{bg_b.width}" height="{bg_b.height}" '
            f'rx="{rx}" ry="{ry}" '
            f'fill="{self.fill}" stroke="{self.stroke}" stroke-width="{self.width}" />'
        )

        # 2. Render children on top
        children_svg = super()._render()

        return f"{bg_svg}\n{children_svg}"

    def trace(self) -> Path:
        # For the Sketch renderer, the Container traces as its border rectangle.
        b = self.local()

        # Helper to create a Rect path around these bounds
        hw, hh = b.width / 2, b.height / 2
        # Center of bounds relative to local (which is usually aligned to children)
        cx, cy = b.center.x, b.center.y

        return (
            Path(fill=self.fill, stroke=self.stroke, width=self.width)
            .jump_to(cx - hw, cy - hh)
            .line_to(cx + hw, cy - hh)
            .line_to(cx + hw, cy + hh)
            .line_to(cx - hw, cy + hh)
            .close()
        )
