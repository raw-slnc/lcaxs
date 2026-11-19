import unittest

from qgis.core import QgsLayerTreeGroup

from lcaxs.plugin import (
    ALWAYS_OPEN_PROPERTY,
    apply_always_open,
    apply_expansion_state,
    group_is_always_open,
)
from lcaxs.state import ExpansionState


class AlwaysOpenTest(unittest.TestCase):
    def test_opens_marked_group_and_ancestors_only(self):
        root = QgsLayerTreeGroup()
        parent = root.addGroup("Parent")
        child = parent.addGroup("Child")
        unrelated = root.addGroup("Unrelated")
        parent.setExpanded(False)
        child.setExpanded(False)
        unrelated.setExpanded(False)
        child.setCustomProperty(ALWAYS_OPEN_PROPERTY, True)

        changed = apply_always_open(root)

        self.assertEqual(changed, 2)
        self.assertTrue(parent.isExpanded())
        self.assertTrue(child.isExpanded())
        self.assertFalse(unrelated.isExpanded())

    def test_false_string_does_not_enable_override(self):
        group = QgsLayerTreeGroup("Group")
        group.setCustomProperty(ALWAYS_OPEN_PROPERTY, "false")

        self.assertFalse(group_is_always_open(group))

    def test_always_open_takes_precedence_over_saved_collapsed_state(self):
        root = QgsLayerTreeGroup()
        group = root.addGroup("Group")
        group.setCustomProperty(ALWAYS_OPEN_PROPERTY, True)
        state = ExpansionState(groups={(("Group", 0),): False})

        apply_expansion_state(root, state)
        apply_always_open(root)

        self.assertTrue(group.isExpanded())


if __name__ == "__main__":
    unittest.main()
