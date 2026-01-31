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
    Ideal for trees, flowcharts, and dependency graphs.
    """

    def __init__(
        self,
        shapes: list[Shape] | None = None,
        rank_sep: float = 50.0,
        node_sep: float = 20.0,
        orientation: str = "vertical",  # vertical or horizontal
    ) -> None:
        super().__init__(shapes)
        self.rank_sep = rank_sep
        self.node_sep = node_sep
        self.orientation = orientation
        # Adjacency: u -> [v, ...] (parents -> children)
        self.adj: dict[Shape, list[Shape]] = defaultdict(list)
        # Reverse Adjacency: v -> [u, ...] (children -> parents)
        self.rev_adj: dict[Shape, list[Shape]] = defaultdict(list)

    def connect(self, u: Shape, v: Shape) -> Self:
        """Defines a directed dependency u -> v."""
        self.adj[u].append(v)
        self.rev_adj[v].append(u)
        return self

    def do_layout(self) -> None:
        if not self.shapes:
            return

        # 1. Ranking Phase: Assign layers
        ranks = self._assign_ranks()

        # Group shapes by rank: {0: [s1, s2], 1: [s3], ...}
        layers: dict[int, list[Shape]] = defaultdict(list)
        for s, r in ranks.items():
            layers[r].append(s)

        max_rank = max(layers.keys())

        # 2. Ordering Phase: Minimize crossings (Barycenter Method)
        # We sweep down from layer 1 to max_rank
        for r in range(1, max_rank + 1):
            layer = layers[r]
            # Sort nodes in this layer based on average position of parents
            layer.sort(key=lambda node: self._barycenter(node, layers[r - 1]))

        # 3. Positioning Phase: Assign physical coordinates
        current_y = 0.0

        for r in sorted(layers.keys()):
            layer = layers[r]

            # Reset transforms first
            for s in layer:
                s.transform.reset()

            # Calculate total width of this layer
            widths = [s.local().width for s in layer]
            total_w = sum(widths) + self.node_sep * (len(layer) - 1)

            # Start X position (centered)
            current_x = -total_w / 2

            max_h = 0.0

            for s in layer:
                b = s.local()
                s.transform.tx = current_x - b.x # Align left edge to current_x
                s.transform.ty = current_y - b.y

                current_x += b.width + self.node_sep
                max_h = max(max_h, b.height)

            current_y += max_h + self.rank_sep

    def _assign_ranks(self) -> dict[Shape, int]:
        """
        Computes the layer index for each node using DFS.
        Detects back-edges (cycles) and ignores them for rank calculation.
        """
        ranks: dict[Shape, int] = {}
        # Set of nodes currently in the recursion stack
        visiting = set()

        def get_rank(node: Shape) -> int:
            # Return memoized result if available
            if node in ranks:
                return ranks[node]

            # Cycle detection: if we see a node that is currently visiting,
            # this is a back-edge. We return -1 to signal "ignore this parent".
            if node in visiting:
                return -1

            visiting.add(node)

            parents = self.rev_adj[node]
            if not parents:
                # No parents -> Root node (Rank 0)
                r = 0
            else:
                # Recursively get ranks of all parents
                parent_ranks = [get_rank(p) for p in parents]

                # Filter out back-edges (which returned -1)
                valid_ranks = [pr for pr in parent_ranks if pr != -1]

                # Rank is 1 + max(parents).
                # If valid_ranks is empty (all parents were back-edges),
                # default to -1 so 1 + -1 = 0.
                r = 1 + max(valid_ranks, default=-1)

            visiting.remove(node)
            ranks[node] = r
            return r

        # Ensure all shapes are ranked, even disconnected components
        for s in self.shapes:
            get_rank(s)

        return ranks

    def _barycenter(self, node: Shape, prev_layer: list[Shape]) -> float:
        """
        Returns the average index of this node's parents in the previous layer.
        """
        parents = [p for p in self.rev_adj[node] if p in prev_layer]
        if not parents:
            # Keep original relative order if no parents
            return 0.0

        # Calculate average index of parents in the *previous layer's list*
        indices = [prev_layer.index(p) for p in parents]
        return sum(indices) / len(indices)
