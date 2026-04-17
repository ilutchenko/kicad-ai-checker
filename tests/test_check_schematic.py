from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kischk.cli.check_schematic import run_main_cycle


REPO_ROOT = Path(__file__).resolve().parents[1]


class MainCycleTests(unittest.TestCase):
    def test_creates_timestamped_run_dir_and_preprocessed_output(self) -> None:
        project_dir = REPO_ROOT / "test_kicad_project"

        with tempfile.TemporaryDirectory() as tmp:
            runs_root = Path(tmp) / "runs"

            run_dir = run_main_cycle(project_dir, runs_root=runs_root)

            self.assertTrue(run_dir.exists())
            self.assertEqual(run_dir.parent, runs_root.resolve())

            output_path = run_dir / "processed_net_graph.json"
            self.assertTrue(output_path.exists())

            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(data["project_root"], str(project_dir.resolve()))
            self.assertEqual(data["run_dir"], str(run_dir))
            self.assertIn("created_at", data)
            self.assertIn("electrical_project", data)
            self.assertGreater(len(data["electrical_project"]["schematics"]), 0)
            self.assertGreater(len(data["electrical_project"]["nets"]), 0)


if __name__ == "__main__":
    unittest.main()
