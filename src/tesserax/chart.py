from __future__ import annotations
from abc import ABC, abstractmethod
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


class Mark(ABC):
    """
    Base class for geometric representations of data.
    Subclasses define how a single data row maps to a Shape.
    """

    def __init__(self, **params: Any) -> None:
        self.params = params

    @abstractmethod
    def build(
        self,
        row: dict[str, Any],
        encoding: dict[str, str],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ) -> Shape | None:
        """Produces a Shape for a single data row."""
        pass


class BarMark(Mark):
    """Represents data as rectangular bars."""

    def build(
        self,
        row: dict[str, Any],
        encoding: dict[str, str],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ) -> Shape | None:
        x_field = encoding.get("x")
        y_field = encoding.get("y")
        color_field = encoding.get("color")

        if not x_field or not y_field:
            return None

        x_scale = scales.get("x")
        y_scale = scales.get("y")
        color_scale = scales.get("color")

        if not isinstance(x_scale, BandScale) or not isinstance(y_scale, Scale):
            return None

        xv = row[x_field]
        yv = row[y_field]

        bw = x_scale.bandwidth
        bh = y_scale.map(yv)
        bx = x_scale.map(xv)
        by = 0

        color = Colors.SteelBlue
        if color_field and color_scale:
            color = color_scale.map(row[color_field])

        rect = Rect(bw, bh, fill=color, stroke=Colors.White, width=0.5)
        # Flip Y for SVG (Chart Space Y=0 is bottom)
        svg_y = chart_height - (by + bh / 2)
        rect.move_to(Point(bx + bw / 2, svg_y))
        return rect


class PointMark(Mark):
    """Represents data as circles/points."""

    def build(
        self,
        row: dict[str, Any],
        encoding: dict[str, str],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ) -> Shape | None:
        x_field = encoding.get("x")
        y_field = encoding.get("y")
        color_field = encoding.get("color")

        if not x_field or not y_field:
            return None

        x_scale = scales.get("x")
        y_scale = scales.get("y")
        color_scale = scales.get("color")

        if not isinstance(x_scale, Scale) or not isinstance(y_scale, Scale):
            return None

        xv = row[x_field]
        yv = row[y_field]

        px = (
            x_scale.center(xv)
            if isinstance(x_scale, BandScale)
            else x_scale.map(xv)
        )
        py = y_scale.map(yv)
        size = self.params.get("size", 5.0)

        color = Colors.SteelBlue
        if color_field and color_scale:
            color = color_scale.map(row[color_field])

        dot = Circle(size, fill=color, stroke=Colors.White, width=0.5)
        # Flip Y for SVG
        dot.move_to(Point(px, chart_height - py))
        return dot


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
        self._mark: Mark = BarMark()
        self._encoding: dict[str, str] = {}

    def mark_bar(self, padding: float = 0.1, **kwargs) -> Self:
        self._mark = BarMark(padding=padding, **kwargs)
        return self

    def mark_point(self, size: float = 5.0, **kwargs) -> Self:
        self._mark = PointMark(size=size, **kwargs)
        return self

    def encode(self, **channels: str) -> Self:
        """Map visual channels (x, y, color) to data fields."""
        self._encoding.update(channels)
        return self

    def _get_domain(self, field: str) -> list[Any]:
        return [d[field] for d in self.data]

    def _is_quantitative(self, field: str) -> bool:
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

        scales: dict[str, Scale | ColorScale] = {}

        # X Scale
        x_domain = self._get_domain(x_field)
        # Bars almost always use BandScale for X
        if self._is_quantitative(x_field) and not isinstance(self._mark, BarMark):
            scales["x"] = LinearScale((min(x_domain), max(x_domain)), (0, self.w))
        else:
            scales["x"] = BandScale(
                list(dict.fromkeys(x_domain)),
                (0, self.w),
                padding=self._mark.params.get("padding", 0.1),
            )

        # Y Scale
        y_domain = self._get_domain(y_field)
        if self._is_quantitative(y_field):
            scales["y"] = LinearScale((0, max(y_domain)), (0, self.h))
        else:
            scales["y"] = BandScale(list(dict.fromkeys(y_domain)), (0, self.h))

        # Color Scale
        if color_field:
            scales["color"] = ColorScale(
                list(dict.fromkeys(self._get_domain(color_field)))
            )

        # 2. Generate Marks
        for row in self.data:
            shape = self._mark.build(row, self._encoding, scales, self.h)

            if shape:
                chart_group.add(shape)

        return chart_group
