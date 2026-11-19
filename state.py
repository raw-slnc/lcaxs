# -*- coding: utf-8 -*-
"""Read expansion state from QGIS project documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Tuple
import zipfile

from qgis.PyQt.QtXml import QDomDocument


GroupSegment = Tuple[str, int]
GroupPath = Tuple[GroupSegment, ...]


@dataclass
class ExpansionState:
    """Saved expanded state for group paths and layer IDs."""

    groups: Dict[GroupPath, bool] = field(default_factory=dict)
    layers: Dict[str, bool] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """Return whether the project contained no expansion information."""

        return not self.groups and not self.layers


def _expanded_value(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def _dom_children(element: Any) -> Iterator[Any]:
    child = element.firstChildElement()
    while not child.isNull():
        yield child
        child = child.nextSiblingElement()


def _dom_tag(element: Any) -> str:
    return element.tagName()


def _dom_attribute(element: Any, name: str) -> str:
    return element.attribute(name)


def _dom_has_attribute(element: Any, name: str) -> bool:
    return element.hasAttribute(name)


def _collect_state(
    tree_root: Any,
    *,
    children: Any,
    tag: Any,
    attribute: Any,
    has_attribute: Any,
) -> ExpansionState:
    state = ExpansionState()

    def visit(parent: Any, path: GroupPath) -> None:
        occurrences: Dict[str, int] = {}
        for child in children(parent):
            child_tag = tag(child)
            if child_tag == "layer-tree-group":
                name = attribute(child, "name")
                occurrence = occurrences.get(name, 0)
                occurrences[name] = occurrence + 1
                child_path = path + ((name, occurrence),)
                if has_attribute(child, "expanded"):
                    state.groups[child_path] = _expanded_value(
                        attribute(child, "expanded")
                    )
                visit(child, child_path)
            elif child_tag == "layer-tree-layer":
                layer_id = attribute(child, "id")
                if layer_id and has_attribute(child, "expanded"):
                    state.layers[layer_id] = _expanded_value(
                        attribute(child, "expanded")
                    )

    visit(tree_root, ())
    return state


def state_from_qdom(document: Any) -> ExpansionState:
    """Read state from the QDomDocument emitted by QgsProject.readProject."""

    document_root = document.documentElement()
    tree_root = document_root.firstChildElement("layer-tree-group")
    if tree_root.isNull():
        return ExpansionState()
    return _collect_state(
        tree_root,
        children=_dom_children,
        tag=_dom_tag,
        attribute=_dom_attribute,
        has_attribute=_dom_has_attribute,
    )


def state_from_xml(data: bytes) -> ExpansionState:
    """Read state from the XML content of a .qgs project."""

    document = QDomDocument()
    result = document.setContent(data)
    success = result[0] if isinstance(result, tuple) else bool(result)
    if not success:
        detail = result[1] if isinstance(result, tuple) and len(result) > 1 else ""
        raise ValueError(f"Invalid QGS project XML: {detail}")
    return state_from_qdom(document)


def _qgs_member(names: Iterable[str]) -> str:
    candidates = [name for name in names if name.lower().endswith(".qgs")]
    if not candidates:
        raise ValueError("The QGZ archive contains no QGS project document")
    return min(candidates, key=lambda name: (name.count("/"), len(name), name))


def state_from_project_file(path: str) -> ExpansionState:
    """Read state from a local .qgs or .qgz project file."""

    project_path = Path(path)
    if project_path.suffix.lower() == ".qgz":
        with zipfile.ZipFile(project_path) as archive:
            data = archive.read(_qgs_member(archive.namelist()))
    else:
        data = project_path.read_bytes()
    return state_from_xml(data)
