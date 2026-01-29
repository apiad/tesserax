from __future__ import annotations
import copy
from dataclasses import dataclass, replace
from abc import ABC, abstractmethod
from typing import Literal
import typing


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

    def padded(self, amount: float) -> Bounds:
        """Returns a new Bounds expanded by the given padding amount on all sides."""
        return Bounds(
            x=self.x - amount,
            y=self.y - amount,
            width=self.width + 2 * amount,
            height=self.height + 2 * amount,
        )

    @property
    def center(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height / 2)

    def anchor(self, name: Anchor) -> Point:
        """Returns a Point based on a string name for layout flexibility."""
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
        """Computes the minimal bounding box that contains all given bounds."""
        if not bounds:
            return Bounds(0, 0, 0, 0)

        x_min = min(b.x for b in bounds)
        y_min = min(b.y for b in bounds)
        x_max = max(b.x + b.width for b in bounds)
        y_max = max(b.y + b.height for b in bounds)

        return Bounds(x_min, y_min, x_max - x_min, y_max - y_min)


if typing.TYPE_CHECKING:
    from .transform import Transform
    from .base import Group


class Shape(ABC):
    """Base class for all renderable SVG components."""

    @abstractmethod
    def bounds(self) -> Bounds:
        """Calculates the bounding box of the shape in the coordinate space."""
        pass

    @abstractmethod
    def render(self) -> str:
        """Returns the SVG XML string representation of the shape."""
        pass

    def translated(self, dx: float, dy: float) -> Transform:
        return self.transformed(dx=dx, dy=dy)

    def rotated(self, theta: float) -> Transform:
        return self.transformed(r=theta)

    def scaled(self, s: float) -> Transform:
        return self.transformed(s=s)

    def transformed(
        self, dx: float = 0, dy: float = 0, r: float = 0, s: float = 1
    ) -> Transform:
        return Transform(self, tx=dx, ty=dy, rotation=r, scale=s)

    def __add__(self, other: Shape) -> Group:
        """Enables the 'shape + shape' syntax to create groups."""
        return Group().add(self, other)

    def clone(self) -> typing.Self:
        """
        Returns a deep copy of the shape.
        Essential for creating variations of a base structure without side effects.
        """
        return copy.deepcopy(self)
