from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kischk.cli.evaluation import run_evaluation


class EvaluationTests(unittest.TestCase):
    def test_runs_check_script_once_with_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runs_root = Path(tmp) / "runs"

            expected_run_dir = runs_root / "20260418_120000"
            with patch("kischk.cli.evaluation.run_main_cycle") as run_main_cycle_mock:
                run_main_cycle_mock.return_value = expected_run_dir

                actual = run_evaluation(project_dir=project_dir, runs_root=runs_root)

            self.assertEqual(actual, expected_run_dir)
            run_main_cycle_mock.assert_called_once_with(
                project_dir=project_dir.resolve(),
                runs_root=runs_root.resolve(),
                run_detector=True,
                detector_prompt_path=None,
                detector_model="gpt-5.3-codex",
                detector_reasoning_effort="xhigh",
            )

    def test_forwards_custom_detector_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runs_root = Path(tmp) / "runs"
            prompt_path = Path(tmp) / "detector.md"
            prompt_path.write_text("prompt", encoding="utf-8")

            expected_run_dir = runs_root / "20260418_120001"
            with patch("kischk.cli.evaluation.run_main_cycle") as run_main_cycle_mock:
                run_main_cycle_mock.return_value = expected_run_dir

                run_evaluation(
                    project_dir=project_dir,
                    runs_root=runs_root,
                    detector_prompt_path=prompt_path,
                    detector_model="gpt-5.4",
                    detector_reasoning_effort="high",
                )

            run_main_cycle_mock.assert_called_once_with(
                project_dir=project_dir.resolve(),
                runs_root=runs_root.resolve(),
                run_detector=True,
                detector_prompt_path=prompt_path,
                detector_model="gpt-5.4",
                detector_reasoning_effort="high",
            )


if __name__ == "__main__":
    unittest.main()
