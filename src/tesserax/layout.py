from abc import abstractmethod
from typing import Literal
from .core import Shape, Bounds
from .base import Group


class Layout(Group):
    def __init__(self, shapes: list[Shape] | None = None) -> None:
        super().__init__(shapes)

    @abstractmethod
    def do_layout(self) -> None:
        """
        Implementation must iterate over self.shapes, RESET their transforms,
        and then apply new translations.
        """
        ...

    def add(self, *shapes: Shape) -> "Layout":
        super().add(*shapes)
        self.do_layout()
        return self


type Align = Literal["start", "middle", "end"]


class Row(Layout):
    def __init__(
        self,
        shapes: list[Shape] | None = None,
        align: Align = "middle",
        gap: float = 0,
    ) -> None:
        self.align = align
        self.gap = gap
        super().__init__(shapes)

    def do_layout(self) -> None:
        if not self.shapes:
            return

        # 1. First pass: Reset transforms so we get pure local bounds
        for s in self.shapes:
            s.transform.reset()

        # 2. Calculate offsets based on the 'clean' shapes
        max_h = max(s.local().height for s in self.shapes)
        current_x = 0.0

        for shape in self.shapes:
            b = shape.local()

            # Calculate Y based on baseline
            match self.align:
                case "start":
                    dy = -b.y
                case "middle":
                    dy = (max_h / 2) - (b.y + b.height / 2)
                case "end":
                    dy = max_h - (b.y + b.height)
                case _:
                    dy = 0

            # 3. Apply the strict layout position
            shape.transform.tx = current_x - b.x
            shape.transform.ty = dy

            current_x += b.width + self.gap


class Column(Row):
    def __init__(
        self,
        shapes: list[Shape] | None = None,
        align: Align = "middle",
        gap: float = 0,
    ) -> None:
        super().__init__(shapes, align, gap)

    def do_layout(self) -> None:
        if not self.shapes:
            return

        for s in self.shapes:
            s.transform.reset()

        max_w = max(s.local().width for s in self.shapes)
        current_y = 0.0

        for shape in self.shapes:
            b = shape.local()

            match self.align:
                case "start":
                    dx = -b.x
                case "end":
                    dx = max_w - (b.x + b.width)
                case "middle":
                    dx = (max_w / 2) - (b.x + b.width / 2)
                case _:
                    dx = 0

            shape.transform.tx = dx
            shape.transform.ty = current_y - b.y

            current_y += b.height + self.gap
