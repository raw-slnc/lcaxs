# -*- coding: utf-8 -*-
"""Restore the Layers panel expansion state after project loading."""

from __future__ import annotations

import os
from typing import Optional
import zipfile

from qgis.PyQt.QtCore import QTimer
from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)

from .always_open import AlwaysOpenFeature
from .restorer import apply_expansion_state
from .state import ExpansionState, state_from_project_file, state_from_qdom


PLUGIN_NAME = "L.C.a.X.s."


class LcaxsPlugin:
    """Lifecycle object loaded by QGIS."""

    def __init__(self, iface):
        self.iface = iface
        self._pending_state: Optional[ExpansionState] = None
        self._timer = QTimer(iface.mainWindow())
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._restore_pending_state)
        self._always_open = AlwaysOpenFeature(iface)
        self._connected = False

    def initGui(self):  # noqa: N802 - QGIS requires this name
        """Connect project-load signals and the group context menu."""

        project = QgsProject.instance()
        project.readProject.connect(self._capture_project_state)
        self.iface.projectRead.connect(self._project_loaded)
        self._always_open.connect()
        self._connected = True

        # Covers enabling the plugin after a project has already been opened.
        if project.fileName():
            self._load_current_project_file()
            self._schedule_restore()

    def unload(self):
        """Disconnect signals and cancel a queued restoration."""

        self._timer.stop()
        self._always_open.disconnect()
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
            self._always_open.apply(root)

    @staticmethod
    def _log_warning(message: str, error: Exception):
        QgsMessageLog.logMessage(
            f"{message}: {error}",
            PLUGIN_NAME,
            Qgis.MessageLevel.Warning,
        )
