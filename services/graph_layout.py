from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LayoutNode:
    key: str
    layer: int
    index: int


def layered_positions(nodes: list[LayoutNode], x_gap: int = 200, y_gap: int = 90) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    by_layer: dict[int, list[LayoutNode]] = {}
    for node in nodes:
        by_layer.setdefault(node.layer, []).append(node)
    for layer, layer_nodes in by_layer.items():
        for idx, node in enumerate(layer_nodes):
            positions[node.key] = (layer * x_gap, idx * y_gap)
    return positions
