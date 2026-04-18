from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from kischk.cli.check_schematic import run_main_cycle


REPO_ROOT = Path(__file__).resolve().parents[1]


class MainCycleTests(unittest.TestCase):
    def test_creates_timestamped_run_dir_and_preprocessed_output(self) -> None:
        project_dir = REPO_ROOT / "test_kicad_project"

        with tempfile.TemporaryDirectory() as tmp:
            runs_root = Path(tmp) / "runs"

            run_dir = run_main_cycle(project_dir, runs_root=runs_root, run_detector=False)

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

    def test_detector_step_uses_prompt_and_runtime_paths(self) -> None:
        project_dir = REPO_ROOT / "test_kicad_project"

        with tempfile.TemporaryDirectory() as tmp:
            runs_root = Path(tmp) / "runs"
            prompt_file = Path(tmp) / "detector.md"
            prompt_file.write_text("Detector prompt template", encoding="utf-8")

            with patch(
                "kischk.cli.check_schematic._run_detector",
            ) as run_detector_mock:
                run_dir = run_main_cycle(
                    project_dir,
                    runs_root=runs_root,
                    detector_prompt_path=prompt_file,
                )

            output_path = run_dir / "processed_net_graph.json"
            run_detector_mock.assert_called_once()
            prompt_text = str(run_detector_mock.call_args.args[0])
            called_run_dir = run_detector_mock.call_args.kwargs["run_dir"]
            self.assertEqual(called_run_dir, run_dir)
            self.assertIn("Detector prompt template", prompt_text)
            self.assertIn(f"processed_net_graph.json path: {output_path}", prompt_text)
            self.assertIn(
                f"datasheet path: {project_dir.resolve() / 'datasheets'}",
                prompt_text,
            )
            self.assertIn(f"output directory path: {run_dir}", prompt_text)


if __name__ == "__main__":
    unittest.main()
