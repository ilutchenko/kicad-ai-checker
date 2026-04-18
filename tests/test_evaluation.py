from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kischk.cli.evaluation import run_evaluation


class EvaluationTests(unittest.TestCase):
    def test_runs_check_and_results_check_with_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runs_root = Path(tmp) / "runs"

            expected_run_dir = runs_root / "20260418_120000"
            with (
                patch("kischk.cli.evaluation.run_main_cycle") as run_main_cycle_mock,
                patch("kischk.cli.evaluation.run_results_check") as run_results_check_mock,
            ):
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
            run_results_check_mock.assert_called_once_with(
                run_dir=expected_run_dir,
                known_mistakes_path=project_dir.resolve() / "known_mistakes.md",
                checker_output_path=expected_run_dir / "analisys_report.json",
                output_json_path=expected_run_dir / "analisys_report_check.json",
                prompt_path=None,
                model="gpt-5.4-mini",
                reasoning_effort="medium",
            )

    def test_forwards_custom_detector_and_results_check_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runs_root = Path(tmp) / "runs"
            detector_prompt_path = Path(tmp) / "detector.md"
            detector_prompt_path.write_text("prompt", encoding="utf-8")
            results_check_prompt_path = Path(tmp) / "results_check.md"
            results_check_prompt_path.write_text("prompt", encoding="utf-8")
            known_mistakes_path = Path(tmp) / "known_mistakes.md"
            known_mistakes_path.write_text("mistakes", encoding="utf-8")
            checker_output_path = Path(tmp) / "custom_analisys_report.json"
            results_check_output_path = Path(tmp) / "custom_analisys_report_check.json"

            expected_run_dir = runs_root / "20260418_120001"
            with (
                patch("kischk.cli.evaluation.run_main_cycle") as run_main_cycle_mock,
                patch("kischk.cli.evaluation.run_results_check") as run_results_check_mock,
            ):
                run_main_cycle_mock.return_value = expected_run_dir

                run_evaluation(
                    project_dir=project_dir,
                    runs_root=runs_root,
                    detector_prompt_path=detector_prompt_path,
                    detector_model="gpt-5.4",
                    detector_reasoning_effort="high",
                    results_check_prompt_path=results_check_prompt_path,
                    known_mistakes_path=known_mistakes_path,
                    checker_output_path=checker_output_path,
                    results_check_output_path=results_check_output_path,
                    results_check_model="gpt-5.2",
                    results_check_reasoning_effort="xhigh",
                )

            run_main_cycle_mock.assert_called_once_with(
                project_dir=project_dir.resolve(),
                runs_root=runs_root.resolve(),
                run_detector=True,
                detector_prompt_path=detector_prompt_path,
                detector_model="gpt-5.4",
                detector_reasoning_effort="high",
            )
            run_results_check_mock.assert_called_once_with(
                run_dir=expected_run_dir,
                known_mistakes_path=known_mistakes_path.resolve(),
                checker_output_path=checker_output_path.resolve(),
                output_json_path=results_check_output_path.resolve(),
                prompt_path=results_check_prompt_path,
                model="gpt-5.2",
                reasoning_effort="xhigh",
            )


if __name__ == "__main__":
    unittest.main()
