from dataclasses import dataclass
from tesserax.core import Shape, Point
from .colliders import Collider, BoxCollider, CircleCollider

@dataclass
class Material:
    density: float = 1.0
    restitution: float = 0.5
    friction: float = 0.3

class Body:
    def __init__(
        self,
        shape: Shape,
        collider: Collider | None = None,
        material: Material | None = None,
        static: bool = False
    ):
        self.shape = shape
        self.material = material or Material()
        self.static = static

        # Linear State
        self.pos = shape.bounds().center
        self.vel = Point(0, 0)
        self.acc = Point(0, 0) # Accumulator for forces

        # Angular State
        self.angle = shape.transform.rotation # Radians
        self.angular_vel = 0.0
        self.torque = 0.0 # Accumulator for rotational forces

        # Mass & Inertia Properties
        if static:
            self.inv_mass = 0.0
            self.inv_inertia = 0.0
        else:
            # 1. Mass = Density * Area
            # Approx area for mass calc
            b = shape.bounds()
            area = b.width * b.height
            mass = self.material.density * (area / 1000.0) # Scale down for pixels
            self.inv_mass = 1.0 / mass

            # 2. Moment of Inertia (Resistance to rotation)
            # For a box: m * (w^2 + h^2) / 12
            # For a circle: 0.5 * m * r^2
            if isinstance(collider, CircleCollider):
                inertia = 0.5 * mass * (collider.radius ** 2)
            else:
                # Default to Box inertia
                w, h = b.width, b.height
                inertia = mass * (w**2 + h**2) / 12.0

            self.inv_inertia = 1.0 / inertia

        # Collider
        self.collider = collider or BoxCollider(shape.bounds().width, shape.bounds().height)

    def apply_force(self, force: Point, point: Point | None = None):
        """
        Applies a force.
        If 'point' is provided (world space), it also applies Torque.
        """
        if self.static: return

        # Linear Acceleration (F = ma)
        self.acc += force * self.inv_mass

        # Angular Acceleration (Torque = r x F)
        if point:
            # r is vector from Center of Mass to point of application
            r = point - self.pos
            # Cross product in 2D is a scalar: r.x * F.y - r.y * F.x
            torque = r.x * force.y - r.y * force.x
            self.torque += torque

    def integrate(self, dt: float):
        if self.static: return

        # 1. Linear
        self.vel += self.acc * dt
        self.pos += self.vel * dt
        self.acc = Point(0, 0) # Reset accumulator

        # 2. Angular
        angular_acc = self.torque * self.inv_inertia
        self.angular_vel += angular_acc * dt
        self.angle += self.angular_vel * dt
        self.torque = 0.0 # Reset accumulator

        # 3. Sync Visuals (Optional, mostly handled by Baker)
        # self.shape.transform.rotation = self.angle
        # self.shape.move_to(self.pos)