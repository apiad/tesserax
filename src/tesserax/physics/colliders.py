from dataclasses import dataclass


@dataclass
class Collider:
    pass


@dataclass
class CircleCollider(Collider):
    radius: float


@dataclass
class BoxCollider(Collider):
    width: float
    height: float
