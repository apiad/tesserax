from __future__ import annotations
from abc import ABC, abstractmethod
import math
from typing import Any, Literal, Self, Sequence
from .core import Component, Shape, Point
from .base import Group, Rect, Circle, Visual, Line, Text
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

    def ticks(self, count: int = 5) -> list[tuple[float, str]]:
        """Generates a list of (value, label) tuples for ticks."""
        d0, d1 = self.domain
        step = (d1 - d0) / (count - 1) if count > 1 else 0
        return [
            (
                d0 + i * step,
                f"{d0 + i * step:.1f}".rstrip("0").rstrip("."),
            )
            for i in range(count)
        ]


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

    def ticks(self) -> list[tuple[Any, str]]:
        """Returns all categories as ticks."""
        return [(v, str(v)) for v in self.domain]


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
        encoding: dict[str, str | Channel],
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
        encoding: dict[str, str | Channel],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ) -> Shape | None:
        x_field = encoding.get("x")
        if isinstance(x_field, Channel):
            x_field = x_field.field
        y_field = encoding.get("y")
        if isinstance(y_field, Channel):
            y_field = y_field.field
        color_field = encoding.get("color")
        if isinstance(color_field, Channel):
            color_field = color_field.field

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
        encoding: dict[str, str | Channel],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ) -> Shape | None:
        x_field = encoding.get("x")
        if isinstance(x_field, Channel):
            x_field = x_field.field
        y_field = encoding.get("y")
        if isinstance(y_field, Channel):
            y_field = y_field.field
        color_field = encoding.get("color")
        if isinstance(color_field, Channel):
            color_field = color_field.field

        if not x_field or not y_field:
            return None

        x_scale = scales.get("x")
        y_scale = scales.get("y")
        color_scale = scales.get("color")

        if not isinstance(x_scale, Scale) or not isinstance(y_scale, Scale):
            return None

        xv = row[x_field]
        yv = row[y_field]

        px = x_scale.center(xv) if isinstance(x_scale, BandScale) else x_scale.map(xv)
        py = y_scale.map(yv)
        size = self.params.get("size", 5.0)

        color = Colors.SteelBlue
        if color_field and color_scale:
            color = color_scale.map(row[color_field])

        dot = Circle(size, fill=color, stroke=Colors.White, width=0.5)
        # Flip Y for SVG
        dot.move_to(Point(px, chart_height - py))
        return dot


class Axis:
    """Configuration for a chart axis."""

    def __init__(
        self,
        title: str | None = None,
        ticks: int | None = None,
        grid: bool = False,
        labels: bool = True,
    ) -> None:
        self.title = title
        self.tick_count = ticks
        self.grid = grid
        self.labels = labels


class Channel:
    """Base class for an encoding channel (x, y, etc.)."""

    def __init__(self, field: str, axis: Axis | None = None) -> None:
        self.field = field
        self.axis = axis


class X(Channel):
    """X-axis encoding channel."""

    pass


class Y(Channel):
    """Y-axis encoding channel."""

    pass


class _AxisComponent(Component):
    """Geometric representation of an axis."""

    def __init__(
        self,
        type: Literal["x", "y"],
        scale: Scale,
        config: Axis,
        length: float,
        cross_length: float,
    ) -> None:
        super().__init__()
        self.type = type
        self.scale = scale
        self.config = config
        self.length = length
        self.cross_length = cross_length

    def _build(self) -> Shape:
        group = Group()
        is_x = self.type == "x"

        # 1. Axis Line
        if is_x:
            line = Line(Point(0, 0), Point(self.length, 0), stroke=Colors.Black)
        else:
            line = Line(Point(0, 0), Point(0, -self.length), stroke=Colors.Black)
        group.add(line)

        # 2. Ticks and Labels
        tick_list = (
            self.scale.ticks(self.config.tick_count or 5)
            if isinstance(self.scale, LinearScale)
            else self.scale.ticks()
        )

        for val, label in tick_list:
            pos = (
                self.scale.center(val)
                if isinstance(self.scale, BandScale)
                else self.scale.map(val)
            )

            if is_x:
                # Tick
                group.add(Line(Point(pos, 0), Point(pos, 5), stroke=Colors.Black))
                # Label
                if self.config.labels:
                    group.add(Text(label, size=10).translated(pos, 15))
                # Grid
                if self.config.grid:
                    group.add(
                        Line(
                            Point(pos, 0),
                            Point(pos, -self.cross_length),
                            stroke=Colors.LightGray,
                            width=0.5,
                        )
                    )
            else:
                # Tick
                group.add(Line(Point(0, -pos), Point(-5, -pos), stroke=Colors.Black))
                # Label
                if self.config.labels:
                    group.add(Text(label, size=10, anchor="end").translated(-10, -pos))
                # Grid
                if self.config.grid:
                    group.add(
                        Line(
                            Point(0, -pos),
                            Point(self.cross_length, -pos),
                            stroke=Colors.LightGray,
                            width=0.5,
                        )
                    )

        # 3. Title
        if self.config.title:
            if is_x:
                group.add(
                    Text(self.config.title, size=12).translated(self.length / 2, 35)
                )
            else:
                group.add(
                    Text(self.config.title, size=12)
                    .rotated(math.radians(-90))
                    .translated(-40, -self.length / 2)
                )

        return group


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
        self._encoding: dict[str, str | Channel] = {}
        self._axes: dict[str, Axis] = {}

    def bar(self, padding: float = 0.1, **kwargs) -> Self:
        return self.mark(BarMark(padding=padding, **kwargs))

    def mark_bar(self, padding: float = 0.1, **kwargs) -> Self:
        """Alias for .bar()"""
        return self.bar(padding=padding, **kwargs)

    def point(self, size: float = 5.0, **kwargs) -> Self:
        return self.mark(PointMark(size=size, **kwargs))

    def mark_point(self, size: float = 5.0, **kwargs) -> Self:
        """Alias for .point()"""
        return self.point(size=size, **kwargs)

    def mark(self, mark: Mark) -> Self:
        """Set a custom mark implementation."""
        self._mark = mark
        return self

    def encode(self, **channels: str | Channel) -> Self:
        """Map visual channels (x, y, color) to data fields."""
        for name, value in channels.items():
            self._encoding[name] = value
            if isinstance(value, Channel) and value.axis:
                self._axes[name] = value.axis
        return self

    def axis(
        self,
        channel: Literal["x", "y"],
        title: str | None = None,
        ticks: int | None = None,
        grid: bool = False,
        labels: bool = True,
    ) -> Self:
        """Shorthand for configuring an axis."""
        self._axes[channel] = Axis(title=title, ticks=ticks, grid=grid, labels=labels)
        return self

    def _get_field(self, channel: str) -> str | None:
        val = self._encoding.get(channel)
        if isinstance(val, Channel):
            return val.field
        return val

    def _get_domain(self, field: str) -> list[Any]:
        return [d[field] for d in self.data]

    def _is_quantitative(self, channel: str) -> bool:
        if not self.data:
            return False
        f = self._get_field(channel)
        if not f:
            return False
        val = self.data[0].get(f)
        return isinstance(val, (int, float))

    def _build(self) -> Shape:
        if not self.data or not self._encoding:
            return Group()

        # 1. Determine Margins
        margin_left = 60 if "y" in self._axes else 10
        margin_bottom = 50 if "x" in self._axes else 10
        margin_right = 20
        margin_top = 20

        plot_w = self.w - margin_left - margin_right
        plot_h = self.h - margin_bottom - margin_top

        # 2. Setup Scales
        x_field = self._get_field("x")
        y_field = self._get_field("y")
        color_field = self._get_field("color")

        if not x_field or not y_field:
            return Group()

        scales: dict[str, Scale | ColorScale] = {}

        # X Scale
        x_domain = self._get_domain(x_field)
        if self._is_quantitative("x") and not isinstance(self._mark, BarMark):
            scales["x"] = LinearScale((min(x_domain), max(x_domain)), (0, plot_w))
        else:
            scales["x"] = BandScale(
                list(dict.fromkeys(x_domain)),
                (0, plot_w),
                padding=self._mark.params.get("padding", 0.1),
            )

        # Y Scale
        y_domain = self._get_domain(y_field)
        if self._is_quantitative("y"):
            scales["y"] = LinearScale((0, max(y_domain)), (0, plot_h))
        else:
            scales["y"] = BandScale(list(dict.fromkeys(y_domain)), (0, plot_h))

        # Color Scale
        if color_field:
            scales["color"] = ColorScale(
                list(dict.fromkeys(self._get_domain(color_field)))
            )

        # 3. Generate Content
        main_group = Group()
        plot_group = Group()

        for row in self.data:
            shape = self._mark.build(row, self._encoding, scales, plot_h)
            if shape:
                plot_group.add(shape)

        # Position plot group
        plot_group.translated(margin_left, margin_top)
        main_group.add(plot_group)

        # 4. Generate Axes
        if "x" in self._axes:
            x_axis = _AxisComponent(
                "x", scales["x"], self._axes["x"], plot_w, plot_h
            ).translated(margin_left, margin_top + plot_h)
            main_group.add(x_axis)

        if "y" in self._axes:
            y_axis = _AxisComponent(
                "y", scales["y"], self._axes["y"], plot_h, plot_w
            ).translated(margin_left, margin_top + plot_h)
            main_group.add(y_axis)

        return main_group
