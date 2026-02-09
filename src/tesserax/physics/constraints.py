from abc import ABC, abstractmethod
from .core import Body


class Constraint(ABC):
    @abstractmethod
    def solve(self):
        """Apply forces or corrections to satisfy constraint."""
        pass


class Spring(Constraint):
    def __init__(
        self, a: Body, b: Body, length: float, k: float = 2.0, damping: float = 0.1
    ):
        self.a = a
        self.b = b
        self.rest_length = length
        self.stiffness = k
        self.damping = damping

    def solve(self):
        # 1. Vector from A to B
        delta = self.b.pos - self.a.pos
        dist = delta.magnitude()

        if dist == 0:
            return

        # 2. Hooke's Law: F = -k * (current_len - rest_len)
        force_mag = (dist - self.rest_length) * self.stiffness

        # 3. Damping (Resistance to velocity difference)
        # Project relative velocity onto the axis
        rel_vel = self.b.vel - self.a.vel
        normal = delta / dist
        vel_along_normal = rel_vel.x * normal.x + rel_vel.y * normal.y
        damping_force = vel_along_normal * self.damping

        total_force = force_mag + damping_force

        # Apply equal and opposite forces
        f_vector = normal * total_force

        self.a.apply_force(f_vector)
        self.b.apply_force(f_vector * -1)  # Newton's 3rd Law


class Rod(Constraint):
    """
    A hard constraint that keeps two bodies at a fixed distance.
    Solves using Position Correction (Jacobi/Gauss-Seidel style).
    """

    def __init__(self, a: Body, b: Body, length: float):
        self.a = a
        self.b = b
        self.length = length

    def solve(self):
        delta = self.b.pos - self.a.pos
        dist = delta.magnitude()
        if dist == 0:
            return

        # Error: How far are we from target length?
        error = dist - self.length

        # We want to move them to fix the error.
        # Move proportional to inverse mass (lighter objects move more).
        total_inv_mass = self.a.inv_mass + self.b.inv_mass
        if total_inv_mass == 0:
            return

        # Correction Vector
        correction = (delta / dist) * (error / total_inv_mass)

        if not self.a.static:
            self.a.pos += correction * self.a.inv_mass
            # Update velocity to prevent fighting next frame (optional but stable)
            # For simple position-based dynamics, we often ignore vel update or zero it along normal

        if not self.b.static:
            self.b.pos -= correction * self.b.inv_mass
