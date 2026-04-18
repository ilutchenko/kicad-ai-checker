from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kischk.cli.detector_prompt_editor as detector_prompt_editor_module
from kischk.cli.detector_prompt_editor import run_detector_prompt_editor


class DetectorPromptEditorTests(unittest.TestCase):
    def test_runs_codex_exec_with_prompt_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt_path = Path(tmp) / "detector_prompt_editor.md"
            prompt_path.write_text("template", encoding="utf-8")

            known_mistakes = Path(tmp) / "known_mistakes.md"
            known_mistakes.write_text("mistakes", encoding="utf-8")
            results_check_output = Path(tmp) / "analisys_report_check.json"
            results_check_output.write_text("{}", encoding="utf-8")
            current_detector_prompt = Path(tmp) / "detector.md"
            current_detector_prompt.write_text("prompt", encoding="utf-8")
            changelog = Path(tmp) / "evaluation" / "detector_prompt_changelog.md"

            captured: dict[str, object] = {}

            def _fake_run(command: list[str], input: str, text: bool) -> subprocess.CompletedProcess[str]:
                captured["command"] = command
                captured["input"] = input
                captured["text"] = text
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with patch(
                "kischk.cli.detector_prompt_editor.subprocess.run",
                side_effect=_fake_run,
            ):
                returned = run_detector_prompt_editor(
                    known_mistakes_path=known_mistakes,
                    results_check_output_path=results_check_output,
                    current_detector_prompt_path=current_detector_prompt,
                    changelog_path=changelog,
                    prompt_path=prompt_path,
                    model="gpt-5.3-codex",
                    reasoning_effort="high",
                )

            self.assertEqual(returned, changelog.resolve())
            self.assertTrue(changelog.parent.exists())
            self.assertEqual(
                captured["command"],
                [
                    "codex",
                    "exec",
                    "--cd",
                    str(detector_prompt_editor_module._repo_root()),
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
            self.assertIn(f"known mistakes file: {known_mistakes.resolve()}", prompt)
            self.assertIn(
                f"output of result checker: {results_check_output.resolve()}",
                prompt,
            )
            self.assertIn(
                f"current detector prompt: {current_detector_prompt.resolve()}",
                prompt,
            )
            self.assertIn(f"markdown changelog: {changelog.resolve()}", prompt)

    def test_raises_when_codex_exec_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt_path = Path(tmp) / "detector_prompt_editor.md"
            prompt_path.write_text("template", encoding="utf-8")
            known_mistakes = Path(tmp) / "known_mistakes.md"
            known_mistakes.write_text("mistakes", encoding="utf-8")
            results_check_output = Path(tmp) / "analisys_report_check.json"
            results_check_output.write_text("{}", encoding="utf-8")
            current_detector_prompt = Path(tmp) / "detector.md"
            current_detector_prompt.write_text("prompt", encoding="utf-8")
            changelog = Path(tmp) / "detector_prompt_changelog.md"

            with patch(
                "kischk.cli.detector_prompt_editor.subprocess.run",
                return_value=subprocess.CompletedProcess(["codex"], 2, stdout="", stderr=""),
            ):
                with self.assertRaisesRegex(RuntimeError, "exit code 2"):
                    run_detector_prompt_editor(
                        known_mistakes_path=known_mistakes,
                        results_check_output_path=results_check_output,
                        current_detector_prompt_path=current_detector_prompt,
                        changelog_path=changelog,
                        prompt_path=prompt_path,
                    )


if __name__ == "__main__":
    unittest.main()
