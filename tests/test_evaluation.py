from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kischk.cli.evaluation as evaluation_module
from kischk.cli.evaluation import _calculate_detected_total, run_evaluation


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
                patch(
                    "kischk.cli.evaluation.run_detector_prompt_editor"
                ) as run_detector_prompt_editor_mock,
                patch(
                    "kischk.cli.evaluation.run_preprocessing_editor"
                ) as run_preprocessing_editor_mock,
                patch("kischk.cli.evaluation._calculate_detected_total") as detected_total_mock,
            ):
                run_main_cycle_mock.return_value = expected_run_dir
                detected_total_mock.return_value = (3, 9)

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
            detected_total_mock.assert_called_once_with(
                expected_run_dir / "analisys_report_check.json"
            )
            run_detector_prompt_editor_mock.assert_called_once_with(
                known_mistakes_path=project_dir.resolve() / "known_mistakes.md",
                results_check_output_path=expected_run_dir / "analisys_report_check.json",
                current_detector_prompt_path=evaluation_module.Path(
                    evaluation_module.__file__
                ).resolve().parents[3]
                / "prompts"
                / "detector.md",
                changelog_path=evaluation_module.Path(
                    evaluation_module.__file__
                ).resolve().parents[3]
                / "evaluation"
                / "detector_prompt_changelog.md",
                prompt_path=None,
                model="gpt-5.3-codex",
                reasoning_effort="high",
            )
            run_preprocessing_editor_mock.assert_called_once_with(
                analysis_process_log_path=expected_run_dir / "analysis_process.md",
                prompt_path=None,
                model="gpt-5.3-codex",
                reasoning_effort="high",
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
            detector_prompt_editor_prompt_path = Path(tmp) / "detector_prompt_editor.md"
            detector_prompt_editor_prompt_path.write_text("prompt", encoding="utf-8")
            current_detector_prompt_path = Path(tmp) / "detector.md"
            current_detector_prompt_path.write_text("prompt", encoding="utf-8")
            detector_prompt_changelog_path = Path(tmp) / "detector_prompt_changelog.md"
            preprocessing_editor_prompt_path = Path(tmp) / "preprocessing_editor.md"
            preprocessing_editor_prompt_path.write_text("prompt", encoding="utf-8")
            analysis_process_log_path = Path(tmp) / "analysis_process.md"
            analysis_process_log_path.write_text("log", encoding="utf-8")

            expected_run_dir = runs_root / "20260418_120001"
            with (
                patch("kischk.cli.evaluation.run_main_cycle") as run_main_cycle_mock,
                patch("kischk.cli.evaluation.run_results_check") as run_results_check_mock,
                patch(
                    "kischk.cli.evaluation.run_detector_prompt_editor"
                ) as run_detector_prompt_editor_mock,
                patch(
                    "kischk.cli.evaluation.run_preprocessing_editor"
                ) as run_preprocessing_editor_mock,
                patch("kischk.cli.evaluation._calculate_detected_total") as detected_total_mock,
            ):
                run_main_cycle_mock.return_value = expected_run_dir
                detected_total_mock.return_value = (5, 12)

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
                    detector_prompt_editor_prompt_path=detector_prompt_editor_prompt_path,
                    current_detector_prompt_path=current_detector_prompt_path,
                    detector_prompt_changelog_path=detector_prompt_changelog_path,
                    detector_prompt_editor_model="gpt-5.4",
                    detector_prompt_editor_reasoning_effort="xhigh",
                    preprocessing_editor_prompt_path=preprocessing_editor_prompt_path,
                    analysis_process_log_path=analysis_process_log_path,
                    preprocessing_editor_model="gpt-5.4-mini",
                    preprocessing_editor_reasoning_effort="xhigh",
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
            detected_total_mock.assert_called_once_with(
                results_check_output_path.resolve()
            )
            run_detector_prompt_editor_mock.assert_called_once_with(
                known_mistakes_path=known_mistakes_path.resolve(),
                results_check_output_path=results_check_output_path.resolve(),
                current_detector_prompt_path=current_detector_prompt_path.resolve(),
                changelog_path=detector_prompt_changelog_path.resolve(),
                prompt_path=detector_prompt_editor_prompt_path,
                model="gpt-5.4",
                reasoning_effort="xhigh",
            )
            run_preprocessing_editor_mock.assert_called_once_with(
                analysis_process_log_path=analysis_process_log_path.resolve(),
                prompt_path=preprocessing_editor_prompt_path,
                model="gpt-5.4-mini",
                reasoning_effort="xhigh",
            )

    def test_calculate_detected_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "analisys_report_check.json"
            output.write_text(
                json.dumps(
                    {
                        "mistakes": [
                            {"name": "a", "detected": "true"},
                            {"name": "b", "detected": "false"},
                            {"name": "c", "detected": True},
                            {"name": "d", "detected": False},
                            {"name": "e", "detected": "TRUE"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            detected, total = _calculate_detected_total(output)
            self.assertEqual((detected, total), (3, 5))


if __name__ == "__main__":
    unittest.main()
