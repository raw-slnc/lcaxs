# -*- coding: utf-8 -*-
"""QGIS plugin entry point."""


def classFactory(iface):  # noqa: N802 - QGIS requires this name
    """Return the plugin instance used by QGIS."""

    from .plugin import LcaxsPlugin

    return LcaxsPlugin(iface)
