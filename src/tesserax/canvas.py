from __future__ import annotations
from pathlib import Path
from typing import Self, TYPE_CHECKING, cast
from .core import Shape, Bounds
from .base import Group
from .color import Colors

if TYPE_CHECKING:
    from .animation import CameraAnimator


class Canvas(Group):
    def __init__(
        self,
        width: float = 1000,
        height: float = 1000,
        quality: str | int = "standard",
    ) -> None:
        super().__init__()

        self.width = width
        self.height = height
        self._defs: dict[str, Shape] = {}

        # Quality settings for rasterization (supersampling)
        # "draft" = 1x, "standard" = 2x, "retina" = 4x
        if isinstance(quality, int):
            self.quality_scale = quality
        else:
            self.quality_scale = {"draft": 1, "standard": 2, "retina": 4}.get(
                quality.lower(), 2
            )

        # Default viewbox is the full canvas size
        self._viewbox: tuple[float, float, float, float] = (0, 0, width, height)

        # Define the default arrowhead
        # We need to import Path here to avoid circular definition issues
        from .base import Path

        arrow = (
            Path(fill=Colors.Black, stroke=Colors.Transparent)
            .jump_to(-10, -4)
            .line_to(0, 0)
            .line_to(-10, 4)
            .close()
        )
        self.define("arrow", arrow)

    def define(self, id: str, shape: Shape) -> Self:
        """Registers a shape as a reusable SVG marker."""
        self._defs[id] = shape
        return self

    def _repr_svg_(self) -> str:
        """Enables automatic rendering in Jupyter/Quarto environments."""
        return self._build_svg()

    def display(self) -> None:
        """
        Explicitly renders the SVG in supported interactive environments.

        Uses IPython.display to render the SVG. If the environment does
        not support rich display, it falls back to printing the SVG string.
        """
        try:
            from IPython.display import SVG, display
        except ImportError:
            raise ImportError("IPython is required for Canvas.display()")

        display(SVG(self._build_svg()))

    def fit(
        self, padding: float = 0, *, crop: bool = True, bounds: Bounds | None = None
    ) -> Canvas:
        """
        Reduces the viewBox to perfectly fit all added shapes.
        If crop is True (default), the width and height will also be adjusted.
        If bounds is provided, it fits to that specific area instead of the shapes.
        """
        if bounds is None:
            all_bounds = [s.bounds() for s in self.shapes]
            if not all_bounds:
                return self
            tight_bounds = Bounds.union(*all_bounds).padded(padding)
        else:
            tight_bounds = bounds.padded(padding)

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
        defs_content = []

        for id, shape in self._defs.items():
            b = shape.local()
            # orient="auto" ensures the marker rotates with the line direction
            # refX/refY=0 assumes the shape is designed with (0,0) as the connection point
            defs_content.append(
                f'<marker id="{id}" viewBox="{b.x} {b.y} {b.width} {b.height}" '
                f'refX="0" refY="0" orient="auto" markerWidth="{b.width}" markerHeight="{b.height}">'
                f"{shape.render()}"
                f"</marker>"
            )

        defs_str = f"<defs>{''.join(defs_content)}</defs>" if defs_content else ""

        vx, vy, vw, vh = self._viewbox

        return (
            f'<svg width="{self.width}" height="{self.height}" '
            f'viewBox="{vx} {vy} {vw} {vh}" '
            'xmlns="http://www.w3.org/2000/svg">\n'
            f"  {defs_str}\n"
            f"  {content}\n"
            "</svg>"
        )

    def save(self, path: str | Path, dpi: int = 300) -> None:
        """
        Exports the canvas to a raster or vector format with high fidelity.

        Supported formats: .png, .pdf, .svg, .ps.
        Requires 'resvg-py' and 'pillow' for high-quality rasterization.
        """

        svg_data = self._build_svg()
        target = str(path)
        extension = Path(path).suffix.lower()

        if extension == ".svg":
            with open(path, "w", encoding="utf-8") as fp:
                fp.write(svg_data)

            return

        try:
            from resvg_py import svg_to_bytes as render
            from PIL import Image
            import io
        except ImportError:
            raise ImportError(
                "High-quality export requires 'resvg-py' and 'pillow'. "
                "Install with: pip install tesserax[export]"
            )

        # We use the quality_scale for supersampling
        # resvg-py uses a 'scale' parameter for the output size
        render_scale = self.quality_scale

        match extension:
            case ".png":
                # 1. Render at high resolution (supersampling)
                png_data = render(svg_data, zoom=render_scale)

                # 2. If scale > 1, downsample using Lanczos for crisp edges
                if render_scale > 1:
                    img = Image.open(io.BytesIO(png_data))
                    # Target size is the original width/height
                    target_size = (int(self.width), int(self.height))
                    img = img.resize(target_size, resample=Image.Resampling.LANCZOS)
                    img.save(target, "PNG")
                else:
                    with open(target, "wb") as f:
                        f.write(png_data)

            case ".pdf" | ".ps":
                # For vector formats like PDF/PS, we fall back to CairoSVG if available
                try:
                    import cairosvg

                    if extension == ".pdf":
                        cairosvg.svg2pdf(
                            bytestring=svg_data.encode("utf-8"),
                            write_to=target,
                            dpi=dpi,
                        )
                    else:
                        cairosvg.svg2ps(
                            bytestring=svg_data.encode("utf-8"),
                            write_to=target,
                            dpi=dpi,
                        )
                except ImportError:
                    raise ImportError(
                        f"Exporting to {extension} requires 'cairosvg'."
                    )
            case _:
                raise ValueError(f"Unsupported export format: {extension}")

    def __str__(self) -> str:
        return self._build_svg()


class Camera(Shape):
    def __init__(self, width: float, height: float, active: bool = False) -> None:
        super().__init__()
        self.width = width
        self.height = height
        self.active = active

    def local(self) -> Bounds:
        # Camera is centered on its transform position
        return Bounds(-self.width / 2, -self.height / 2, self.width, self.height)

    def _render(self) -> str:
        # If active and attached to a Canvas, force the viewbox
        if self.active and self.parent and isinstance(self.parent, Canvas):
            # We fit the canvas to the camera's current world bounds.
            # crop=True ensures the output SVG size matches the camera size.
            self.parent.fit(bounds=self.bounds(), crop=True)

        return ""  # Invisible

    @property
    def animate(self) -> CameraAnimator:
        from .animation import CameraAnimator

        if self._animator is None:
            self._animator = CameraAnimator(self)

        return cast(CameraAnimator, self._animator)
