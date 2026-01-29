from abc import abstractmethod
from typing import Literal
from .core import Shape, Bounds, Group, Anchor


class Layout(Group):
    """
    A Group that automatically positions its children according to a strategy.
    """

    def __init__(
        self,
        shapes: list[Shape] | None = None,
    ) -> None:
        super().__init__(shapes=shapes)
        shapes = shapes
        self._is_dirty = True

    def _refresh(self) -> None:
        if self._is_dirty:
            self.shapes = self.layout(self.shapes)
            self._is_dirty = False

    @abstractmethod
    def layout(self, shapes: list[Shape]) -> list[Shape]:
        """
        Logic to return a list of Shapes (usually Transforms)
        positioned correctly.
        """
        ...

    def bounds(self) -> Bounds:
        self._refresh()
        return super().bounds()

    def render(self) -> str:
        self._refresh()
        return super().render()

    def add(self, *shapes: Shape) -> "Layout":
        super().add(*shapes)
        self._is_dirty = True
        return self


type Baseline = Literal["start", "middle", "end"]


class Row(Layout):
    def __init__(
        self,
        baseline: Baseline,
        padding: float = 0,
        shapes: list[Shape] | None = None,
    ) -> None:
        super().__init__(shapes)
        self.baseline = baseline
        self.padding = padding

    def layout(self, shapes: list[Shape]) -> list[Shape]:
        if not shapes:
            return []

        # Find the maximum height to calculate baseline offsets
        max_h = max(s.bounds().height for s in shapes)
        current_x = 0.0
        positioned_shapes: list[Shape] = []

        for shape in shapes:
            b = shape.bounds()

            # Calculate Y based on baseline
            match self.baseline:
                case "start":
                    dy = -b.y  # Align top edge to y=0
                case "middle":
                    dy = max_h - (b.y + b.height)
                case "end":
                    dy = (max_h / 2) - (b.y + b.height / 2)
                case _:
                    dy = 0

            positioned_shapes.append(shape.translated(current_x - b.x, dy))
            current_x += b.width + self.padding

        return positioned_shapes


class Column(Row):
    def layout(self, shapes: list[Shape]) -> list[Shape]:
        if not shapes:
            return []

        max_w = max(s.bounds().width for s in shapes)
        current_y = 0.0
        positioned_shapes: list[Shape] = []

        for shape in shapes:
            b = shape.bounds()

            # Calculate X based on horizontal baseline (left, center, right)
            match self.baseline:
                case "start":
                    dx = -b.x
                case "end":
                    dx = max_w - (b.x + b.width)
                case "middle":
                    dx = (max_w / 2) - (b.x + b.width / 2)
                case _:
                    dx = 0

            positioned_shapes.append(shape.translated(dx, current_y - b.y))
            current_y += b.height + self.padding

        return positioned_shapes
