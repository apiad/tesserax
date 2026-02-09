from abc import abstractmethod
from collections import defaultdict
import math
from typing import Literal, Self
from .core import Anchor, Shape, Bounds
from .base import Group


class Layout(Group):
    def __init__(self, shapes: list[Shape] | None = None) -> None:
        super().__init__(shapes)
        self.do_layout()

    @abstractmethod
    def do_layout(self) -> None:
        """
        Implementation must iterate over self.shapes, RESET their transforms,
        and then apply new translations.
        """
        ...

    def add(
        self, *shapes: Shape, mode: Literal["strict", "loose"] = "strict"
    ) -> "Layout":
        super().add(*shapes, mode=mode)
        self.do_layout()
        return self


type Align = Literal["start", "middle", "end"]


class RowLayout(Layout):
    def __init__(
        self,
        shapes: list[Shape] | None = None,
        align: Align = "middle",
        gap: float = 0.0,
        width: float | None = None,
        mode: Literal["tight", "space-between", "space-around"] = "tight",
    ) -> None:
        self.align_mode = align
        self.gap = gap
        self.width = width
        self.mode = mode
        super().__init__(shapes)

    def do_layout(self) -> None:
        # Map Row's 'align' terminology to the Group's 'anchor' terminology
        anchor_map: dict[Align, Anchor] = {
            "start": "top",
            "middle": "center",
            "end": "bottom",
        }

        # 1. Distribute along the flow axis (X)
        self.distribute(
            axis="horizontal", size=self.width, mode=self.mode, gap=self.gap
        )

        # 2. Align along the cross axis (Y)
        self.align(axis="vertical", anchor=anchor_map[self.align_mode])


class ColumnLayout(Layout):
    def __init__(
        self,
        shapes: list[Shape] | None = None,
        align: Align = "middle",
        gap: float = 0.0,
        height: float | None = None,
        mode: Literal["tight", "space-between", "space-around"] = "tight",
    ) -> None:
        self.align_mode = align
        self.gap = gap
        self.height = height
        self.mode = mode
        super().__init__(shapes)

    def do_layout(self) -> None:
        anchor_map: dict[Align, Anchor] = {
            "start": "left",
            "middle": "center",
            "end": "right",
        }

        # 1. Distribute along the flow axis (Y)
        self.distribute(axis="vertical", size=self.height, mode=self.mode, gap=self.gap)

        # 2. Align along the cross axis (X)
        self.align(axis="horizontal", anchor=anchor_map[self.align_mode])


class GridLayout(Layout):
    def __init__(
        self,
        shapes: list[Shape] | None = None,
        cols: int = 1,
        gap: float | tuple[float, float] = 0.0,
        halign: Align = "middle",
        valign: Align = "middle",
    ) -> None:
        self.cols = cols
        self.gap = gap if isinstance(gap, tuple) else (gap, gap)
        self.halign = halign
        self.valign = valign
        super().__init__(shapes)

    def do_layout(self) -> None:
        if not self.shapes:
            return

        # 1. Matrix Organization
        # Split shapes into rows of length self.cols
        rows = [
            self.shapes[i : i + self.cols]
            for i in range(0, len(self.shapes), self.cols)
        ]

        # 2. Measure Tracks (Intrinsic Sizing)
        # col_widths[c] = max width of any shape in column c
        col_widths = [0.0] * self.cols
        # row_heights[r] = max height of any shape in row r
        row_heights = [0.0] * len(rows)

        for r, row_shapes in enumerate(rows):
            for c, shape in enumerate(row_shapes):
                # Reset transform to get intrinsic bounds
                shape.transform.reset()
                b = shape.local()
                col_widths[c] = max(col_widths[c], b.width)
                row_heights[r] = max(row_heights[r], b.height)

        # 3. Calculate Cell Positions
        # cum_x[c] is the starting X coordinate of column c
        cum_x = [0.0]
        for w in col_widths[:-1]:
            cum_x.append(cum_x[-1] + w + self.gap[0])

        # cum_y[r] is the starting Y coordinate of row r
        cum_y = [0.0]
        for h in row_heights[:-1]:
            cum_y.append(cum_y[-1] + h + self.gap[1])

        # 4. Position and Align Shapes
        # We need a map to convert user's "align" (e.g. "center")
        # to the specific point on the shape/cell bounds.
        # Simple approach: Calculate cell box, use shape.align_to(cell_box) logic.

        for r, row_shapes in enumerate(rows):
            for c, shape in enumerate(row_shapes):
                # Define the cell's rigid boundary
                cell_x = cum_x[c]
                cell_y = cum_y[r]
                cell_w = col_widths[c]
                cell_h = row_heights[r]

                # Current shape bounds (at 0,0)
                b = shape.local()

                # Calculate offsets within the cell based on alignment
                dx, dy = 0.0, 0.0

                # Horizontal Alignment
                if self.halign == "start":
                    dx = 0
                elif self.halign == "end":
                    dx = cell_w - b.width
                else:  # center/middle
                    dx = (cell_w - b.width) / 2

                # Vertical Alignment
                if self.valign == "start":
                    dy = 0
                elif self.valign == "end":
                    dy = cell_h - b.height
                else:  # center/middle
                    dy = (cell_h - b.height) / 2

                # Apply final translation (Cell Origin + Internal Alignment - Local Origin)
                # Note: b.x/b.y handles shapes not centered at 0,0 locally
                shape.transform.tx = cell_x + dx - b.x
                shape.transform.ty = cell_y + dy - b.y


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
        diameter: int = 100,
        k: float | None = None,
    ) -> None:
        super().__init__(shapes)
        self.connections: list[tuple[Shape, Shape]] = []
        self.iterations = iterations
        self.diameter = diameter
        self.k = k

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
        area = self.diameter * self.diameter
        k = self.k or math.sqrt(area / len(self.shapes))
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
