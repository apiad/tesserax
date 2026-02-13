from tesserax.animation import Animation, Parallel, KeyframeAnimation
from tesserax.core import Bounds
from .core import Body
from .forces import Field
from .constraints import Constraint
from .collisions import Collision


class PhysicsAnimation(Parallel):
    def __init__(
        self, *animations: Animation, bounds: Bounds | None = None, **kwargs
    ) -> None:
        super().__init__(*animations, **kwargs)
        self.bounds = bounds


class World:
    def __init__(self):
        self.bodies: list[Body] = []
        self.fields: list[Field] = []
        self.constraints: list[Constraint] = []

    def add(self, shape, **kwargs) -> Body:
        b = Body(shape, **kwargs)
        self.bodies.append(b)
        return b

    def constraint(self, c: Constraint):
        self.constraints.append(c)
        return c

    def simulate(self, duration: float, dt: float = 0.01) -> PhysicsAnimation:
        steps = int(duration / dt)

        # Tracks now include 'rotation'
        tracks = {b: {"tx": {}, "ty": {}, "rotation": {}} for b in self.bodies}

        time = 0.0
        for _ in range(steps):
            t_norm = time / duration if duration > 0 else 0

            # 1. Record
            for b in self.bodies:
                tracks[b]["tx"][t_norm] = b.pos.x
                tracks[b]["ty"][t_norm] = b.pos.y
                tracks[b]["rotation"][t_norm] = b.rotation  # Radians

            # 2. Physics Step
            self._step(dt)
            time += dt

        # 3. Bake and Compute Bounds
        anims = []
        all_bounds = []

        for b, props in tracks.items():
            anims.append(
                KeyframeAnimation(
                    b.shape,
                    tx=props["tx"],
                    ty=props["ty"],
                    rotation=props["rotation"],  # This maps to transform.rotation
                )
            )

            # Compute approximate bounds for this body over the entire simulation
            # We assume the AABB of the shape + the min/max translations
            local = b.shape.local()
            tx_values = props["tx"].values()
            ty_values = props["ty"].values()

            if tx_values and ty_values:
                min_tx, max_tx = min(tx_values), max(tx_values)
                min_ty, max_ty = min(ty_values), max(ty_values)

                # Union of the shape at its min position and max position
                # This is a safe approximation for "camera fitting" purposes
                # (width/height remain constant in local space)
                b_bounds = Bounds(
                    x=min_tx + local.x,
                    y=min_ty + local.y,
                    width=(max_tx - min_tx) + local.width,
                    height=(max_ty - min_ty) + local.height,
                )
                all_bounds.append(b_bounds)

        total_bounds = Bounds.union(*all_bounds) if all_bounds else None

        return PhysicsAnimation(*anims, bounds=total_bounds)

    def _step(self, dt: float):
        # 1. Apply Fields (Gravity, Drag)
        for f in self.fields:
            f.apply(self.bodies)

        # 2. Solve Constraints (Springs apply forces)
        for c in self.constraints:
            c.solve()

        # 3. Integrate (Move objects)
        for b in self.bodies:
            b.integrate(dt)

        # 4. Resolve Collisions (Impulses)
        # Naive O(N^2) - Fine for < 100 objects
        count = len(self.bodies)
        for i in range(count):
            for j in range(i + 1, count):
                a = self.bodies[i]
                b = self.bodies[j]

                # Optimization: Don't check static vs static
                if a.static and b.static:
                    continue

                if col := Collision.solve(a, b):
                    col.resolve()
