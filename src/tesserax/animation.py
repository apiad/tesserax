from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Self
import bisect
import math
import random
import string
import io
import base64
import imageio
import cairosvg


from .base import IVisual, Text, Polyline
from .core import IShape, Point, Shape, Transform
from .canvas import Canvas


# --- Easing Functions ---
def linear(t: float) -> float:
    return t


def smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def ease_out(t: float) -> float:
    return t * (2 - t)


def ease_in_out_cubic(t: float) -> float:
    return 3 * t * t - 2 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


# --- Core Animation Class ---


class Animation(ABC):
    """
    Base class for logic that modifies a shape over a normalized time t [0, 1].
    """

    def __init__(self):
        self.rate = linear
        self.relative_weight = 1.0
        self._started = False

    def begin(self) -> None:
        """Capture initial state. Only run once per playback."""
        if not self._started:
            self._start()
            self._started = True

    def _start(self) -> None:
        """Subclasses implement specific state capture here."""
        pass

    def update(self, t: float) -> None:
        """Apply changes based on normalized progress t."""
        if not self._started:
            raise TypeError("You need to call begin() first.")

        self._update(self.rate(t))

    @abstractmethod
    def _update(self, t: float):
        pass

    def finish(self) -> None:
        """Force final state."""
        if not self._started:
            self.begin()

        self.update(1.0)

    # --- Fluent API Modifiers ---

    def weight(self, w: float) -> Self:
        self.relative_weight = w
        return self

    def rated(self, func: Callable[[float], float]) -> Self:
        self.rate = func
        return self

    def smoothed(self) -> Self:
        return self.rated(smooth)

    def delayed(self, delay_ratio: float) -> Animation:
        return Wrapped(self).rated(
            lambda t: 0 if t < delay_ratio else (t - delay_ratio) / (1 - delay_ratio),
        )

    def repeating(self, times: float) -> Animation:
        return Wrapped(self).rated(lambda t: (t * times) % 1.0)

    def looping(self) -> Animation:
        return Wrapped(self).rated(lambda t: t / 2 if t < 0.5 else 1 - t / 2)

    def reversed(self) -> Animation:
        return Wrapped(self).rated(lambda t: 1.0 - t)

    # --- Operator Overloads ---

    def __mul__(self, factor: float) -> Animation:
        return self.repeating(factor)

    def __or__(self, other: Animation) -> Animation:
        children = self.children if isinstance(self, Sequence) else [self]

        if isinstance(other, Sequence):
            children.extend(other.children)
        else:
            children.append(other)

        return Sequence(*children)

    def __add__(self, other: Animation) -> Animation:
        children = self.children if isinstance(self, Parallel) else [self]

        if isinstance(other, Sequence):
            children.extend(other.children)
        else:
            children.append(other)

        return Parallel(*children)



# --- Structural Animations ---


class Wrapped(Animation):
    def __init__(self, child: Animation):
        super().__init__()
        self.child = child
        self.relative_weight = child.relative_weight

    def _start(self):
        self.child.begin()

    def _update(self, t: float):
        self.child.update(t)


class Sequence(Animation):
    def __init__(self, *animations: Animation, **kwargs):
        super().__init__(**kwargs)
        self.children = list(animations)

        total_weight = sum(c.relative_weight for c in animations)
        self.checkpoints = []
        current = 0.0

        for c in animations:
            width = c.relative_weight / (total_weight or 1)
            current += width
            self.checkpoints.append(current)

    def _update(self, t: float):
        n = len(self.children)

        if n == 0:
            return

        idx = bisect.bisect_left(self.checkpoints, t)

        if idx >= n:
            idx = n - 1

        start_t = self.checkpoints[idx - 1] if idx > 0 else 0.0
        end_t = self.checkpoints[idx]
        duration = end_t - start_t

        local_t = (t - start_t) / duration if duration > 1e-9 else 1.0

        # Catch up previous
        for i in range(idx):
            child = self.children[i]

            if not child._started:
                child.begin()

            child.update(1.0)

        # Update active
        active = self.children[idx]

        if not active._started:
            active.begin()

        active.update(local_t)


class Parallel(Animation):
    def __init__(self, *animations: Animation, **kwargs):
        super().__init__(**kwargs)
        self.children = list(animations)

    def _start(self) -> None:
        for anim in self.children:
            anim.begin()

    def _update(self, t: float):
        for anim in self.children:
            anim.update(t)


class Delayed(Animation):
    """
    Plays a group of animations with a time lag.
    lag_ratio: 0.0 (parallel) -> 1.0 (sequential)
    """

    def __init__(self, *animations: Animation, lag_ratio: float = 0.1, **kwargs):
        super().__init__(**kwargs)
        self.anims = animations
        self.lag = lag_ratio

    def begin(self):
        self._started = True

    def update(self, t: float):
        t = self.rate(t)
        n = len(self.anims)
        if n == 0:
            return

        # Total span in relative time units = 1.0 + total lag
        total_span = 1.0 + (n - 1) * self.lag

        for i, anim in enumerate(self.anims):
            # Calculate start/end time for this specific animation in global t
            start = (i * self.lag) / total_span
            end = (1.0 + i * self.lag) / total_span

            if t < start:
                local_t = 0.0
            elif t > end:
                local_t = 1.0
            else:
                local_t = (t - start) / (end - start)

            if local_t > 0 and not anim._started:
                anim.begin()

            anim.update(local_t)


class Wait(Animation):
    def __init__(self, weight: float = 1.0):
        super().__init__()
        self.weight(weight)


# --- Property Animations ---


class Transformed(Animation):
    def __init__(self, shape: IShape, target: Transform, **kwargs):
        super().__init__(**kwargs)
        self.shape = shape
        self.target = target
        self.start_transform = None

    def _start(self):
        self.start_transform = self.shape.transform.copy()

    def _update(self, t: float):
        if self.start_transform is None:
            raise TypeError("You need to call begin() first.")

        new_trans = self.start_transform.lerp(self.target, t)
        self.shape.transform = new_trans


class Styled(Animation):
    def __init__(self, shape: IVisual, fill=None, stroke=None, width=None, **kwargs):
        super().__init__(**kwargs)
        self.shape = shape
        self.target_fill = fill
        self.target_stroke = stroke
        self.target_width = width
        self.start_fill = None
        self.start_stroke = None
        self.start_width = None

    def _start(self):
        self.start_fill = self.shape.fill
        self.start_stroke = self.shape.stroke
        self.start_width = self.shape.width

    def _update(self, t: float):

        if (
            self.start_fill is None
            or self.start_stroke is None
            or self.start_width is None
        ):
            raise TypeError("You need to call begin() first.")

        if self.target_width is not None:
            self.shape.width = (
                self.start_width + (self.target_width - self.start_width) * t
            )
        if self.target_fill is not None:
            self.shape.fill = self.start_fill.towards(self.target_fill, t)
        if self.target_stroke is not None:
            self.shape.stroke = self.start_stroke.towards(self.target_stroke, t)


# --- Specialized Animations ---


class Written(Animation):
    def __init__(self, shape: Text, **kwargs):
        super().__init__(**kwargs)
        self.shape = shape
        self.full_text = getattr(shape, "text", "")

    def _start(self):
        self.full_text = getattr(self.shape, "text", "")

    def _update(self, t: float):
        count = int(t * len(self.full_text))
        self.shape.content = self.full_text[:count]


class Scrambled(Animation):
    def __init__(self, shape: Text, seed: int = 42, **kwargs):
        super().__init__(**kwargs)
        self.shape = shape
        self.full_text = getattr(shape, "text", "")
        self.rng = random.Random(seed)

    def _update(self, t: float):
        total = len(self.full_text)
        resolved = int(t * total)

        result = list(self.full_text[:resolved])
        remaining = total - resolved
        chars = string.ascii_letters + string.digits + "!@#$%"
        scramble = [self.rng.choice(chars) for _ in range(remaining)]
        self.shape.content = "".join(result + scramble)


class Morphed(Animation):
    def __init__(self, shape: Polyline, target_points: list, **kwargs):
        super().__init__(**kwargs)
        self.shape = shape
        self.target_points = target_points
        self.start_points = []
        # Lazy import for Point to avoid circular dependency issues at module level
        from .core import Point

        self._Point = Point

    def _start(self):
        if not hasattr(self.shape, "points"):
            # Fail gracefully or raise
            self.start_points = []
            return

        current = getattr(self.shape, "points")
        self.start_points = [self._Point(p.x, p.y) for p in current]

        # Simple safety check on length
        if len(self.start_points) != len(self.target_points):
            print(
                f"Warning: Morph mismatch {len(self.start_points)} vs {len(self.target_points)}"
            )

    def _update(self, t: float):
        if not self.start_points:
            return

        new_pts = []
        for s, e in zip(self.start_points, self.target_points):
            nx = s.x + (e.x - s.x) * t
            ny = s.y + (e.y - s.y) * t
            new_pts.append(self._Point(nx, ny))

        self.shape.points = new_pts


class Following(Animation):
    def __init__(
        self, shape: IShape, path: Shape, rotate_along: bool = False, **kwargs
    ):
        super().__init__(**kwargs)
        self.shape = shape
        self.path = path
        self.rotate_along = rotate_along

    def _update(self, t: float):
        # Requires path to have point_at(t) -> Point
        if not hasattr(self.path, "point_at"):
            return

        target_point = self.path.point_at(alpha)

        # Set position directly (Global coordinates)
        self.shape.transform.tx = target_point.x
        self.shape.transform.ty = target_point.y

        if self.rotate_along:
            epsilon = 0.01
            # Look ahead for tangent
            next_t = min(1.0, t + epsilon)
            # If we are at the end, look backward
            if next_t == t:
                next_t = t
                t = max(0.0, t - epsilon)
                target_point = self.path.point_at(t)

            next_p = self.path.point_at(next_t)
            angle = math.atan2(next_p.y - target_point.y, next_p.x - target_point.x)
            self.shape.transform.rotation = angle


class Warped(Animation):
    """
    Applies a time-dependent transformation function to a shape's points.
    The function should accept a Point and the current time t [0, 1].
    """

    def __init__(
        self, shape: Polyline, func: Callable[[Point, float], Point], **kwargs
    ):
        super().__init__(**kwargs)
        self.shape = shape
        self.func = func
        self.start_points: list[Point] = []

    def _start(self):
        # Capture the points exactly as they are when the animation begins
        if hasattr(self.shape, "points"):
            self.start_points = list(self.shape.points)

    def _update(self, t: float):
        if not self.start_points:
            return

        # Map the original points through the function at the current time t
        self.shape.points = [self.func(p, t) for p in self.start_points]

        # If the shape is a Component (like Polyline), it may need to rebuild its path
        if hasattr(self.shape, "refresh"):
            self.shape.refresh()


# --- Factory Class ---


class Animator[TShape: IShape]:
    """Helper attached to shape.animate"""

    def __init__(self, shape: TShape):
        self.shape = shape

    # Transform
    def translate(self, dx: float = 0, dy: float = 0) -> Animation:
        target = self.shape.transform.copy()
        target.tx += dx
        target.ty += dy
        return Transformed(self.shape, target)

    def rotate(self, angle: float) -> Animation:
        target = self.shape.transform.copy()
        target.rotation += angle
        return Transformed(self.shape, target)

    def scale(self, factor: float) -> Animation:
        target = self.shape.transform.copy()
        target.sx *= factor
        target.sy *= factor
        return Transformed(self.shape, target)

    def follow(self, path: Shape, rotate: bool = False) -> Animation:
        return Following(self.shape, path, rotate_along=rotate)


class StyledAnimator[TShape: IVisual](Animator[TShape]):
    def __init__(self, shape: TShape):
        super().__init__(shape)

    # Style
    def fill(self, color: str) -> Animation:
        return Styled(self.shape, fill=color)

    def stroke(self, color: str) -> Animation:
        return Styled(self.shape, stroke=color)

    def style(self, **kwargs) -> Animation:
        return Styled(self.shape, **kwargs)


class TextAnimator(StyledAnimator[Text]):
    def __init__(self, shape: Text):
        super().__init__(shape)

    # Text
    def write(self) -> Animation:
        return Written(self.shape)

    def scramble(self) -> Animation:
        return Scrambled(self.shape)


class PolylineAnimator(StyledAnimator[Polyline]):
    # Geometry
    def morph(self, target: Polyline) -> Animation:
        pts = target.points
        return Morphed(self.shape, pts)

    def warp(self, func: Callable[[Point, float], Point]) -> Animation:
        """
        Creates a warp animation using a function that maps (Point, t) -> Point.
        """
        return Warped(self.shape, func)


# --- Scene Class ---


class Scene:
    def __init__(self, canvas: Canvas, fps: int = 30, background: str = "white"):
        self.canvas = canvas
        self.fps = fps
        self.background = background
        self._frames: list[bytes] = []

    def capture(self):
        svg = self.canvas._build_svg()
        png = cairosvg.svg2png(
            bytestring=svg.encode("utf-8"), background_color=self.background
        )
        self._frames.append(png)

    def play(self, *animations: Animation, duration: float = 1.0):
        if not animations:
            return

        total = int(duration * self.fps)

        # Initialize
        for anim in animations:
            anim.begin()

        # Loop
        for i in range(total):
            t = i / total

            for anim in animations:
                anim.update(t)

            self.capture()

        # Finalize
        for anim in animations:
            anim.finish()

    def save(self, dest, format=None):
        if not self._frames:
            return
        images = [imageio.imread(io.BytesIO(f)) for f in self._frames]

        kwargs = {"fps": self.fps}
        if format == "mp4":
            kwargs["quality"] = 8
        else:
            kwargs["loop"] = 0

        imageio.mimsave(dest, images, format=format or "gif", **kwargs)

    def display(self):
        try:
            from IPython.display import display, HTML
        except ImportError:
            return

        buf = io.BytesIO()
        self.save(buf, format="gif")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        display(
            HTML(f'<img src="data:image/gif;base64,{b64}" style="max-width:100%"/>')
        )

    def _ipython_display_(self):
        self.display()
