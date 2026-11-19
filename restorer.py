# -*- coding: utf-8 -*-
"""Apply a saved expansion state to the QGIS layer tree."""

from __future__ import annotations

from qgis.core import QgsLayerTreeGroup

from .state import ExpansionState, GroupPath


def _find_group(root: QgsLayerTreeGroup, path: GroupPath):
    current = root
    for name, occurrence in path:
        matches = [
            child
            for child in current.children()
            if isinstance(child, QgsLayerTreeGroup) and child.name() == name
        ]
        if occurrence >= len(matches):
            return None
        current = matches[occurrence]
    return current


def apply_expansion_state(root: QgsLayerTreeGroup, state: ExpansionState) -> int:
    """Apply saved expansion state and return the number of changed nodes."""

    changed = 0
    for layer_id, expanded in state.layers.items():
        node = root.findLayer(layer_id)
        if node is not None and node.isExpanded() != expanded:
            node.setExpanded(expanded)
            changed += 1

    # Children first, parents last, so every parent's saved state is final.
    for path, expanded in sorted(
        state.groups.items(), key=lambda item: len(item[0]), reverse=True
    ):
        group = _find_group(root, path)
        if group is not None and group.isExpanded() != expanded:
            group.setExpanded(expanded)
            changed += 1

    return changed
