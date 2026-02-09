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
        percent = 0.8
        slop = 0.01
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
        # We really should include angular velocity here for rigid bodies:
        # V_p = V_cm + w x r
        # For now, simple linear impulse is okay for the V1 baking engine.
        rv = b.vel - a.vel

        vel_along_normal = rv.x * self.normal.x + rv.y * self.normal.y

        if vel_along_normal > 0:
            return

        e = min(a.material.restitution, b.material.restitution)

        j = -(1 + e) * vel_along_normal
        j /= total_inv_mass

        impulse = self.normal * j

        if not a.static:
            a.vel -= impulse * a.inv_mass
        if not b.static:
            b.vel += impulse * b.inv_mass

        # 3. Friction
        tangent = (rv - (self.normal * vel_along_normal)).normalize()
        jt = -(rv.x * tangent.x + rv.y * tangent.y)
        jt /= total_inv_mass

        if abs(jt) < 0.001:
            return

        mu = math.sqrt(a.material.friction * b.material.friction)
        friction_impulse = tangent * max(-j * mu, min(j * mu, jt))

        if not a.static:
            a.vel -= friction_impulse * a.inv_mass
        if not b.static:
            b.vel += friction_impulse * b.inv_mass


# --- SAT Helpers ---


def _get_box_vertices(b: Body) -> list[Point]:
    """Returns world-space vertices of the box collider."""
    box = cast(BoxCollider, b.collider)
    hw, hh = box.width / 2, box.height / 2

    # Local corners
    corners = [
        Point(-hw, -hh), Point(hw, -hh),
        Point(hw, hh), Point(-hw, hh)
    ]

    # Transform to world
    # We assume Body has 'rotation' (radians) and 'pos' (center)
    # If Body doesn't have rotation yet, assume 0
    rot = getattr(b, "rotation", 0.0)
    pos = b.pos

    world_corners = []
    cos_r = math.cos(rot)
    sin_r = math.sin(rot)

    for p in corners:
        # Rotate then Translate
        rx = p.x * cos_r - p.y * sin_r
        ry = p.x * sin_r + p.y * cos_r
        world_corners.append(Point(rx + pos.x, ry + pos.y))

    return world_corners


def _project_poly(vertices: list[Point], axis: Point) -> tuple[float, float]:
    """Projects vertices onto an axis and returns (min, max)."""
    min_p = float("inf")
    max_p = float("-inf")
    for v in vertices:
        proj = v.x * axis.x + v.y * axis.y
        if proj < min_p: min_p = proj
        if proj > max_p: max_p = proj
    return min_p, max_p


def _sat_check(verts_a: list[Point], verts_b: list[Point], axes: list[Point]) -> tuple[bool, float, Point]:
    """Returns (is_colliding, min_overlap, best_axis)."""
    min_overlap = float("inf")
    best_axis = Point(0, 0)

    for axis in axes:
        min_a, max_a = _project_poly(verts_a, axis)
        min_b, max_b = _project_poly(verts_b, axis)

        # Gap check
        if max_a < min_b or max_b < min_a:
            return False, 0.0, Point(0, 0)

        # Overlap
        overlap = min(max_a, max_b) - max(min_a, min_b)
        if overlap < min_overlap:
            min_overlap = overlap
            best_axis = axis

    return True, min_overlap, best_axis


def _get_box_axes(vertices: list[Point]) -> list[Point]:
    """Gets the 2 normal axes for a box."""
    # Edges: 0-1 and 1-2
    axes = []
    for i in range(2):
        p1 = vertices[i]
        p2 = vertices[i+1]
        edge = p2 - p1
        # Normal is (-y, x)
        axes.append(Point(-edge.y, edge.x).normalize())
    return axes


# --- Specific Solvers ---


@solver(CircleCollider, CircleCollider)
def circle_to_circle(a: Body, b: Body) -> Collision | None:
    ra = cast(CircleCollider, a.collider).radius
    rb = cast(CircleCollider, b.collider).radius

    n = b.pos - a.pos
    dist_sq = n.x**2 + n.y**2
    r_sum = ra + rb

    if dist_sq > r_sum * r_sum:
        return None

    dist = math.sqrt(dist_sq)
    if dist == 0:
        return Collision(a, b, Point(1, 0), r_sum)

    return Collision(a, b, n / dist, r_sum - dist)


@solver(BoxCollider, BoxCollider)
def box_to_box(a: Body, b: Body) -> Collision | None:
    verts_a = _get_box_vertices(a)
    verts_b = _get_box_vertices(b)

    # Axes: normals of A and normals of B
    axes = _get_box_axes(verts_a) + _get_box_axes(verts_b)

    is_hit, depth, axis = _sat_check(verts_a, verts_b, axes)
    if not is_hit:
        return None

    # Ensure normal points A -> B
    direction = b.pos - a.pos
    if direction.x * axis.x + direction.y * axis.y < 0:
        axis = axis * -1

    return Collision(a, b, axis, depth)


@solver(CircleCollider, BoxCollider)
def circle_to_box(circ: Body, box: Body) -> Collision | None:
    # Rotate Circle center into Box's local space to handle Box rotation
    box_rot = getattr(box, "rotation", 0.0)

    # Vector from Box center to Circle center
    rel = circ.pos - box.pos

    # Rotate backwards by box_rot
    cos_r = math.cos(-box_rot)
    sin_r = math.sin(-box_rot)
    local_cx = rel.x * cos_r - rel.y * sin_r
    local_cy = rel.x * sin_r + rel.y * cos_r

    # Box extents
    hw = cast(BoxCollider, box.collider).width / 2
    hh = cast(BoxCollider, box.collider).height / 2

    # Clamp in local space
    closest_local_x = max(-hw, min(local_cx, hw))
    closest_local_y = max(-hh, min(local_cy, hh))

    # Distance in local space
    dist_x = local_cx - closest_local_x
    dist_y = local_cy - closest_local_y
    dist_sq = dist_x**2 + dist_y**2

    if dist_sq > cast(CircleCollider, circ.collider).radius ** 2:
        return None

    # We have a collision.
    # We need the normal and depth in WORLD space.

    # If center is inside box
    if dist_sq == 0:
        # Push out along smallest local axis
        # (Simplified: assume Y is smallest penetration for floors)
        # For robustness, check min overlap to edges
        dist = 0
        normal_local = Point(0, -1)
        depth = cast(CircleCollider, circ.collider).radius # Approximation
    else:
        dist = math.sqrt(dist_sq)
        normal_local = Point(dist_x / dist, dist_y / dist) # Points Box -> Circle (B->A)
        depth = cast(CircleCollider, circ.collider).radius - dist

    # Rotate normal back to World space (rotate by +box_rot)
    # Note: normal_local is B->A. We want A->B (Circle->Box). So negate.
    normal_local = normal_local * -1

    cos_r = math.cos(box_rot)
    sin_r = math.sin(box_rot)

    world_nx = normal_local.x * cos_r - normal_local.y * sin_r
    world_ny = normal_local.x * sin_r + normal_local.y * cos_r

    return Collision(circ, box, Point(world_nx, world_ny), depth)
