from __future__ import annotations
from pathlib import Path
from .core import Shape, Bounds
from .base import Group


class Canvas(Group):
    def __init__(self, width: float = 1000, height: float = 1000) -> None:
        super().__init__()

        self.width = width
        self.height = height
        self._defs: list[str] = [
            """<marker id="arrowhead" markerWidth="10" markerHeight="7"
            refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="black" />
            </marker>"""
        ]
        # Default viewbox is the full canvas size
        self._viewbox: tuple[float, float, float, float] = (0, 0, width, height)

    def _repr_svg_(self) -> str:
        """Enables automatic rendering in Jupyter/Quarto environments."""
        return self._build_svg()

    def display(self) -> None:
        """
        Explicitly renders the SVG in supported interactive environments.

        Uses IPython.display to render the SVG. If the environment does
        not support rich display, it falls back to printing the SVG string.
        """
        from IPython.display import SVG, display as ipy_display

        ipy_display(SVG(self._build_svg()))

    def fit(self, padding: float = 0, crop: bool = True) -> Canvas:
        """
        Reduces the viewBox to perfectly fit all added shapes.
        If crop is True (default), the width and height will also be adjusted.
        """
        all_bounds = [s.bounds() for s in self.shapes]
        tight_bounds = Bounds.union(*all_bounds).padded(padding)

        self._viewbox = (
            tight_bounds.x,
            tight_bounds.y,
            tight_bounds.width,
            tight_bounds.height,
        )

        if crop:
            self.width = tight_bounds.width
            self.height = tight_bounds.height

        return self

    def _build_svg(self) -> str:
        content = "\n  ".join(s.render() for s in self.shapes)
        defs_content = "\n    ".join(self._defs)

        vx, vy, vw, vh = self._viewbox
        return (
            f'<svg width="{self.width}" height="{self.height}" '
            f'viewBox="{vx} {vy} {vw} {vh}" '
            'xmlns="http://www.w3.org/2000/svg">\n'
            f"  <defs>\n    {defs_content}\n  </defs>\n"
            f"  {content}\n"
            "</svg>"
        )

    def save(self, path: str | Path) -> None:
        """Writes the canvas content to an SVG file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._build_svg())

    def __str__(self) -> str:
        return self._build_svg()
