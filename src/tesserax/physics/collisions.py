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
    normal: Point  # A -> B
    depth: float
    point: Point  # Contact Point in World Space

    @staticmethod
    def register(t1, t2, func):
        SOLVERS[(t1, t2)] = func
        SOLVERS[(t2, t1)] = lambda a, b: func(b, a)._flip() if func(b, a) else None

    def _flip(self) -> Collision:
        self.normal = self.normal * -1
        self.a, self.b = self.b, self.a
        return self

    @classmethod
    def solve(cls, a: Body, b: Body) -> Collision | None:
        t1, t2 = type(a.collider), type(b.collider)
        if s := SOLVERS.get((t1, t2)):
            return s(a, b)
        return None

    def resolve(self):
        """Applies Rigid Body Impulse with Friction."""
        a, b = self.a, self.b
        n = self.normal

        # 1. Positional Correction (Anti-Sinking)
        total_inv_mass = a.inv_mass + b.inv_mass
        if total_inv_mass == 0:
            return

        # Increased from 0.5 to 0.8 to reduce "mushiness"
        correction = max(self.depth - 0.01, 0.0) / total_inv_mass * 0.8
        move = n * correction
        if not a.static:
            a.pos -= move * a.inv_mass
        if not b.static:
            b.pos += move * b.inv_mass

        # 2. Lever Arms (Vector from Center to Contact Point)
        ra = self.point - a.pos
        rb = self.point - b.pos

        # 3. Relative Velocity at Contact Point
        # V_p = V_cm + (w x r)
        # 2D Cross scalar-vector: w x r = (-w*ry, w*rx)
        va = a.vel + Point(-a.angular_vel * ra.y, a.angular_vel * ra.x)
        vb = b.vel + Point(-b.angular_vel * rb.y, b.angular_vel * rb.x)

        rv = vb - va

        # Velocity along normal
        vel_along_normal = rv.x * n.x + rv.y * n.y
        if vel_along_normal > 0:
            return  # Separating

        # 4. Compute Impulse Scalar (J)
        raxn = ra.x * n.y - ra.y * n.x  # Cross product 2D (scalar)
        rbxn = rb.x * n.y - rb.y * n.x

        inv_mass_sum = (
            a.inv_mass
            + b.inv_mass
            + (raxn**2 * a.inv_inertia)
            + (rbxn**2 * b.inv_inertia)
        )

        e = min(a.material.restitution, b.material.restitution)
        j = -(1 + e) * vel_along_normal
        j /= inv_mass_sum

        impulse = n * j

        self._apply_impulse(impulse, ra, rb)

        # 5. Friction Impulse
        t = (rv - (n * vel_along_normal)).normalize()

        raxt = ra.x * t.y - ra.y * t.x
        rbxt = rb.x * t.y - rb.y * t.x
        inv_mass_sum_t = (
            a.inv_mass
            + b.inv_mass
            + (raxt**2 * a.inv_inertia)
            + (rbxt**2 * b.inv_inertia)
        )

        jt = -(rv.x * t.x + rv.y * t.y)
        jt /= inv_mass_sum_t

        mu = math.sqrt(a.material.friction * b.material.friction)

        max_j = j * mu
        if abs(jt) > max_j:
            friction_impulse = t * (max_j * (1 if jt > 0 else -1))
        else:
            friction_impulse = t * jt

        self._apply_impulse(friction_impulse, ra, rb)

    def _apply_impulse(self, impulse: Point, ra: Point, rb: Point):
        a, b = self.a, self.b

        if not a.static:
            a.vel -= impulse * a.inv_mass
        if not b.static:
            b.vel += impulse * b.inv_mass

        torque_a = ra.x * impulse.y - ra.y * impulse.x
        torque_b = rb.x * impulse.y - rb.y * impulse.x

        if not a.static:
            a.angular_vel -= torque_a * a.inv_inertia
        if not b.static:
            b.angular_vel += torque_b * b.inv_inertia


# --- Helpers ---


def _get_box_vertices(b: Body) -> list[Point]:
    box = cast(BoxCollider, b.collider)
    hw, hh = box.width / 2, box.height / 2
    corners = [Point(-hw, -hh), Point(hw, -hh), Point(hw, hh), Point(-hw, hh)]

    rot = getattr(b, "rotation", 0.0)
    pos = b.pos
    cos_r, sin_r = math.cos(rot), math.sin(rot)

    world_corners = []
    for p in corners:
        rx = p.x * cos_r - p.y * sin_r
        ry = p.x * sin_r + p.y * cos_r
        world_corners.append(Point(rx + pos.x, ry + pos.y))
    return world_corners


def _get_axes(verts: list[Point]) -> list[Point]:
    axes = []
    for i in range(len(verts)):
        p1 = verts[i]
        p2 = verts[(i + 1) % len(verts)]
        edge = p2 - p1
        axes.append(Point(-edge.y, edge.x).normalize())
    return axes


def _project(verts: list[Point], axis: Point) -> tuple[float, float]:
    min_p = float("inf")
    max_p = float("-inf")
    for v in verts:
        proj = v.x * axis.x + v.y * axis.y
        if proj < min_p:
            min_p = proj
        if proj > max_p:
            max_p = proj
    return min_p, max_p


# --- Solvers ---


@solver(CircleCollider, CircleCollider)
def circle_to_circle(a: Body, b: Body) -> Collision | None:
    n = b.pos - a.pos
    dist = n.magnitude()
    r = (
        cast(CircleCollider, a.collider).radius
        + cast(CircleCollider, b.collider).radius
    )

    if dist > r:
        return None

    normal = n.normalize() if dist > 0 else Point(1, 0)
    contact = a.pos + (normal * cast(CircleCollider, a.collider).radius)

    return Collision(a, b, normal, r - dist, contact)


@solver(CircleCollider, BoxCollider)
def circle_to_box(circ: Body, box: Body) -> Collision | None:
    # 1. Transform Circle to Box Local
    box_rot = getattr(box, "rotation", 0.0)
    rel = circ.pos - box.pos
    cos_r, sin_r = math.cos(-box_rot), math.sin(-box_rot)
    lx = rel.x * cos_r - rel.y * sin_r
    ly = rel.x * sin_r + rel.y * cos_r

    hw = cast(BoxCollider, box.collider).width / 2
    hh = cast(BoxCollider, box.collider).height / 2

    # 2. Closest Point on Box (Local)
    cx = max(-hw, min(lx, hw))
    cy = max(-hh, min(ly, hh))

    dx, dy = lx - cx, ly - cy
    dist_sq = dx**2 + dy**2
    r = cast(CircleCollider, circ.collider).radius

    if dist_sq > r**2:
        return None

    dist = math.sqrt(dist_sq)
    if dist == 0:
        local_n = Point(0, -1)
        depth = r
    else:
        local_n = Point(dx / dist, dy / dist)
        depth = r - dist

    # Rotate Normal to World
    # Note: local_n points Box->Circle. This matches A->B convention?
    # No, A=Circle, B=Box. We want A->B. Current is B->A.
    local_n = local_n * -1

    cos_w, sin_w = math.cos(box_rot), math.sin(box_rot)
    nx = local_n.x * cos_w - local_n.y * sin_w
    ny = local_n.x * sin_w + local_n.y * cos_w

    wx = cx * cos_w - cy * sin_w
    wy = cx * sin_w + cy * cos_w
    contact = box.pos + Point(wx, wy)

    return Collision(circ, box, Point(nx, ny), depth, contact)


@solver(BoxCollider, BoxCollider)
def box_to_box(a: Body, b: Body) -> Collision | None:
    verts_a = _get_box_vertices(a)
    verts_b = _get_box_vertices(b)

    axes_a = _get_axes(verts_a)
    axes_b = _get_axes(verts_b)
    all_axes = axes_a + axes_b

    min_overlap = float("inf")
    best_axis = Point(0, 0)

    # 1. SAT Check
    for axis in all_axes:
        min_a, max_a = _project(verts_a, axis)
        min_b, max_b = _project(verts_b, axis)

        if max_a < min_b or max_b < min_a:
            return None

        overlap = min(max_a, max_b) - max(min_a, min_b)
        if overlap < min_overlap:
            min_overlap = overlap
            best_axis = axis

    # 2. Correct Normal A -> B
    direction = b.pos - a.pos
    if direction.x * best_axis.x + direction.y * best_axis.y < 0:
        best_axis = best_axis * -1

    # 3. Identify Contact Point (Reference Face vs Incident Vertex)
    # The body with a face most perpendicular to the normal is the Reference.
    def get_max_axis_dot(axes, n):
        max_d = 0.0
        for ax in axes:
            d = abs(ax.x * n.x + ax.y * n.y)
            if d > max_d:
                max_d = d
        return max_d

    dot_a = get_max_axis_dot(axes_a, best_axis)
    dot_b = get_max_axis_dot(axes_b, best_axis)

    if dot_a > dot_b:
        # A is Reference (Flat Face), B is Incident (Corner)
        # Find B's vertex most opposite to Normal (deepest into A)
        candidates = verts_b
        best_v = candidates[0]
        min_d = float("inf")
        for v in candidates:
            d = v.x * best_axis.x + v.y * best_axis.y
            if d < min_d:
                min_d = d
                best_v = v
        contact = best_v
    else:
        # B is Reference (Flat Face), A is Incident (Corner)
        # Find A's vertex most along Normal (deepest into B)
        candidates = verts_a
        best_v = candidates[0]
        max_d = float("-inf")
        for v in candidates:
            d = v.x * best_axis.x + v.y * best_axis.y
            if d > max_d:
                max_d = d
                best_v = v
        contact = best_v

    return Collision(a, b, best_axis, min_overlap, contact)