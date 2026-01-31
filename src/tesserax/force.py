import math
from typing import Self
from .core import Shape
from .layout import Layout


class ForceLayout(Layout):
    """
    A force-directed layout for graph visualization.

    Nodes are positioned using a physical simulation where connections act
    as springs (attraction) and all nodes repel each other (repulsion).
    """

    def __init__(
        self,
        shapes: list[Shape] | None = None,
        iterations: int = 100,
        k: float | None = None,
    ) -> None:
        super().__init__(shapes)
        self.connections: list[tuple[Shape, Shape]] = []
        self.iterations = iterations
        self.k_const = k

    def connect(self, u: Shape, v: Shape) -> Self:
        """
        Defines an undirected connection between two shapes.
        The layout will use this connection to apply attractive forces.
        """
        self.connections.append((u, v))
        return self

    def do_layout(self) -> None:
        """
        Executes the Fruchterman-Reingold force-directed simulation.
        """
        if not self.shapes:
            return

        # 1. Initialize positions in a circle to avoid overlapping origins
        for i, shape in enumerate(self.shapes):
            if shape.transform.tx == 0 and shape.transform.ty == 0:
                angle = (2 * math.pi * i) / len(self.shapes)
                shape.transform.tx = 100 * math.cos(angle)
                shape.transform.ty = 100 * math.sin(angle)

        # 2. Simulation parameters
        # k is the optimal distance between nodes
        area = 600 * 600
        k = self.k_const or math.sqrt(area / len(self.shapes))
        t = 100.0  # Temperature (max displacement per step)
        dt = t / self.iterations

        for _ in range(self.iterations):
            # Store displacement for each shape ID
            disp = {id(s): [0.0, 0.0] for s in self.shapes}

            # Repulsion Force (between all pairs)
            for i, v in enumerate(self.shapes):
                for j, u in enumerate(self.shapes):
                    if i == j:
                        continue

                    dx = v.transform.tx - u.transform.tx
                    dy = v.transform.ty - u.transform.ty
                    dist = math.sqrt(dx * dx + dy * dy) + 0.01

                    # fr(d) = k^2 / d
                    mag = (k * k) / dist
                    disp[id(v)][0] += (dx / dist) * mag
                    disp[id(v)][1] += (dy / dist) * mag

            # Attraction Force (only between connected nodes)
            for u, v in self.connections:
                dx = v.transform.tx - u.transform.tx
                dy = v.transform.ty - u.transform.ty
                dist = math.sqrt(dx * dx + dy * dy) + 0.01

                # fa(d) = d^2 / k
                mag = (dist * dist) / k
                fx, fy = (dx / dist) * mag, (dy / dist) * mag

                disp[id(v)][0] -= fx
                disp[id(v)][1] -= fy
                disp[id(u)][0] += fx
                disp[id(u)][1] += fy

            # Apply displacement limited by temperature
            for shape in self.shapes:
                dx, dy = disp[id(shape)]
                dist = math.sqrt(dx * dx + dy * dy) + 0.01

                shape.transform.tx += (dx / dist) * min(dist, t)
                shape.transform.ty += (dy / dist) * min(dist, t)

            # Cool the simulation
            t -= dt
