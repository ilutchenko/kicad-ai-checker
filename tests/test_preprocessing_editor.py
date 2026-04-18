from __future__ import annotations

import subprocess
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

            captured: dict[str, object] = {}

            def _fake_run(command: list[str], input: str, text: bool) -> subprocess.CompletedProcess[str]:
                captured["command"] = command
                captured["input"] = input
                captured["text"] = text
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with patch(
                "kischk.cli.preprocessing_editor.subprocess.run",
                side_effect=_fake_run,
            ):
                returned = run_preprocessing_editor(
                    analysis_process_log_path=analysis_process_log,
                    prompt_path=prompt_path,
                    model="gpt-5.3-codex",
                    reasoning_effort="high",
                )

            self.assertEqual(returned, analysis_process_log.resolve())
            self.assertEqual(
                captured["command"],
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
            self.assertTrue(captured["text"])
            prompt = str(captured["input"])
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
                "kischk.cli.preprocessing_editor.subprocess.run",
                return_value=subprocess.CompletedProcess(["codex"], 5, stdout="", stderr=""),
            ):
                with self.assertRaisesRegex(RuntimeError, "exit code 5"):
                    run_preprocessing_editor(
                        analysis_process_log_path=analysis_process_log,
                        prompt_path=prompt_path,
                    )


if __name__ == "__main__":
    unittest.main()
