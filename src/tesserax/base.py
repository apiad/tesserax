from __future__ import annotations
from typing import Self
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

    def __init__(
        self, float, size: float, stroke: str = "black", fill: str = "none"
    ) -> None:
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
    """A basic connection between two points."""

    def __init__(
        self, p1: Point, p2: Point, stroke: str = "black", width: float = 1.0
    ) -> None:
        super().__init__()
        self.p1, self.p2 = p1, p2
        self.stroke, self.width = stroke, width

    def local(self) -> Bounds:
        x = min(self.p1.x, self.p2.x)
        y = min(self.p1.y, self.p2.y)
        return Bounds(x, y, abs(self.p1.x - self.p2.x), abs(self.p1.y - self.p2.y))

    def _render(self) -> str:
        return f'<line x1="{self.p1.x}" y1="{self.p1.y}" x2="{self.p2.x}" y2="{self.p2.y}" stroke="{self.stroke}" stroke-width="{self.width}" />'


class Arrow(Line):
    """A line with an arrowhead, using the 'arrowhead' marker defined in Canvas."""

    def _render(self) -> str:
        return (
            f'<line x1="{self.p1.x}" y1="{self.p1.y}" x2="{self.p2.x}" y2="{self.p2.y}" '
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

        return Bounds.union(*[s.local() for s in self.shapes])

    def _render(self) -> str:
        return "\n".join(s._render() for s in self.shapes)

    def __iadd__(self, other: Shape) -> Self:
        """Enables 'group += shape'."""
        self.shapes.append(other)
        return self

    def __enter__(self):
        self.stack.append([])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.add(*self.stack.pop())
