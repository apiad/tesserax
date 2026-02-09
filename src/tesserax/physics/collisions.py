from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, cast
from .core import Body, Point
from .colliders import CircleCollider, BoxCollider, Collider


SOLVERS = dict()


def solver[C1: Collider, C2: Collider](t1: type[C1], t2: type[C2]):
    def wrapper(func: Callable[[Body, Body], Collision | None]):
        Collision.register(t1, t2, func)
        return func

    return wrapper


@dataclass
class Collision:
    """Stores information about a collision between A and B."""

    a: Body
    b: Body
    normal: Point  # Points from A to B
    depth: float  # Penetration depth

    @staticmethod
    def register[C1: Collider, C2: Collider](
        t1: type[C1], t2: type[C2], solver: Callable[[Body, Body], Collision | None]
    ):
        SOLVERS[(t1, t2)] = solver
        SOLVERS[(t2, t1)] = lambda c1, c2: solver(c2, c1)

    @classmethod
    def solve(cls, a: Body, b: Body) -> Collision | None:
        """Dispatcher: checks types and calls specific solver."""
        t1 = type(a.collider)
        t2 = type(b.collider)

        if solver := SOLVERS.get((t1, t2)):
            return solver(a, b)

        return None

    def resolve(self):
        """Applies physics impulse to bounce objects."""
        a, b = self.a, self.b

        # 1. Positional Correction (Prevent Sinking)
        # Move objects apart based on inverse mass (lighter object moves more)
        percent = 0.8  # Penetration percentage to correct
        slop = 0.01  # Penetration allowance
        total_inv_mass = a.inv_mass + b.inv_mass

        if total_inv_mass == 0:
            return

        correction = max(self.depth - slop, 0.0) / total_inv_mass * percent
        correction_vec = self.normal * correction

        if not a.static:
            a.pos -= correction_vec * a.inv_mass
        if not b.static:
            b.pos += correction_vec * b.inv_mass

        # 2. Velocity Impulse (The Bounce)
        # Calculate relative velocity
        rv = b.vel - a.vel

        # Velocity along normal
        vel_along_normal = rv.x * self.normal.x + rv.y * self.normal.y

        # Do not resolve if velocities are separating
        if vel_along_normal > 0:
            return

        # Calculate restitution (bounciness) - use the lower of the two
        e = min(a.material.restitution, b.material.restitution)

        # Calculate impulse scalar
        j = -(1 + e) * vel_along_normal
        j /= total_inv_mass

        # Apply impulse
        impulse = self.normal * j

        if not a.static:
            a.vel -= impulse * a.inv_mass
        if not b.static:
            b.vel += impulse * b.inv_mass

        # 3. Friction (Optional but good)
        # Tangent vector is perpendicular to normal
        tangent = (rv - (self.normal * vel_along_normal)).normalize()
        jt = -(rv.x * tangent.x + rv.y * tangent.y)
        jt /= total_inv_mass

        # Don't apply tiny friction
        if abs(jt) < 0.001:
            return

        # Coulomb's Law
        mu = math.sqrt(a.material.friction * b.material.friction)
        friction_impulse = tangent * max(-j * mu, min(j * mu, jt))

        if not a.static:
            a.vel -= friction_impulse * a.inv_mass
        if not b.static:
            b.vel += friction_impulse * b.inv_mass

    # --- Specific Solvers ---


@solver(CircleCollider, CircleCollider)
def circle_to_circle(a: Body, b: Body) -> Collision | None:
    ra = cast(CircleCollider, a.collider).radius
    rb = cast(CircleCollider, b.collider).radius

    # Vector from A to B
    n = b.pos - a.pos
    dist_sq = n.x**2 + n.y**2
    r_sum = ra + rb

    if dist_sq > r_sum * r_sum:
        return None

    dist = math.sqrt(dist_sq)
    if dist == 0:
        return Collision(a, b, Point(1, 0), r_sum)  # Overlap exact

    return Collision(a, b, n / dist, r_sum - dist)


@solver(CircleCollider, BoxCollider)
def circle_to_box(circ: Body, box: Body) -> Collision | None:
    # AABB logic for box (assumes box is not rotated for V1)
    # Clamp circle center to box bounds

    # Half-extents
    hw = cast(BoxCollider, box.collider).width / 2
    hh = cast(BoxCollider, box.collider).height / 2

    bx = box.pos.x
    by = box.pos.y

    cx = circ.pos.x
    cy = circ.pos.y

    closest_x = max(bx - hw, min(cx, bx + hw))
    closest_y = max(by - hh, min(cy, by + hh))

    dist_x = cx - closest_x
    dist_y = cy - closest_y
    dist_sq = dist_x**2 + dist_y**2

    if dist_sq > cast(CircleCollider, circ.collider).radius ** 2:
        return None

    dist = math.sqrt(dist_sq)

    # If center is inside box (dist == 0)
    if dist == 0:
        # Push out along nearest axis (Simplified)
        # Assuming we usually hit top of floor:
        return Collision(
            circ, box, Point(0, -1), cast(CircleCollider, circ.collider).radius
        )

    # Normal points from A (Circle) to B (Box)?
    # Logic in resolve assumes Normal points A -> B.
    # Here vector is Closest -> Center (Box to Circle).
    # So Closest->Center is B->A.
    # We want A->B, so Center->Closest.

    normal = Point(-dist_x / dist, -dist_y / dist)
    return Collision(
        circ, box, normal, cast(CircleCollider, circ.collider).radius - dist
    )
