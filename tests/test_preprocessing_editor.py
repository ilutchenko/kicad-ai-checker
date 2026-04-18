from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kischk.cli.preprocessing_editor as preprocessing_editor_module
from kischk.cli.preprocessing_editor import run_preprocessing_editor


class PreprocessingEditorTests(unittest.TestCase):
    def test_runs_codex_exec_with_prompt_and_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt_path = Path(tmp) / "preprocessing_editor.md"
            prompt_path.write_text("template", encoding="utf-8")
            analysis_process_log = Path(tmp) / "analysis_process.md"
            analysis_process_log.write_text("log", encoding="utf-8")

            with patch(
                "kischk.cli.preprocessing_editor.run_codex_exec",
            ) as run_codex_exec_mock:
                returned = run_preprocessing_editor(
                    analysis_process_log_path=analysis_process_log,
                    prompt_path=prompt_path,
                    model="gpt-5.3-codex",
                    reasoning_effort="high",
                )

            self.assertEqual(returned, analysis_process_log.resolve())
            run_codex_exec_call = run_codex_exec_mock.call_args.kwargs
            self.assertEqual(
                run_codex_exec_call["command"],
                [
                    "codex",
                    "exec",
                    "--cd",
                    str(preprocessing_editor_module._repo_root()),
                    "--model",
                    "gpt-5.3-codex",
                    "-c",
                    'reasoning_effort="high"',
                    "-",
                ],
            )
            self.assertEqual(run_codex_exec_call["usage_step"], "preprocessing_editor")
            self.assertEqual(run_codex_exec_call["model"], "gpt-5.3-codex")
            self.assertEqual(run_codex_exec_call["reasoning_effort"], "high")
            self.assertIsNone(run_codex_exec_call["usage_stats_path"])
            prompt = str(run_codex_exec_call["prompt"])
            self.assertIn("template", prompt)
            self.assertIn(
                f"analysis_process.md path: {analysis_process_log.resolve()}",
                prompt,
            )

    def test_raises_when_codex_exec_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt_path = Path(tmp) / "preprocessing_editor.md"
            prompt_path.write_text("template", encoding="utf-8")
            analysis_process_log = Path(tmp) / "analysis_process.md"
            analysis_process_log.write_text("log", encoding="utf-8")

            with patch(
                "kischk.cli.preprocessing_editor.run_codex_exec",
                side_effect=RuntimeError("codex exec failed with exit code 5"),
            ):
                with self.assertRaisesRegex(RuntimeError, "exit code 5"):
                    run_preprocessing_editor(
                        analysis_process_log_path=analysis_process_log,
                        prompt_path=prompt_path,
                    )


if __name__ == "__main__":
    unittest.main()
