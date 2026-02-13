from abc import ABC, abstractmethod
from .core import Body, Point


class Field(ABC):
    @abstractmethod
    def apply(self, bodies: list[Body]):
        pass


class SimpleField(Field):
    def apply(self, bodies: list[Body]):
        for b in bodies:
            if not b.static:
                self._apply(b)

    @abstractmethod
    def _apply(self, b: Body):
        pass


class InverseDistanceField(SimpleField):
    def __init__(self, intensity: float, center=Point(0, 0), exponent: int = 2) -> None:
        self.intensity = intensity
        self.center = center
        self.exponent = exponent

    def _apply(self, b: Body):
        f = b.mass * self.intensity / (self.center - b.pos).magnitude() ** self.exponent
        b.apply((self.center - b.pos).normalize() * f)


class Gravity(Field):
    def __init__(self, g: float = 980.0):  # Pixels/s^2
        self.g = Point(0, g)

    def apply(self, bodies: list[Body]):
        for b in bodies:
            if not b.static:
                # F = m * a -> a is just g
                b.acc += self.g


class Drag(Field):
    def __init__(self, k: float = 0.1):
        self.k = k

    def apply(self, bodies: list[Body]):
        for b in bodies:
            if not b.static:
                # Simple linear drag
                b.acc -= b.vel * self.k
