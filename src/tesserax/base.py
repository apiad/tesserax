from __future__ import annotations
from typing import Self
from .core import Point, Shape, Bounds


class Rect(Shape):
    """A rectangular shape, the foundation for arrays and memory blocks."""

    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        stroke: str = "black",
        fill: str = "none",
    ) -> None:
        self.x, self.y, self.w, self.h = x, y, w, h
        self.stroke, self.fill = stroke, fill

    def bounds(self) -> Bounds:
        return Bounds(self.x, self.y, self.w, self.h)

    def render(self) -> str:
        return f'<rect x="{self.x}" y="{self.y}" width="{self.w}" height="{self.h}" stroke="{self.stroke}" fill="{self.fill}" />'


class Square(Rect):
    """A specialized Rect where width equals height."""

    def __init__(
        self, x: float, y: float, size: float, stroke: str = "black", fill: str = "none"
    ) -> None:
        super().__init__(x, y, size, size, stroke, fill)


class Circle(Shape):
    """A circle, ideal for nodes in trees or states in automata."""

    def __init__(
        self, cx: float, cy: float, r: float, stroke: str = "black", fill: str = "none"
    ) -> None:
        self.cx, self.cy, self.r = cx, cy, r
        self.stroke, self.fill = stroke, fill

    def bounds(self) -> Bounds:
        return Bounds(self.cx - self.r, self.cy - self.r, self.r * 2, self.r * 2)

    def render(self) -> str:
        return f'<circle cx="{self.cx}" cy="{self.cy}" r="{self.r}" stroke="{self.stroke}" fill="{self.fill}" />'


class Ellipse(Shape):
    """An ellipse for when text labels are wider than they are tall."""

    def __init__(
        self,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        stroke: str = "black",
        fill: str = "none",
    ) -> None:
        self.cx, self.cy, self.rx, self.ry = cx, cy, rx, ry
        self.stroke, self.fill = stroke, fill

    def bounds(self) -> Bounds:
        return Bounds(self.cx - self.rx, self.cy - self.ry, self.rx * 2, self.ry * 2)

    def render(self) -> str:
        return f'<ellipse cx="{self.cx}" cy="{self.cy}" rx="{self.rx}" ry="{self.ry}" stroke="{self.stroke}" fill="{self.fill}" />'


class Line(Shape):
    """A basic connection between two points."""

    def __init__(
        self, p1: Point, p2: Point, stroke: str = "black", width: float = 1.0
    ) -> None:
        self.p1, self.p2 = p1, p2
        self.stroke, self.width = stroke, width

    def bounds(self) -> Bounds:
        x = min(self.p1.x, self.p2.x)
        y = min(self.p1.y, self.p2.y)
        return Bounds(x, y, abs(self.p1.x - self.p2.x), abs(self.p1.y - self.p2.y))

    def render(self) -> str:
        return f'<line x1="{self.p1.x}" y1="{self.p1.y}" x2="{self.p2.x}" y2="{self.p2.y}" stroke="{self.stroke}" stroke-width="{self.width}" />'


class Arrow(Line):
    """A line with an arrowhead, using the 'arrowhead' marker defined in Canvas."""

    def render(self) -> str:
        return (
            f'<line x1="{self.p1.x}" y1="{self.p1.y}" x2="{self.p2.x}" y2="{self.p2.y}" '
            f'stroke="{self.stroke}" stroke-width="{self.width}" marker-end="url(#arrowhead)" />'
        )


class Group(Shape):
    """A collection of shapes that behaves as a single unit."""

    def __init__(self, shapes: list[Shape] | None = None) -> None:
        self.shapes: list[Shape] = shapes or []

    def add(self, *shapes: Shape) -> Group:
        """Adds a shape and returns self for chaining."""
        for shape in shapes:
            self.shapes.append(shape)

        return self

    def bounds(self) -> Bounds:
        """Computes the union of all child bounds."""
        if not self.shapes:
            return Bounds(0, 0, 0, 0)

        return Bounds.union(*[s.bounds() for s in self.shapes])

    def render(self) -> str:
        """Wraps children in a group tag."""
        inner_svg = "\n  ".join(s.render() for s in self.shapes)
        return f'<g class="tesserax-group">\n  {inner_svg}\n</g>'

    def __iadd__(self, other: Shape) -> Self:
        """Enables 'group += shape'."""
        self.shapes.append(other)
        return self
