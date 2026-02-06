from __future__ import annotations
import copy
from dataclasses import dataclass
from abc import ABC, abstractmethod
import math
from typing import Literal, Protocol, Self, TYPE_CHECKING
from .color import Color, Colors

if TYPE_CHECKING:
    from .base import Group

type Anchor = Literal[
    "top",
    "bottom",
    "left",
    "right",
    "center",
    "topleft",
    "topright",
    "bottomleft",
    "bottomright",
]


def deg(degrees: float) -> float:
    """Use this method to convert to radians."""
    return math.radians(degrees)


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    @classmethod
    def zero(cls) -> Point: return cls(0, 0)

    @classmethod
    def up(cls) -> Point: return cls(0, -1) # SVG Y is down

    @classmethod
    def down(cls) -> Point: return cls(0, 1)

    @classmethod
    def left(cls) -> Point: return cls(-1, 0)

    @classmethod
    def right(cls) -> Point: return cls(1, 0)

    @staticmethod
    def distance_to_segment(p: Point, start: Point, end: Point) -> float:
        # Area of triangle = 0.5 * base * height
        # Height = (2 * Area) / base
        # Area can be found via cross product
        dx = end.x - start.x
        dy = end.y - start.y

        if dx == 0 and dy == 0:
            return (p - start).magnitude()

        num = abs(dy * p.x - dx * p.y + end.x * start.y - end.y * start.x)
        den = math.sqrt(dy**2 + dx**2)
        return num / den

    def apply(self, tx=0.0, ty=0.0, r=0.0, s=1.0) -> Point:
        rad = math.radians(r)
        nx, ny = self.x * s, self.y * s
        rx = nx * math.cos(rad) - ny * math.sin(rad)
        ry = nx * math.sin(rad) + ny * math.cos(rad)
        return Point(rx + tx, ry + ty)

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self) -> Point:
        m = self.magnitude()

        if m == 0:
            return Point(0, 0)

        return Point(self.x / m, self.y / m)

    def __mul__(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Point:
        return Point(self.x / scalar, self.y / scalar)

    def dx(self, dx: float) -> Point:
        return self + Point(dx, 0)

    def dy(self, dy: float) -> Point:
        return self + Point(0, dy)

    def d(self, dx: float, dy: float) -> Point:
        return self + Point(dx, dy)

    def lerp(self, other: Point, t: float) -> Point:
        """Linear interpolation between this point and another."""
        return self + (other - self) * t


@dataclass
class Transform:
    """
    Represents an affine transformation decomposed into:
    Translation (tx, ty), Rotation (radians), and Scale (sx, sy).
    """

    tx: float = 0.0
    ty: float = 0.0
    rotation: float = 0.0
    sx: float = 1.0
    sy: float = 1.0

    # --- Factory & Lifecycle ---

    @classmethod
    def identity(cls) -> Self:
        return cls()

    def copy(self) -> Transform:
        return Transform(self.tx, self.ty, self.rotation, self.sx, self.sy)

    def reset(self) -> Self:
        self.tx = 0.0
        self.ty = 0.0
        self.rotation = 0.0
        self.sx = 1.0
        self.sy = 1.0
        return self

    # --- Animation Logic ---

    def lerp(self, target: "Transform", t: float) -> "Transform":
        """
        Linearly interpolates between this transform and a target.
        Returns a NEW Transform instance.
        """
        # Clamp t to [0, 1] to prevent overshooting
        t = max(0.0, min(1.0, t))

        return Transform(
            tx=self.tx + (target.tx - self.tx) * t,
            ty=self.ty + (target.ty - self.ty) * t,
            # Interpolating angle directly preserves rotational direction
            rotation=self.rotation + (target.rotation - self.rotation) * t,
            sx=self.sx + (target.sx - self.sx) * t,
            sy=self.sy + (target.sy - self.sy) * t,
        )

    # --- Math & Application ---

    def map(self, p: "Point") -> "Point":
        """
        Applies the transformation to a Point (Scale -> Rotate -> Translate).
        """
        # 1. Scale
        x = p.x * self.sx
        y = p.y * self.sy

        # 2. Rotate
        if self.rotation != 0:
            cos_theta = math.cos(self.rotation)
            sin_theta = math.sin(self.rotation)
            x_new = x * cos_theta - y * sin_theta
            y_new = x * sin_theta + y * cos_theta
            x, y = x_new, y_new

        # 3. Translate
        return p.__class__(x + self.tx, y + self.ty)

    # --- Fluent Mutators ---

    def translate(self, dx: float, dy: float) -> Self:
        self.tx += dx
        self.ty += dy
        return self

    def rotate(self, radians: float) -> Self:
        self.rotation += radians
        return self

    def scale(self, sx: float, sy: float | None = None) -> Self:
        if sy is None:
            sy = sx

        self.sx *= sx
        self.sy *= sy
        return self


@dataclass(frozen=True)
class Bounds:
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> Point:
        return Point(self.x, self.y + self.height / 2)

    @property
    def right(self) -> Point:
        return Point(self.x + self.width, self.y + self.height / 2)

    @property
    def top(self) -> Point:
        return Point(self.x + self.width / 2, self.y)

    @property
    def bottom(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height)

    @property
    def topleft(self) -> Point:
        return Point(self.x, self.y)

    @property
    def topright(self) -> Point:
        return Point(self.x + self.width, self.y)

    @property
    def bottomleft(self) -> Point:
        return Point(self.x, self.y + self.height)

    @property
    def bottomright(self) -> Point:
        return Point(self.x + self.width, self.y + self.height)

    @property
    def center(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height / 2)

    def padded(self, amount: float) -> Bounds:
        return Bounds(
            self.x - amount,
            self.y - amount,
            self.width + 2 * amount,
            self.height + 2 * amount,
        )

    def anchor(self, name: Anchor) -> Point:
        match name:
            case "top":
                return self.top
            case "bottom":
                return self.bottom
            case "left":
                return self.left
            case "right":
                return self.right
            case "center":
                return self.center
            case "topleft":
                return self.topleft
            case "topright":
                return self.topright
            case "bottomleft":
                return self.bottomleft
            case "bottomright":
                return self.bottomright
            case _:
                raise ValueError(f"Unknown anchor: {name}")

    @classmethod
    def union(cls, *bounds: Bounds) -> Bounds:
        if not bounds:
            return Bounds(0, 0, 0, 0)

        x_min = min(b.x for b in bounds)
        y_min = min(b.y for b in bounds)
        x_max = max(b.x + b.width for b in bounds)
        y_max = max(b.y + b.height for b in bounds)

        return Bounds(x_min, y_min, x_max - x_min, y_max - y_min)


class Shape(ABC):
    def __init__(
        self,
    ) -> None:
        from .base import Group
        from .animation import Animator

        self.transform = Transform.identity()
        self.parent: Group | None = None
        self.hidden: bool = False

        if (gp := Group.current()) is not None:
            gp.append(self)

        self._animator: Animator | None = None

    def detach(self) -> Self:
        if self.parent:
            self.parent.remove(self)

        return self

    def show(self) -> Self:
        self.hidden = False
        return self

    def hide(self) -> Self:
        self.hidden = True
        return self

    @property
    def animate(self):
        from .animation import Animator

        if self._animator is None:
            self._animator = Animator(self)

        return self._animator

    @abstractmethod
    def local(self) -> Bounds:
        pass

    def bounds(self) -> Bounds:
        base = self.local()

        corners = [base.topleft, base.topright, base.bottomleft, base.bottomright]
        transformed = [self.transform.map(p) for p in corners]
        xs = [p.x for p in transformed]
        ys = [p.y for p in transformed]

        return Bounds(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    @abstractmethod
    def _render(self) -> str:
        pass

    def render(self) -> str:
        """Generates the SVG expression for this shape, including transformation."""
        if self.hidden:
            return ""

        t = self.transform

        # Optimization: Return raw render if transform is identity
        # (This avoids nested <g> tags for shapes that haven't moved)
        if t.tx == 0 and t.ty == 0 and t.rotation == 0 and t.sx == 1 and t.sy == 1:
            return self._render()

        # Fix: SVG rotate expects degrees, but Transform stores radians
        deg = math.degrees(t.rotation)

        ts = f' transform="translate({t.tx} {t.ty}) rotate({deg}) scale({t.sx} {t.sy})"'
        return f"<g{ts}>\n{self._render()}\n</g>"

    def resolve(self, p: Point) -> Point:
        world_p = self.transform.map(p)
        if self.parent:
            return self.parent.resolve(world_p)
        return world_p

    def anchor(self, name: Anchor) -> Point:
        return self.resolve(self.local().anchor(name))

    def translated(self, dx: float, dy: float) -> Self:
        self.transform.translate(dx, dy)
        return self

    def rotated(self, r: float) -> Self:
        self.transform.rotate(r)
        return self

    def scaled(self, s: float) -> Self:
        self.transform.scale(s)
        return self

    def clone(self) -> Self:
        return copy.deepcopy(self)

    def __add__(self, other: Shape) -> Group:
        # Import internally to avoid circular import with base.py
        from .base import Group

        return Group().add(self, other)

    def align_to(
        self,
        other: Shape,
        anchor: Anchor,
        other_anchor: Anchor | None = None,
    ) -> Self:
        """
        Aligns this shape to another shape.

        Moves this shape so that its 'anchor' point coincides with
        'other_anchor' on the target shape.
        """
        target_anchor = other_anchor or anchor
        return self.move_to(other.anchor(target_anchor), anchor)

    def move_to(self, target: Point, anchor: Anchor = "center") -> Self:
        """
        Moves the shape so that its specified anchor is at the target Point.
        """
        p_self = self.anchor(anchor)
        diff = target - p_self

        self.transform.tx += diff.x
        self.transform.ty += diff.y

        return self


class Component(Shape):
    """
    A Shape that is composed of other Shapes.
    Subclasses must implement build() which returns the geometric representation.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self._primitive: Shape | None = None
        self._kwargs = kwargs

    @abstractmethod
    def _build(self) -> Shape:
        """
        Constructs the visual representation of this component.
        Returns a Shape (e.g., Group, Path, Rect).
        """
        pass

    def refresh(self) -> Self:
        """Invalidates the cache, forcing a rebuild on next use."""
        self._primitive = None
        return self

    @property
    def _shape(self) -> Shape:
        if self._primitive is None:
            self._primitive = self._build().detach()

        return self._primitive

    def local(self) -> Bounds:
        return self._shape.bounds()

    def _render(self) -> str:
        # Render the built primitive.
        # Note: The primitive's own transform is applied inside its .render()
        # The Component's transform is applied by the caller (Shape.render)
        return self._shape.render()


# Protocols for different types of shapes


class HasStyle(Protocol):
    fill: Color
    stroke: Color
    width: float


class HasTexT(Protocol):
    text: str


class HasPoints(Protocol):
    points: list[Point]
