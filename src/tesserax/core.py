from __future__ import annotations
import copy
from dataclasses import dataclass
from abc import ABC, abstractmethod
import math
from typing import Literal, Self, TYPE_CHECKING

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


@dataclass(frozen=True)
class Point:
    x: float
    y: float

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


@dataclass
class Transform:
    tx: float = 0.0
    ty: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0

    def map(self, p: Point) -> Point:
        return p.apply(self.tx, self.ty, self.rotation, self.scale)

    def reset(self) -> None:
        self.tx = 0.0
        self.ty = 0.0
        self.rotation = 0.0
        self.scale = 1.0


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
    def __init__(self) -> None:
        from .base import Group

        self.transform = Transform()
        self.parent: Group | None = None

        if (gp := Group.current()) is not None:
            gp.append(self)

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
        """Wraps the inner content in a transform group."""
        t = self.transform
        ts = f' transform="translate({t.tx} {t.ty}) rotate({t.rotation}) scale({t.scale})"'
        return f"<g{ts}>\n{self._render()}\n</g>"

    def resolve(self, p: Point) -> Point:
        world_p = self.transform.map(p)
        if self.parent:
            return self.parent.resolve(world_p)
        return world_p

    def anchor(self, name: Anchor) -> Point:
        return self.resolve(self.local().anchor(name))

    def translated(self, dx: float, dy: float) -> Self:
        self.transform.tx += dx
        self.transform.ty += dy
        return self

    def rotated(self, r: float) -> Self:
        self.transform.rotation += r
        return self

    def scaled(self, s: float) -> Self:
        self.transform.scale += s
        return self

    def clone(self) -> Self:
        return copy.deepcopy(self)

    def __add__(self, other: Shape) -> Group:
        # Import internally to avoid circular import with base.py
        from .base import Group

        return Group().add(self, other)
