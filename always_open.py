# -*- coding: utf-8 -*-
"""Provide the optional always-open group policy and its context menu."""

from __future__ import annotations

from typing import Iterator

from qgis.PyQt.QtGui import QActionGroup
from qgis.core import QgsApplication, QgsLayerTreeGroup, QgsProject


ALWAYS_OPEN_PROPERTY = "lcaxs/alwaysOpen"
MENU_TITLE = "L.C.a.X.s."


def _groups_below(group: QgsLayerTreeGroup) -> Iterator[QgsLayerTreeGroup]:
    for child in group.children():
        if isinstance(child, QgsLayerTreeGroup):
            yield child
            yield from _groups_below(child)


def _property_is_true(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def group_is_always_open(group: QgsLayerTreeGroup) -> bool:
    """Return whether a group has the persistent always-open override."""

    return _property_is_true(group.customProperty(ALWAYS_OPEN_PROPERTY, False))


def _expand_group_and_ancestors(
    group: QgsLayerTreeGroup, root: QgsLayerTreeGroup
) -> int:
    changed = 0
    current = group
    while isinstance(current, QgsLayerTreeGroup) and current is not root:
        if not current.isExpanded():
            current.setExpanded(True)
            changed += 1
        current = current.parent()
    return changed


def apply_always_open(root: QgsLayerTreeGroup) -> int:
    """Open opted-in groups and their ancestors, returning changed node count."""

    changed = 0
    for group in _groups_below(root):
        if group_is_always_open(group):
            changed += _expand_group_and_ancestors(group, root)
    return changed


class AlwaysOpenFeature:
    """Manage the always-open policy and its layer-tree context menu."""

    def __init__(self, iface):
        self.iface = iface
        self._connected = False

    def connect(self):
        """Add the group context-menu hook."""

        if self._connected:
            return
        self.iface.layerTreeView().contextMenuAboutToShow.connect(
            self._populate_context_menu
        )
        self._connected = True

    def disconnect(self):
        """Remove the group context-menu hook."""

        if not self._connected:
            return
        try:
            self.iface.layerTreeView().contextMenuAboutToShow.disconnect(
                self._populate_context_menu
            )
        except (TypeError, RuntimeError):
            pass
        self._connected = False

    @staticmethod
    def apply(root: QgsLayerTreeGroup) -> int:
        """Apply all persisted always-open overrides."""

        return apply_always_open(root)

    def _populate_context_menu(self, menu):
        node = self.iface.layerTreeView().currentNode()
        if not isinstance(node, QgsLayerTreeGroup):
            return

        menu.addSeparator()
        submenu = menu.addMenu(MENU_TITLE)
        choices = QActionGroup(submenu)
        choices.setExclusive(True)

        always_open = submenu.addAction(self._text("常に開く", "Always open"))
        follow_saved = submenu.addAction(
            self._text("保存状態に従う", "Follow saved state")
        )
        for action in (always_open, follow_saved):
            action.setCheckable(True)
            choices.addAction(action)

        enabled = group_is_always_open(node)
        always_open.setChecked(enabled)
        follow_saved.setChecked(not enabled)
        always_open.triggered.connect(
            lambda checked, group=node: self._set_always_open(group, checked)
        )
        follow_saved.triggered.connect(
            lambda checked, group=node: self._set_always_open(group, not checked)
        )

    @staticmethod
    def _set_always_open(group: QgsLayerTreeGroup, enabled: bool):
        if enabled:
            group.setCustomProperty(ALWAYS_OPEN_PROPERTY, True)
            _expand_group_and_ancestors(group, QgsProject.instance().layerTreeRoot())
        else:
            group.removeCustomProperty(ALWAYS_OPEN_PROPERTY)
        # Changing the policy is an explicit project edit and must be saved.
        QgsProject.instance().setDirty(True)

    @staticmethod
    def _text(japanese: str, english: str) -> str:
        return japanese if QgsApplication.locale().lower().startswith("ja") else english
