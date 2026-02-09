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

        correction = max(self.depth - 0.01, 0.0) / total_inv_mass * 0.5
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
        # J = -(1+e) * V_rel / (1/ma + 1/mb + (ra x n)^2 / Ia + (rb x n)^2 / Ib)

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

        # Solve for tangent impulse Jt
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

        # Coulomb's Law
        mu = math.sqrt(a.material.friction * b.material.friction)

        max_j = j * mu
        if abs(jt) > max_j:
            friction_impulse = t * (max_j * (1 if jt > 0 else -1))
        else:
            friction_impulse = t * jt

        self._apply_impulse(friction_impulse, ra, rb)

    def _apply_impulse(self, impulse: Point, ra: Point, rb: Point):
        a, b = self.a, self.b

        # Linear
        if not a.static:
            a.vel -= impulse * a.inv_mass
        if not b.static:
            b.vel += impulse * b.inv_mass

        # Angular: Torque = r x F
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

    # 3. Calculate World Normal & Depth
    dist = math.sqrt(dist_sq)
    if dist == 0:
        # Deep penetration fallback (Local Up)
        local_n = Point(0, -1)
        depth = r
    else:
        local_n = Point(dx / dist, dy / dist)
        depth = r - dist

    # Rotate Normal to World (Box Frame -> World)
    # Note: local_n points Box->Circle. This matches A->B convention?
    # Wait, solver(Circle, Box) means A=Circle, B=Box.
    # We want Normal A->B (Circle->Box).
    # current local_n is Box->Circle. So we negate.
    local_n = local_n * -1

    cos_w, sin_w = math.cos(box_rot), math.sin(box_rot)
    nx = local_n.x * cos_w - local_n.y * sin_w
    ny = local_n.x * sin_w + local_n.y * cos_w

    # 4. Calculate World Contact Point
    # Transform closest box point (cx, cy) to world
    wx = cx * cos_w - cy * sin_w
    wy = cx * sin_w + cy * cos_w
    contact = box.pos + Point(wx, wy)

    return Collision(circ, box, Point(nx, ny), depth, contact)


@solver(BoxCollider, BoxCollider)
def box_to_box(a: Body, b: Body) -> Collision | None:
    verts_a = _get_box_vertices(a)
    verts_b = _get_box_vertices(b)

    # SAT: Check all axes
    axes = _get_axes(verts_a) + _get_axes(verts_b)

    min_overlap = float("inf")
    best_axis = Point(0, 0)

    for axis in axes:
        min_a, max_a = _project(verts_a, axis)
        min_b, max_b = _project(verts_b, axis)

        if max_a < min_b or max_b < min_a:
            return None  # Gap found

        overlap = min(max_a, max_b) - max(min_a, min_b)
        if overlap < min_overlap:
            min_overlap = overlap
            best_axis = axis

    # Correct Normal Direction: Must point A -> B
    direction = b.pos - a.pos
    if direction.x * best_axis.x + direction.y * best_axis.y < 0:
        best_axis = best_axis * -1

    # --- FIND CONTACT POINT (Deepest Vertex) ---
    # 1. Identify "Incident" Body (The one pushing INTO the other)
    # We check which vertices of B are most opposed to the Normal (deepest in A)
    # Or which vertices of A are most along the Normal (deepest in B)
    # Since Normal is A->B, we look for vertex of A most along Normal?
    # Actually, easiest heuristic:
    # Find vertex of A closest to B's center? No.
    # Find vertex of A with Max projection along Normal?
    # Find vertex of B with Min projection along Normal?

    # Let's check both sets and pick the one that is actually inside.
    # Or simpler: The "Support Point" is the vertex furthest along the separation direction.

    # Vertices of B with Min projection along Normal (Deepest into A)
    min_proj_b = float("inf")
    best_vert_b = verts_b[0]
    for v in verts_b:
        proj = v.x * best_axis.x + v.y * best_axis.y
        if proj < min_proj_b:
            min_proj_b = proj
            best_vert_b = v

    # Vertices of A with Max projection along Normal (Deepest into B)
    max_proj_a = float("-inf")
    best_vert_a = verts_a[0]
    for v in verts_a:
        proj = v.x * best_axis.x + v.y * best_axis.y
        if proj > max_proj_a:
            max_proj_a = proj
            best_vert_a = v

    # Which penetration is significant?
    # Usually we pick the vertex from the "Incident Face".
    # For V1, we simply return the midpoint of these two "deepest" candidates
    # OR simpler: pick 'best_vert_b' (Vertex of B penetrating A).
    # Since Normal is A->B, B is being pushed away. The vertex of B "furthest back"
    # is the one penetrating most.

    contact = best_vert_b

    return Collision(a, b, best_axis, min_overlap, contact)
