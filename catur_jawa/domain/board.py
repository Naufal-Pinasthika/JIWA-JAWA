from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from catur_jawa.domain.models import Node, PlayerSide


@dataclass(frozen=True, slots=True)
class Board:
    nodes: dict[str, Node]
    edges: frozenset[tuple[str, str]]
    promotion_nodes: dict[PlayerSide, frozenset[str]]
    initial_nodes: dict[PlayerSide, tuple[str, ...]]

    def neighbors(self, node_id: str) -> tuple[str, ...]:
        found: list[str] = []
        for a, b in self.edges:
            if a == node_id:
                found.append(b)
            elif b == node_id:
                found.append(a)
        return tuple(sorted(found))

    def has_edge(self, a: str, b: str) -> bool:
        return _edge(a, b) in self.edges

    def node(self, node_id: str) -> Node:
        return self.nodes[node_id]


def _edge(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def _is_between(a: Node, b: Node, c: Node) -> bool:
    cross = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
    if abs(cross) > 1e-9:
        return False
    return min(a.x, c.x) <= b.x <= max(a.x, c.x) and min(a.y, c.y) <= b.y <= max(a.y, c.y)


def _add_center_grid(nodes: dict[str, Node], edges: set[tuple[str, str]]) -> None:
    for x in range(5):
        for y in range(5):
            node_id = f"C{x}{y}"
            nodes[node_id] = Node(node_id, node_id, float(x), float(y))

    for x in range(5):
        for y in range(5):
            if x < 4:
                edges.add(_edge(f"C{x}{y}", f"C{x + 1}{y}"))
            if y < 4:
                edges.add(_edge(f"C{x}{y}", f"C{x}{y + 1}"))
            if x < 4 and y < 4:
                edges.add(_edge(f"C{x}{y}", f"C{x + 1}{y + 1}"))
                edges.add(_edge(f"C{x + 1}{y}", f"C{x}{y + 1}"))


def _add_wing(
    prefix: str,
    side_sign: int,
    center_attach: str,
    nodes: dict[str, Node],
    edges: set[tuple[str, str]],
) -> tuple[str, ...]:
    # Six wing intersections approximate the diagrams: three outer points,
    # two slanted-side midpoints, and one inner apex connected to the 5x5 arena.
    x0 = -3.0 if side_sign < 0 else 7.0
    x1 = -2.0 if side_sign < 0 else 6.0
    x2 = -1.0 if side_sign < 0 else 5.0
    wing_nodes = {
        f"{prefix}0": (x0, 1.0),
        f"{prefix}1": (x0, 2.0),
        f"{prefix}2": (x0, 3.0),
        f"{prefix}3": (x1, 1.5),
        f"{prefix}4": (x1, 2.5),
        f"{prefix}5": (x2, 2.0),
    }
    for node_id, (x, y) in wing_nodes.items():
        nodes[node_id] = Node(node_id, node_id, x, y)

    edges.update(
        {
            _edge(f"{prefix}0", f"{prefix}1"),
            _edge(f"{prefix}1", f"{prefix}2"),
            _edge(f"{prefix}0", f"{prefix}3"),
            _edge(f"{prefix}3", f"{prefix}5"),
            _edge(f"{prefix}2", f"{prefix}4"),
            _edge(f"{prefix}4", f"{prefix}5"),
            _edge(f"{prefix}1", f"{prefix}5"),
            _edge(f"{prefix}1", f"{prefix}3"),
            _edge(f"{prefix}1", f"{prefix}4"),
            _edge(f"{prefix}5", center_attach),
        }
    )
    return tuple(sorted(wing_nodes))


def create_standard_board() -> Board:
    nodes: dict[str, Node] = {}
    edges: set[tuple[str, str]] = set()
    _add_center_grid(nodes, edges)
    left_nodes = _add_wing("L", -1, "C02", nodes, edges)
    right_nodes = _add_wing("R", 1, "C42", nodes, edges)
    return Board(
        nodes=nodes,
        edges=frozenset(edges),
        promotion_nodes={
            PlayerSide.A: frozenset({"R0", "R1", "R2"}),
            PlayerSide.B: frozenset({"L0", "L1", "L2"}),
        },
        initial_nodes={
            PlayerSide.A: (*left_nodes, *(f"C{x}{y}" for x in (0, 1) for y in range(5))),
            PlayerSide.B: (*right_nodes, *(f"C{x}{y}" for x in (3, 4) for y in range(5))),
        },
    )


STANDARD_BOARD = create_standard_board()


def straight_landing_node(board: Board, source: str, jumped: str) -> str | None:
    a = board.node(source)
    b = board.node(jumped)
    dx = b.x - a.x
    dy = b.y - a.y
    target_x = b.x + dx
    target_y = b.y + dy
    for node in board.nodes.values():
        if abs(node.x - target_x) < 1e-9 and abs(node.y - target_y) < 1e-9:
            return node.id if board.has_edge(jumped, node.id) else None
    return None


def middle_node_on_line(board: Board, source: str, destination: str) -> str | None:
    a = board.node(source)
    c = board.node(destination)
    candidates = [
        b
        for b in board.nodes.values()
        if b.id not in {source, destination}
        and board.has_edge(source, b.id)
        and board.has_edge(b.id, destination)
        and _is_between(a, b, c)
    ]
    if len(candidates) != 1:
        return None
    return candidates[0].id


def validate_graph(board: Board = STANDARD_BOARD) -> None:
    for a, b in board.edges:
        if a not in board.nodes or b not in board.nodes:
            raise ValueError(f"Edge references unknown node: {a}-{b}")
    for a, b in combinations(board.nodes, 2):
        if _edge(a, b) in board.edges and _edge(b, a) not in board.edges:
            raise ValueError(f"Unsymmetrical edge: {a}-{b}")
