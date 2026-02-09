from tesserax.animation import Animation, Parallel, KeyframeAnimation
from .core import Body
from .forces import Field
from .constraints import Constraint
from .collisions import Collision


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

    def simulate(self, duration: float, dt: float = 0.01) -> Animation:
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

        # 3. Bake
        anims = []
        for b, props in tracks.items():
            anims.append(
                KeyframeAnimation(
                    b.shape,
                    tx=props["tx"],
                    ty=props["ty"],
                    rotation=props["rotation"],  # This maps to transform.rotation
                )
            )

        return Parallel(*anims)

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
