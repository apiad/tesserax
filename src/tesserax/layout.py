from abc import abstractmethod
from collections import defaultdict
import math
from typing import Literal, Self
from .core import Shape, Bounds
from .base import Group


class Layout(Group):
    def __init__(self, shapes: list[Shape] | None = None) -> None:
        super().__init__(shapes)

    @abstractmethod
    def do_layout(self) -> None:
        """
        Implementation must iterate over self.shapes, RESET their transforms,
        and then apply new translations.
        """
        ...

    def add(self, *shapes: Shape) -> "Layout":
        super().add(*shapes)
        self.do_layout()
        return self


type Align = Literal["start", "middle", "end"]


class Row(Layout):
    def __init__(
        self,
        shapes: list[Shape] | None = None,
        align: Align = "middle",
        gap: float = 0,
    ) -> None:
        self.align = align
        self.gap = gap
        super().__init__(shapes)

    def do_layout(self) -> None:
        if not self.shapes:
            return

        # 1. First pass: Reset transforms so we get pure local bounds
        for s in self.shapes:
            s.transform.reset()

        # 2. Calculate offsets based on the 'clean' shapes
        max_h = max(s.local().height for s in self.shapes)
        current_x = 0.0

        for shape in self.shapes:
            b = shape.local()

            # Calculate Y based on baseline
            match self.align:
                case "start":
                    dy = -b.y
                case "middle":
                    dy = (max_h / 2) - (b.y + b.height / 2)
                case "end":
                    dy = max_h - (b.y + b.height)
                case _:
                    dy = 0

            # 3. Apply the strict layout position
            shape.transform.tx = current_x - b.x
            shape.transform.ty = dy

            current_x += b.width + self.gap


class Column(Row):
    def __init__(
        self,
        shapes: list[Shape] | None = None,
        align: Align = "middle",
        gap: float = 0,
    ) -> None:
        super().__init__(shapes, align, gap)

    def do_layout(self) -> None:
        if not self.shapes:
            return

        for s in self.shapes:
            s.transform.reset()

        max_w = max(s.local().width for s in self.shapes)
        current_y = 0.0

        for shape in self.shapes:
            b = shape.local()

            match self.align:
                case "start":
                    dx = -b.x
                case "end":
                    dx = max_w - (b.x + b.width)
                case "middle":
                    dx = (max_w / 2) - (b.x + b.width / 2)
                case _:
                    dx = 0

            shape.transform.tx = dx
            shape.transform.ty = current_y - b.y

            current_y += b.height + self.gap


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


class HierarchicalLayout(Layout):
    """
    Arranges nodes in distinct layers based on directed connections.
    Supports both Vertical (Top-Bottom) and Horizontal (Left-Right) flows.
    """

    def __init__(
        self,
        shapes: list[Shape] | None = None,
        roots: list[Shape] | None = None,
        rank_sep: float = 50.0,
        node_sep: float = 20.0,
        orientation: Literal["vertical", "horizontal"] = "vertical",
    ) -> None:
        super().__init__(shapes)
        self.rank_sep = rank_sep
        self.node_sep = node_sep
        self.orientation = orientation
        self.roots = set(roots or [])
        self.adj: dict[Shape, list[Shape]] = defaultdict(list)
        self.rev_adj: dict[Shape, list[Shape]] = defaultdict(list)

    def root(self, n: Shape) -> Self:
        self.roots.add(n)
        return self

    def connect(self, u: Shape, v: Shape) -> Self:
        """Defines a directed dependency u -> v."""
        self.adj[u].append(v)
        self.rev_adj[v].append(u)
        return self

    def do_layout(self) -> None:
        if not self.shapes:
            return

        # 1. Ranking Phase: Assign layers (ignoring back-edges)
        ranks = self._assign_ranks()

        layers: dict[int, list[Shape]] = defaultdict(list)
        for s, r in ranks.items():
            layers[r].append(s)

        max_rank = max(layers.keys()) if layers else 0

        # 2. Ordering Phase: Minimize crossings (Barycenter Method)
        for r in range(1, max_rank + 1):
            layers[r].sort(key=lambda node: self._barycenter(node, layers[r - 1]))

        # 3. Positioning Phase: Assign physical coordinates
        # 'current_flow' tracks the position along the main axis (Y for vert, X for horz)
        current_flow = 0.0

        for r in sorted(layers.keys()):
            layer = layers[r]

            # Reset transforms to get clean local bounds
            for s in layer:
                s.transform.reset()

            # Calculate metrics for centering this layer
            if self.orientation == "horizontal":
                # In horizontal, 'breadth' is the height of the nodes
                breadths = [s.local().height for s in layer]
                # 'depth' is the width of the nodes (rank thickness)
                depths = [s.local().width for s in layer]
            else:
                # In vertical, 'breadth' is the width of the nodes
                breadths = [s.local().width for s in layer]
                # 'depth' is the height of the nodes (rank thickness)
                depths = [s.local().height for s in layer]

            # Center the layer along the cross-axis
            total_breadth = sum(breadths) + self.node_sep * (len(layer) - 1)
            current_cross = -total_breadth / 2

            # The thickness of this rank is determined by the tallest/widest node
            max_depth_in_rank = 0.0

            for i, s in enumerate(layer):
                b = s.local()

                if self.orientation == "horizontal":
                    # Flow is X, Cross is Y
                    # Align Left edge to current_flow
                    s.transform.tx = current_flow - b.x
                    # Align Top edge to current_cross
                    s.transform.ty = current_cross - b.y

                    max_depth_in_rank = max(max_depth_in_rank, b.width)
                    current_cross += b.height + self.node_sep
                else:
                    # Flow is Y, Cross is X
                    # Align Left edge to current_cross
                    s.transform.tx = current_cross - b.x
                    # Align Top edge to current_flow
                    s.transform.ty = current_flow - b.y

                    max_depth_in_rank = max(max_depth_in_rank, b.height)
                    current_cross += b.width + self.node_sep

            # Advance the main flow axis
            current_flow += max_depth_in_rank + self.rank_sep

    def _assign_ranks(self) -> dict[Shape, int]:
        """
        Computes the layer index for each node using DFS.
        Detects back-edges (cycles) and ignores them for rank calculation.
        """
        ranks: dict[Shape, int] = {}
        visiting = set()

        def get_rank(node: Shape) -> int:
            if node in ranks:
                return ranks[node]

            # Cycle detection: We are currently visiting this node's descendant
            if node in visiting:
                return -1  # Signal to ignore this parent

            visiting.add(node)

            parents = self.rev_adj[node]
            if not parents:
                r = 0
            else:
                parent_ranks = [get_rank(p) for p in parents]
                # Filter out back-edges (-1s)
                valid_ranks = [pr for pr in parent_ranks if pr != -1]
                # If all parents were back-edges, treat as root (0)
                r = 1 + max(valid_ranks, default=-1)

            visiting.remove(node)
            ranks[node] = r
            return r

        for r in self.roots:
            ranks[r] = 0

        for s in self.shapes:
            get_rank(s)

        return ranks

    def _barycenter(self, node: Shape, prev_layer: list[Shape]) -> float:
        parents = [p for p in self.rev_adj[node] if p in prev_layer]
        if not parents:
            return 0.0
        indices = [prev_layer.index(p) for p in parents]
        return sum(indices) / len(indices)
