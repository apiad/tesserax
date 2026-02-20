from __future__ import annotations
from abc import ABC, abstractmethod
import math
from typing import Any, Literal, Self, Sequence, cast, TYPE_CHECKING
from .core import Component, StatefulComponent, Shape, Point
from .base import Group, Rect, Circle, Visual, Line, Text
from .color import Color, Colors

if TYPE_CHECKING:
    from .animation import Animation, Parallel


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
    ) -> Shape:
        """Produces a Shape for a single data row."""
        pass

    @abstractmethod
    def enter(
        self,
        row: dict[str, Any],
        encoding: dict[str, str | Channel],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ) -> tuple[Shape, Animation]:
        """Creates a new shape and its entrance animation."""
        pass

    @abstractmethod
    def update(
        self,
        shape: Shape,
        row: dict[str, Any],
        encoding: dict[str, str | Channel],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ) -> Animation:
        """Updates an existing shape to match new data."""
        pass

    @abstractmethod
    def exit(self, shape: Shape) -> Animation:
        """Creates an animation for a shape that is being removed."""
        pass


class BarMark(Mark):
    """Represents data as rectangular bars."""

    def _get_params(
        self,
        row: dict[str, Any],
        encoding: dict[str, str | Channel],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ):
        x_field = encoding.get("x")
        if isinstance(x_field, Channel):
            x_field = x_field.field
        y_field = encoding.get("y")
        if isinstance(y_field, Channel):
            y_field = y_field.field
        color_field = encoding.get("color")
        if isinstance(color_field, Channel):
            color_field = color_field.field

        x_scale = scales.get("x")
        y_scale = scales.get("y")
        color_scale = scales.get("color")

        xv = row[x_field]
        yv = row[y_field]

        bw = x_scale.bandwidth
        bh = y_scale.map(yv)
        bx = x_scale.map(xv)
        by = 0

        color = Colors.SteelBlue
        if color_field and color_scale:
            color = color_scale.map(row[color_field])

        svg_y = chart_height - (by + bh / 2)
        return bw, bh, bx + bw / 2, svg_y, color

    def build(
        self,
        row: dict[str, Any],
        encoding: dict[str, str | Channel],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ) -> Shape:
        bw, bh, cx, cy, color = self._get_params(row, encoding, scales, chart_height)
        rect = Rect(bw, bh, fill=color, stroke=Colors.White, width=0.5)
        rect.move_to(Point(cx, cy))
        return rect

    def enter(self, row, encoding, scales, chart_height) -> tuple[Shape, Animation]:
        bw, bh, cx, cy, color = self._get_params(row, encoding, scales, chart_height)
        # Start at height 0, positioned at the baseline
        baseline = cy + bh / 2
        rect = Rect(bw, 0.01, fill=color, stroke=Colors.White, width=0.5)
        rect.move_to(Point(cx, baseline))
        rect.opacity = 0.0

        # Animate to full height and correct center SIMULTANEOUSLY with opacity
        anim = (
            rect.animate.h(bh)
            + rect.animate.translate(dy=cy - baseline)
            + rect.animate.opacity(1.0)
        )
        return rect, anim

    def update(self, shape: Shape, row, encoding, scales, chart_height) -> Animation:
        bw, bh, cx, cy, color = self._get_params(row, encoding, scales, chart_height)
        rect = cast(Rect, shape)
        return (
            rect.animate.h(bh)
            + rect.animate.fill(color)
            + rect.animate.translate(cx - rect.transform.tx, cy - rect.transform.ty)
            + rect.animate.opacity(1.0)
        )

    def exit(self, shape: Shape) -> Animation:
        rect = cast(Rect, shape)
        baseline = rect.transform.ty + rect.h / 2

        def detach_rect(_):
            if rect.parent:
                rect.parent.remove(rect)

        return (
            (
                rect.animate.h(0.01)
                + rect.animate.translate(dy=baseline - rect.transform.ty)
            )
            + rect.animate.opacity(0.0)
        ).then(detach_rect)


class PointMark(Mark):
    """Represents data as circles/points."""

    def _get_params(
        self,
        row: dict[str, Any],
        encoding: dict[str, str | Channel],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ):
        x_field = encoding.get("x")
        if isinstance(x_field, Channel):
            x_field = x_field.field
        y_field = encoding.get("y")
        if isinstance(y_field, Channel):
            y_field = y_field.field
        color_field = encoding.get("color")
        if isinstance(color_field, Channel):
            color_field = color_field.field

        x_scale = scales.get("x")
        y_scale = scales.get("y")
        color_scale = scales.get("color")

        xv = row[x_field]
        yv = row[y_field]

        px = x_scale.center(xv) if isinstance(x_scale, BandScale) else x_scale.map(xv)
        py = y_scale.map(yv)
        size = self.params.get("size", 5.0)

        color = Colors.SteelBlue
        if color_field and color_scale:
            color = color_scale.map(row[color_field])

        return px, chart_height - py, size, color

    def build(
        self,
        row: dict[str, Any],
        encoding: dict[str, str | Channel],
        scales: dict[str, Scale | ColorScale],
        chart_height: float,
    ) -> Shape:
        px, py, r, color = self._get_params(row, encoding, scales, chart_height)
        dot = Circle(r, fill=color, stroke=Colors.White, width=0.5)
        dot.move_to(Point(px, py))
        return dot

    def enter(self, row, encoding, scales, chart_height) -> tuple[Shape, Animation]:
        px, py, r, color = self._get_params(row, encoding, scales, chart_height)
        dot = Circle(0.01, fill=color, stroke=Colors.White, width=0.5)
        dot.move_to(Point(px, py))
        dot.opacity = 0.0
        return dot, dot.animate.r(r) + dot.animate.opacity(1.0)

    def update(self, shape: Shape, row, encoding, scales, chart_height) -> Animation:
        px, py, r, color = self._get_params(row, encoding, scales, chart_height)
        dot = cast(Circle, shape)
        return (
            dot.animate.r(r)
            + dot.animate.fill(color)
            + dot.animate.translate(px - dot.transform.tx, py - dot.transform.ty)
            + dot.animate.opacity(1.0)
        )

    def exit(self, shape: Shape) -> Animation:
        dot = cast(Circle, shape)

        def detach_dot(_):
            if dot.parent:
                dot.parent.remove(dot)

        return (dot.animate.r(0.01) + dot.animate.opacity(0.0)).then(detach_dot)


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


class _AxisComponent(StatefulComponent):
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
        # Persistent state for ticks: value -> Group(Line, Text)
        self._tick_marks: dict[Any, Group] = {}

    def _build_tick(self, val: Any, label: str) -> Group:
        tick_group = Group()
        is_x = self.type == "x"

        pos = (
            self.scale.center(val)
            if isinstance(self.scale, BandScale)
            else self.scale.map(val)
        )

        if is_x:
            # Tick
            tick_group.add(Line(Point(pos, 0), Point(pos, 5), stroke=Colors.Black))
            # Label
            if self.config.labels:
                tick_group.add(Text(label, size=10).translated(pos, 15))
            # Grid
            if self.config.grid:
                tick_group.add(
                    Line(
                        Point(pos, 0),
                        Point(pos, -self.cross_length),
                        stroke=Colors.LightGray,
                        width=0.5,
                    )
                )
        else:
            # Tick
            tick_group.add(Line(Point(0, -pos), Point(-5, -pos), stroke=Colors.Black))
            # Label
            if self.config.labels:
                tick_group.add(Text(label, size=10, anchor="end").translated(-10, -pos))
            # Grid
            if self.config.grid:
                tick_group.add(
                    Line(
                        Point(0, -pos),
                        Point(self.cross_length, -pos),
                        stroke=Colors.LightGray,
                        width=0.5,
                    )
                )
        return tick_group

    def _build(self) -> Shape:
        main_group = Group()
        is_x = self.type == "x"

        # 1. Axis Line
        if is_x:
            line = Line(Point(0, 0), Point(self.length, 0), stroke=Colors.Black)
        else:
            line = Line(Point(0, 0), Point(0, -self.length), stroke=Colors.Black)
        main_group.add(line)

        # 2. Ticks and Labels
        tick_list = (
            self.scale.ticks(self.config.tick_count or 5)
            if isinstance(self.scale, LinearScale)
            else self.scale.ticks()
        )

        self._tick_marks = {}
        for val, label in tick_list:
            mark = self._build_tick(val, label)
            main_group.add(mark)
            self._tick_marks[val] = mark

        # 3. Title
        if self.config.title:
            if is_x:
                main_group.add(
                    Text(self.config.title, size=12).translated(self.length / 2, 35)
                )
            else:
                main_group.add(
                    Text(self.config.title, size=12)
                    .rotated(math.radians(-90))
                    .translated(-40, -self.length / 2)
                )

        return main_group

    def transition(
        self, new_scale: Scale
    ) -> tuple[list[Animation], list[Animation], list[Animation]]:
        from .animation import Styled

        old_scale = self.scale

        # Ticks from new scale
        new_tick_list = (
            new_scale.ticks(self.config.tick_count or 5)
            if isinstance(new_scale, LinearScale)
            else new_scale.ticks()
        )
        new_values = {v for v, l in new_tick_list}
        old_values = set(self._tick_marks.keys())

        enter_vals = new_values - old_values
        update_vals = new_values & old_values
        exit_vals = old_values - new_values

        exit_anims = []
        update_anims = []
        enter_anims = []

        is_x = self.type == "x"

        # 1. Exit
        for val in exit_vals:
            mark = self._tick_marks[val]
            # Simple fade out
            for s in mark.shapes:
                exit_anims.append(s.animate.opacity(0.0))

            def detach_mark(_, m=mark):
                if m.parent:
                    m.parent.remove(m)

            exit_anims[-1].then(detach_mark)
            del self._tick_marks[val]

        # 2. Update
        for val, label in new_tick_list:
            if val in update_vals:
                mark = self._tick_marks[val]
                # New position
                new_pos = (
                    new_scale.center(val)
                    if isinstance(new_scale, BandScale)
                    else new_scale.map(val)
                )

                old_pos = (
                    old_scale.center(val)
                    if isinstance(old_scale, BandScale)
                    else old_scale.map(val)
                )

                diff = new_pos - old_pos
                if diff != 0:
                    for s in mark.shapes:
                        if is_x:
                            update_anims.append(s.animate.translate(dx=diff))
                        else:
                            update_anims.append(s.animate.translate(dy=-diff))

        # 3. Enter
        for val, label in new_tick_list:
            if val in enter_vals:
                # Use new scale for building enter marks
                self.scale = new_scale
                mark = self._build_tick(val, label)
                self.scale = old_scale  # Restore

                # Set initial state (transparent)
                for s in mark.shapes:
                    if isinstance(s, Visual):
                        s.opacity = 0.0

                # Add to axis
                if self._cached_shape and isinstance(self._cached_shape, Group):
                    self._cached_shape.add(mark)

                # Animate in
                for s in mark.shapes:
                    if isinstance(s, Visual):
                        enter_anims.append(s.animate.opacity(1.0))

                self._tick_marks[val] = mark

        # Finalizer to update scale
        def finalize(_):
            self.scale = new_scale

        # We attach finalizer to the last enter anim if it exists, or update
        if enter_anims:
            enter_anims[-1].then(finalize)
        elif update_anims:
            update_anims[-1].then(finalize)
        else:
            finalize(None)

        return exit_anims, update_anims, enter_anims


class Chart(StatefulComponent):
    """
    A grammar-of-graphics component for building visualizations.
    Uses an Altair-lite API: .bar().encode(x='col1', y='col2')
    """

    def __init__(
        self, data: list[dict[str, Any]], width: float = 400, height: float = 300
    ) -> None:
        super().__init__()
        self._data = data
        self.w = width
        self.h = height
        self._mark: Mark = BarMark()
        self._encoding: dict[str, str | Channel] = {}
        self._axes: dict[str, Axis] = {}
        # Persistent state for marks
        self._marks: dict[Any, Shape] = {}
        self._plot_group: Group | None = None
        self._x_axis_comp: _AxisComponent | None = None
        self._y_axis_comp: _AxisComponent | None = None

    @property
    def data(self) -> list[dict[str, Any]]:
        return self._data

    @data.setter
    def data(self, value: list[dict[str, Any]]):
        self._data = value
        self.invalidate()

    def _get_id(self, row: dict[str, Any], index: int) -> Any:
        # 1. User provided explicit ID
        if "_id" in row:
            return row["_id"]
        if "id" in row:
            return row["id"]

        # 2. Use 'x' field as identity if it's categorical (common case)
        x_field = self._get_field("x")
        if x_field and x_field in row:
            val = row[x_field]
            if isinstance(val, (str, int)):
                return val

        # 3. Fallback to list index
        return index

    def bar(self, padding: float = 0.1, **kwargs) -> Self:
        self.invalidate()
        return self.mark(BarMark(padding=padding, **kwargs))

    def mark_bar(self, padding: float = 0.1, **kwargs) -> Self:
        """Alias for .bar()"""
        return self.bar(padding=padding, **kwargs)

    def point(self, size: float = 5.0, **kwargs) -> Self:
        self.invalidate()
        return self.mark(PointMark(size=size, **kwargs))

    def mark_point(self, size: float = 5.0, **kwargs) -> Self:
        """Alias for .point()"""
        return self.point(size=size, **kwargs)

    def mark(self, mark: Mark) -> Self:
        """Set a custom mark implementation."""
        self._mark = mark
        self.invalidate()
        return self

    def encode(self, **channels: str | Channel) -> Self:
        """Map visual channels (x, y, color) to data fields."""
        for name, value in channels.items():
            self._encoding[name] = value
            if isinstance(value, Channel) and value.axis:
                self._axes[name] = value.axis
        self.invalidate()
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
        self.invalidate()
        return self

    def _get_field(self, channel: str) -> str | None:
        val = self._encoding.get(channel)
        if isinstance(val, Channel):
            return val.field
        return val

    def _get_domain(self, data: list[dict[str, Any]], field: str) -> list[Any]:
        return [d[field] for d in data]

    def _is_quantitative(self, data: list[dict[str, Any]], channel: str) -> bool:
        if not data:
            return False
        f = self._get_field(channel)
        if not f:
            return False
        val = data[0].get(f)
        return isinstance(val, (int, float))

    def _get_scales(
        self, data: list[dict[str, Any]], plot_w: float, plot_h: float
    ) -> dict[str, Scale | ColorScale]:
        x_field = self._get_field("x")
        y_field = self._get_field("y")
        color_field = self._get_field("color")

        if not x_field or not y_field:
            return {}

        scales: dict[str, Scale | ColorScale] = {}

        # X Scale
        x_domain = self._get_domain(data, x_field)
        if self._is_quantitative(data, "x") and not isinstance(self._mark, BarMark):
            scales["x"] = LinearScale((min(x_domain), max(x_domain)), (0, plot_w))
        else:
            scales["x"] = BandScale(
                list(dict.fromkeys(x_domain)),
                (0, plot_w),
                padding=self._mark.params.get("padding", 0.1),
            )

        # Y Scale
        y_domain = self._get_domain(data, y_field)
        if self._is_quantitative(data, "y"):
            scales["y"] = LinearScale((0, max(y_domain)), (0, plot_h))
        else:
            scales["y"] = BandScale(list(dict.fromkeys(y_domain)), (0, plot_h))

        # Color Scale
        if color_field:
            scales["color"] = ColorScale(
                list(dict.fromkeys(self._get_domain(data, color_field)))
            )

        return scales

    def _build(self) -> Shape:
        # Initialize plot group even for empty data to support animations
        self._plot_group = Group()

        if not self._encoding:
            return Group()

        # 1. Determine Margins
        margin_left = 60 if "y" in self._axes else 10
        margin_bottom = 50 if "x" in self._axes else 10
        margin_right = 20
        margin_top = 20

        plot_w = self.w - margin_left - margin_right
        plot_h = self.h - margin_bottom - margin_top

        # 2. Setup Scales
        scales = self._get_scales(self._data, plot_w, plot_h)
        if not scales:
            return Group().add(self._plot_group)

        # 3. Generate Content
        main_group = Group()

        new_marks = {}
        for i, row in enumerate(self._data):
            row_id = self._get_id(row, i)
            shape = self._mark.build(row, self._encoding, scales, plot_h)
            self._plot_group.add(shape)
            new_marks[row_id] = shape

        # Update persistent state
        self._marks = new_marks

        # Position plot group
        self._plot_group.translated(margin_left, margin_top)
        main_group.add(self._plot_group)

        # 4. Generate Axes
        if "x" in self._axes:
            self._x_axis_comp = _AxisComponent(
                "x", scales["x"], self._axes["x"], plot_w, plot_h
            )
            self._x_axis_comp.translated(margin_left, margin_top + plot_h)
            main_group.add(self._x_axis_comp)

        if "y" in self._axes:
            self._y_axis_comp = _AxisComponent(
                "y", scales["y"], self._axes["y"], plot_h, plot_w
            )
            self._y_axis_comp.translated(margin_left, margin_top + plot_h)
            main_group.add(self._y_axis_comp)

        return main_group

    @property
    def animate(self) -> ChartAnimator:
        return ChartAnimator(self)


class ChartAnimator:
    def __init__(self, chart: Chart):
        self.chart = chart

    def data(self, new_data: list[dict[str, Any]]) -> Animation:
        from .animation import Parallel, Sequence

        # Ensure the chart is built once to have the initial state (_marks, _plot_group)
        _ = self.chart._shape

        # 1. Setup dimensions and scales for new data
        margin_left = 60 if "y" in self.chart._axes else 10
        margin_bottom = 50 if "x" in self.chart._axes else 10
        margin_right = 20
        margin_top = 20
        plot_w = self.chart.w - margin_left - margin_right
        plot_h = self.chart.h - margin_bottom - margin_top

        # Compute new scales without updating the official data yet
        new_scales = self.chart._get_scales(new_data, plot_w, plot_h)

        # 2. Diffing
        old_data = self.chart.data
        old_ids = {self.chart._get_id(row, i) for i, row in enumerate(old_data)}
        new_ids_list = [self.chart._get_id(row, i) for i, row in enumerate(new_data)]
        new_ids = set(new_ids_list)

        enter_ids = new_ids - old_ids
        update_ids = new_ids & old_ids
        exit_ids = old_ids - new_ids

        exit_anims = []
        update_anims = []
        enter_anims = []

        # 3. Exit
        for row_id in exit_ids:
            shape = self.chart._marks[row_id]
            anim = self.chart._mark.exit(shape)
            exit_anims.append(anim)
            # Remove from tracking (it will be detached via .then() callback)
            del self.chart._marks[row_id]

        # 4. Update
        for i, row in enumerate(new_data):
            row_id = self.chart._get_id(row, i)
            if row_id in update_ids:
                shape = self.chart._marks[row_id]
                anim = self.chart._mark.update(
                    shape, row, self.chart._encoding, new_scales, plot_h
                )
                update_anims.append(anim)

        # 5. Enter
        for i, row in enumerate(new_data):
            row_id = self.chart._get_id(row, i)
            if row_id in enter_ids:
                shape, anim = self.chart._mark.enter(
                    row, self.chart._encoding, new_scales, plot_h
                )
                if self.chart._plot_group:
                    self.chart._plot_group.add(shape)
                self.chart._marks[row_id] = shape
                enter_anims.append(anim)

        # 6. Axis Transitions
        if self.chart._x_axis_comp:
            ex, up, en = self.chart._x_axis_comp.transition(new_scales["x"])
            exit_anims.extend(ex)
            update_anims.extend(up)
            enter_anims.extend(en)
        if self.chart._y_axis_comp:
            ex, up, en = self.chart._y_axis_comp.transition(new_scales["y"])
            exit_anims.extend(ex)
            update_anims.extend(up)
            enter_anims.extend(en)

        # Build sequence of stages
        stages = []
        if exit_anims:
            stages.append(Parallel(*exit_anims))
        if update_anims:
            stages.append(Parallel(*update_anims))
        if enter_anims:
            stages.append(Parallel(*enter_anims))

        # Finally, update the chart's data property WITHOUT invalidating
        # so that future builds use the new data.
        def finalize(_):
            self.chart._data = new_data

        if not stages:
            # Fallback for no changes
            from .animation import Wait

            return Wait(0).then(finalize)

        return Sequence(*stages).then(finalize)
