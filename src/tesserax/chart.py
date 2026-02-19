from __future__ import annotations
from typing import Any, Literal, Self, Sequence
from .core import Component, Shape, Point
from .base import Group, Rect, Circle, Visual
from .color import Color, Colors


class Scale:
    """Base class for mapping data values to visual ranges."""

    def __init__(self, domain: Sequence[Any], range: tuple[float, float]) -> None:
        self.domain = domain
        self.range = range

    def map(self, value: Any) -> float:
        raise NotImplementedError


class LinearScale(Scale):
    """Maps quantitative values to a continuous range."""

    def __init__(self, domain: tuple[float, float], range: tuple[float, float]) -> None:
        super().__init__(domain, range)

    def map(self, value: float) -> float:
        d0, d1 = self.domain
        r0, r1 = self.range
        if d1 == d0:
            return r0
        # Normalize t to [0, 1]
        t = (value - d0) / (d1 - d0)
        return r0 + t * (r1 - r0)


class BandScale(Scale):
    """Maps categorical values to discrete steps with padding."""

    def __init__(
        self,
        domain: Sequence[Any],
        range: tuple[float, float],
        padding: float = 0.1,
    ) -> None:
        super().__init__(domain, range)
        self.padding = padding
        self._calculate()

    def _calculate(self) -> None:
        n = len(self.domain)
        r0, r1 = self.range
        total_width = abs(r1 - r0)

        # total_width = n * step - padding * step
        # (Where step is the distance from start of one band to start of next)
        self.step = total_width / max(1, n - self.padding)
        self.bandwidth = self.step * (1 - self.padding)

    def map(self, value: Any) -> float:
        try:
            idx = self.domain.index(value)
        except ValueError:
            return self.range[0]
        return self.range[0] + idx * self.step

    def center(self, value: Any) -> float:
        """Returns the center of the band for a given value."""
        return self.map(value) + self.bandwidth / 2


class ColorScale:
    """Maps values to a color palette."""

    PALETTE = [
        Colors.Navy,
        Colors.DarkRed,
        Colors.DarkGreen,
        Colors.Orange,
        Colors.Purple,
        Colors.Teal,
    ]

    def __init__(self, domain: Sequence[Any]) -> None:
        self.domain = domain

    def map(self, value: Any) -> Color:
        try:
            idx = self.domain.index(value)
        except ValueError:
            return Colors.Gray
        return self.PALETTE[idx % len(self.PALETTE)]


class Chart(Component):
    """
    A grammar-of-graphics component for building visualizations.
    Uses an Altair-lite API: .mark_bar().encode(x='col1', y='col2')
    """

    def __init__(
        self, data: list[dict[str, Any]], width: float = 400, height: float = 300
    ) -> None:
        super().__init__()
        self.data = data
        self.w = width
        self.h = height
        self._mark: Literal["bar", "point"] = "bar"
        self._encoding: dict[str, str] = {}
        self._mark_params: dict[str, Any] = {}

    def mark_bar(self, padding: float = 0.1, **kwargs) -> Self:
        self._mark = "bar"
        self._mark_params = {"padding": padding, **kwargs}
        return self

    def mark_point(self, size: float = 5.0, **kwargs) -> Self:
        self._mark = "point"
        self._mark_params = {"size": size, **kwargs}
        return self

    def encode(self, **channels: str) -> Self:
        """Map visual channels (x, y, color) to data fields."""
        self._encoding.update(channels)
        return self

    def _get_domain(self, field: str) -> list[Any]:
        return [d[field] for d in self.data]

    def _is_quantitative(self, field: str) -> bool:
        # Simple heuristic: if the first value is a number, it's quantitative
        if not self.data:
            return False
        val = self.data[0].get(field)
        return isinstance(val, (int, float))

    def _build(self) -> Shape:
        if not self.data or not self._encoding:
            return Group()

        chart_group = Group()

        # 1. Setup Scales
        x_field = self._encoding.get("x")
        y_field = self._encoding.get("y")
        color_field = self._encoding.get("color")

        if not x_field or not y_field:
            return chart_group

        # X Scale
        x_domain = self._get_domain(x_field)
        if self._is_quantitative(x_field) and self._mark != "bar":
            x_scale = LinearScale((min(x_domain), max(x_domain)), (0, self.w))
        else:
            # Bars almost always use BandScale for X
            x_scale = BandScale(
                list(dict.fromkeys(x_domain)),
                (0, self.w),
                padding=self._mark_params.get("padding", 0.1),
            )

        # Y Scale
        y_domain = self._get_domain(y_field)
        if self._is_quantitative(y_field):
            # For charts, we usually want the Y axis to start at 0
            # unless the user explicitly requests otherwise.
            y_scale = LinearScale((0, max(y_domain)), (0, self.h))
        else:
            y_scale = BandScale(list(dict.fromkeys(y_domain)), (0, self.h))

        # Color Scale
        color_scale = None
        if color_field:
            color_scale = ColorScale(list(dict.fromkeys(self._get_domain(color_field))))

        # 2. Generate Marks
        for row in self.data:
            xv = row[x_field]
            yv = row[y_field]
            color = Colors.SteelBlue  # Default
            if color_scale:
                color = color_scale.map(row[color_field])

            if self._mark == "bar":
                bw = x_scale.bandwidth
                bh = y_scale.map(yv)
                # Bottom-left of the bar in Chart Space
                bx = x_scale.map(xv)
                by = 0

                # Convert to Tesserax Shape (Rect is centered at 0,0)
                # We want the bottom of the rect at 'by', so we shift it up by bh/2
                rect = Rect(bw, bh, fill=color, stroke=Colors.White, width=0.5)
                # Placement: bx + bw/2 (center x), by + bh/2 (center y)
                # BUT: we need to flip Y for SVG.
                # Chart Space Y=0 is bottom (SVG Y=height)
                # Chart Space Y=bh is top (SVG Y=height-bh)
                svg_y = self.h - (by + bh / 2)
                rect.move_to(Point(bx + bw / 2, svg_y))
                chart_group.add(rect)

            elif self._mark == "point":
                px = (
                    x_scale.center(xv)
                    if isinstance(x_scale, BandScale)
                    else x_scale.map(xv)
                )
                py = y_scale.map(yv)
                size = self._mark_params.get("size", 5.0)

                dot = Circle(size, fill=color, stroke=Colors.White, width=0.5)
                # Flip Y for SVG
                dot.move_to(Point(px, self.h - py))
                chart_group.add(dot)

        return chart_group
