import unittest

from qgis.core import QgsLayerTreeGroup

from lcaxs.restorer import apply_expansion_state
from lcaxs.state import ExpansionState


class RestorerTest(unittest.TestCase):
    def test_restores_duplicate_groups_by_tree_path(self):
        root = QgsLayerTreeGroup()
        first = root.addGroup("Data")
        second = root.addGroup("Data")
        first.setExpanded(True)
        second.setExpanded(False)
        state = ExpansionState(
            groups={
                (("Data", 0),): False,
                (("Data", 1),): True,
            }
        )

        changed = apply_expansion_state(root, state)

        self.assertEqual(changed, 2)
        self.assertFalse(first.isExpanded())
        self.assertTrue(second.isExpanded())


if __name__ == "__main__":
    unittest.main()
