# -*- coding: utf-8 -*-
"""Restore the Layers panel expansion state after project loading."""

from __future__ import annotations

import os
from typing import Iterator, Optional
import zipfile

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QActionGroup
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsLayerTreeGroup,
    QgsMessageLog,
    QgsProject,
)

from .state import ExpansionState, GroupPath, state_from_project_file, state_from_qdom


PLUGIN_NAME = "L.C.a.X.s."
ALWAYS_OPEN_PROPERTY = "lcaxs/alwaysOpen"


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


class LcaxsPlugin:
    """Lifecycle object loaded by QGIS."""

    def __init__(self, iface):
        self.iface = iface
        self._pending_state: Optional[ExpansionState] = None
        self._timer = QTimer(iface.mainWindow())
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._restore_pending_state)
        self._connected = False

    def initGui(self):  # noqa: N802 - QGIS requires this name
        """Connect project-load signals and the group context menu."""

        project = QgsProject.instance()
        project.readProject.connect(self._capture_project_state)
        self.iface.projectRead.connect(self._project_loaded)
        self.iface.layerTreeView().contextMenuAboutToShow.connect(
            self._populate_context_menu
        )
        self._connected = True

        # Covers enabling the plugin after a project has already been opened.
        if project.fileName():
            self._load_current_project_file()
            self._schedule_restore()

    def unload(self):
        """Disconnect signals and cancel a queued restoration."""

        self._timer.stop()
        if self._connected:
            project = QgsProject.instance()
            try:
                project.readProject.disconnect(self._capture_project_state)
            except (TypeError, RuntimeError):
                pass
            try:
                self.iface.projectRead.disconnect(self._project_loaded)
            except (TypeError, RuntimeError):
                pass
            try:
                self.iface.layerTreeView().contextMenuAboutToShow.disconnect(
                    self._populate_context_menu
                )
            except (TypeError, RuntimeError):
                pass
        try:
            self._timer.timeout.disconnect(self._restore_pending_state)
        except (TypeError, RuntimeError):
            pass
        self._pending_state = None
        self._connected = False

    def _capture_project_state(self, document):
        try:
            self._pending_state = state_from_qdom(document)
        except (AttributeError, TypeError, ValueError) as error:
            self._pending_state = None
            self._log_warning("Could not read the project layer-tree state", error)

    def _project_loaded(self):
        # QGIS emits iface.projectRead after it has selected the first layer.
        if self._pending_state is None:
            self._load_current_project_file()
        self._schedule_restore()

    def _load_current_project_file(self):
        path = QgsProject.instance().fileName()
        if not path or not os.path.isfile(path):
            return
        try:
            self._pending_state = state_from_project_file(path)
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            self._pending_state = None
            self._log_warning("Could not read the saved project file", error)

    def _schedule_restore(self):
        # Run after every synchronous projectRead handler has finished.
        self._timer.start(0)

    def _restore_pending_state(self):
        state = self._pending_state
        self._pending_state = None
        project = QgsProject.instance()
        # This is a UI restoration, not a project edit. Keep QGIS from showing
        # a save prompt solely because the panel state was put back.
        with QgsProject.blockDirtying(project):
            root = project.layerTreeRoot()
            if state is not None and not state.is_empty():
                apply_expansion_state(root, state)
            apply_always_open(root)

    def _populate_context_menu(self, menu):
        node = self.iface.layerTreeView().currentNode()
        if not isinstance(node, QgsLayerTreeGroup):
            return

        menu.addSeparator()
        submenu = menu.addMenu("L.C.a.X.s.")
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

    def _set_always_open(self, group: QgsLayerTreeGroup, enabled: bool):
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

    @staticmethod
    def _log_warning(message: str, error: Exception):
        QgsMessageLog.logMessage(
            f"{message}: {error}",
            PLUGIN_NAME,
            Qgis.MessageLevel.Warning,
        )
