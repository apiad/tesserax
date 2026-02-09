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
        mass: float = 1.0,
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
        self.acc = Point(0, 0)

        # Angular State
        self.rotation = getattr(shape.transform, "rotation", 0.0)
        self.angular_vel = 0.0
        self.torque = 0.0
        self.mass = mass

        # Mass & Inertia Properties
        if static:
            self.inv_mass = 0.0
            self.inv_inertia = 0.0
        else:
            # 1. Mass
            b = shape.bounds()
            self.inv_mass = 1.0 / self.mass

            # 2. Moment of Inertia
            # Box: m * (w^2 + h^2) / 12
            # Circle: 0.5 * m * r^2
            if isinstance(collider, CircleCollider):
                inertia = 0.5 * mass * (collider.radius ** 2)
            else:
                # Default to Box inertia
                w, h = b.width, b.height
                inertia = mass * (w**2 + h**2) / 12.0

            self.inv_inertia = 1.0 / inertia

        # Collider
        self.collider = collider or BoxCollider(shape.bounds().width, shape.bounds().height)

    def integrate(self, dt: float):
        if self.static: return

        # Linear
        self.vel += self.acc * dt
        self.pos += self.vel * dt
        self.acc = Point(0, 0)

        # Angular
        # alpha = Torque / Inertia
        angular_acc = self.torque * self.inv_inertia
        self.angular_vel += angular_acc * dt
        self.rotation += self.angular_vel * dt
        self.torque = 0.0

        # Angular Damping (Air resistance for spin)
        # This helps stop eternal spinning
        self.angular_vel *= 0.99

    def apply(self, force: Point):
        self.acc += force * self.mass
