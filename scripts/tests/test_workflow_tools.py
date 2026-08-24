from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "data_generation"))

from render_loader import render
from validate_data_profile import expected_files


class WorkflowToolsTest(unittest.TestCase):
    def test_data_profile_has_30_unique_files(self) -> None:
        files = expected_files()
        self.assertEqual(len(files), 30)
        self.assertEqual(len(set(files)), 30)

    def test_loader_render_replaces_stable_aliases(self) -> None:
        rendered = render(
            "FROM 'legacy_host_data/grbench/sf10_4/sciscinet_papers.csv';",
            "sf10_1",
            Path("/tmp/grbench-data"),
            Path("/tmp/grbench-prepared"),
            Path("/tmp/grbench-updates"),
        )
        self.assertIn("/tmp/grbench-data/sf10_1/sciscinet_papers.csv", rendered)
        self.assertNotIn("legacy_host_data", rendered)


if __name__ == "__main__":
    unittest.main()
