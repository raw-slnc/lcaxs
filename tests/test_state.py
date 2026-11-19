import tempfile
import unittest
from pathlib import Path
import zipfile

from state import state_from_project_file, state_from_xml


PROJECT_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<qgis>
  <layer-tree-group>
    <layer-tree-group name="Output" expanded="0">
      <layer-tree-group name="Data" expanded="1">
        <layer-tree-layer id="layer_a" expanded="0" />
      </layer-tree-group>
      <layer-tree-group name="Data" expanded="0">
        <layer-tree-layer id="layer_b" expanded="1" />
      </layer-tree-group>
    </layer-tree-group>
  </layer-tree-group>
</qgis>
"""


class ExpansionStateTest(unittest.TestCase):
    def test_nested_and_duplicate_group_names(self):
        state = state_from_xml(PROJECT_XML)

        self.assertFalse(state.groups[(("Output", 0),)])
        self.assertTrue(state.groups[(("Output", 0), ("Data", 0))])
        self.assertFalse(state.groups[(("Output", 0), ("Data", 1))])
        self.assertEqual(state.layers, {"layer_a": False, "layer_b": True})

    def test_reads_qgs_and_qgz(self):
        with tempfile.TemporaryDirectory() as folder:
            folder_path = Path(folder)
            qgs_path = folder_path / "sample.qgs"
            qgs_path.write_bytes(PROJECT_XML)

            qgz_path = folder_path / "sample.qgz"
            with zipfile.ZipFile(qgz_path, "w") as archive:
                archive.writestr("sample.qgs", PROJECT_XML)

            self.assertEqual(
                state_from_project_file(str(qgs_path)).groups,
                state_from_project_file(str(qgz_path)).groups,
            )


if __name__ == "__main__":
    unittest.main()
