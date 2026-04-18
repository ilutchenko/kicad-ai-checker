from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kischk.cli.results_check import run_results_check


class ResultsCheckTests(unittest.TestCase):
    def test_runs_codex_exec_with_prompt_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            prompt_path = Path(tmp) / "results_check.md"
            prompt_path.write_text("template", encoding="utf-8")

            known_mistakes = Path(tmp) / "known_mistakes.md"
            known_mistakes.write_text("mistakes", encoding="utf-8")
            checker_output = Path(tmp) / "analisys_report.json"
            checker_output.write_text("{}", encoding="utf-8")
            output_json = Path(tmp) / "nested" / "analisys_report_check.json"

            captured: dict[str, object] = {}

            def _fake_run(command: list[str], input: str, text: bool) -> subprocess.CompletedProcess[str]:
                captured["command"] = command
                captured["input"] = input
                captured["text"] = text
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with patch("kischk.cli.results_check.subprocess.run", side_effect=_fake_run):
                returned = run_results_check(
                    run_dir=run_dir,
                    known_mistakes_path=known_mistakes,
                    checker_output_path=checker_output,
                    output_json_path=output_json,
                    prompt_path=prompt_path,
                    model="gpt-5.4-mini",
                    reasoning_effort="medium",
                )

            self.assertEqual(returned, output_json.resolve())
            self.assertTrue(output_json.parent.exists())
            self.assertEqual(
                captured["command"],
                [
                    "codex",
                    "exec",
                    "--cd",
                    str(run_dir.resolve()),
                    "--model",
                    "gpt-5.4-mini",
                    "-c",
                    'reasoning_effort="medium"',
                    "-",
                ],
            )
            self.assertTrue(captured["text"])
            prompt = str(captured["input"])
            self.assertIn("template", prompt)
            self.assertIn(f"known mistakes file: {known_mistakes.resolve()}", prompt)
            self.assertIn(f"output of schematic checker: {checker_output.resolve()}", prompt)
            self.assertIn(f"your output json: {output_json.resolve()}", prompt)

    def test_raises_when_codex_exec_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            prompt_path = Path(tmp) / "results_check.md"
            prompt_path.write_text("template", encoding="utf-8")
            known_mistakes = Path(tmp) / "known_mistakes.md"
            known_mistakes.write_text("mistakes", encoding="utf-8")
            checker_output = Path(tmp) / "analisys_report.json"
            checker_output.write_text("{}", encoding="utf-8")
            output_json = Path(tmp) / "analisys_report_check.json"

            with patch(
                "kischk.cli.results_check.subprocess.run",
                return_value=subprocess.CompletedProcess(["codex"], 3, stdout="", stderr=""),
            ):
                with self.assertRaisesRegex(RuntimeError, "exit code 3"):
                    run_results_check(
                        run_dir=run_dir,
                        known_mistakes_path=known_mistakes,
                        checker_output_path=checker_output,
                        output_json_path=output_json,
                        prompt_path=prompt_path,
                    )


if __name__ == "__main__":
    unittest.main()
