from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import subprocess


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[kischk-prompt-editor {timestamp}] {message}", flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_prompt_path() -> Path:
    return _repo_root() / "prompts" / "detector_prompt_editor.md"


def _build_prompt(
    prompt_template: str,
    known_mistakes_path: Path,
    results_check_output_path: Path,
    current_detector_prompt_path: Path,
    changelog_path: Path,
) -> str:
    return (
        prompt_template.rstrip()
        + "\n\n"
        + f"known mistakes file: {known_mistakes_path}\n"
        + f"output of result checker: {results_check_output_path}\n"
        + f"current detector prompt: {current_detector_prompt_path}\n"
        + f"markdown changelog: {changelog_path}\n"
    )


def run_detector_prompt_editor(
    known_mistakes_path: str | Path,
    results_check_output_path: str | Path,
    current_detector_prompt_path: str | Path,
    changelog_path: str | Path,
    prompt_path: str | Path | None = None,
    model: str = "gpt-5.3-codex",
    reasoning_effort: str = "high",
) -> Path:
    resolved_known_mistakes = Path(known_mistakes_path).expanduser().resolve()
    resolved_results_check_output = Path(results_check_output_path).expanduser().resolve()
    resolved_current_detector_prompt = Path(current_detector_prompt_path).expanduser().resolve()
    resolved_changelog = Path(changelog_path).expanduser().resolve()
    resolved_changelog.parent.mkdir(parents=True, exist_ok=True)

    resolved_prompt = (
        Path(prompt_path).expanduser().resolve()
        if prompt_path is not None
        else _default_prompt_path()
    )

    _log(f"Using prompt template: {resolved_prompt}")
    prompt_template = resolved_prompt.read_text(encoding="utf-8")
    full_prompt = _build_prompt(
        prompt_template=prompt_template,
        known_mistakes_path=resolved_known_mistakes,
        results_check_output_path=resolved_results_check_output,
        current_detector_prompt_path=resolved_current_detector_prompt,
        changelog_path=resolved_changelog,
    )

    command = [
        "codex",
        "exec",
        "--cd",
        str(_repo_root()),
        "--model",
        model,
        "-c",
        f'reasoning_effort="{reasoning_effort}"',
        "-",
    ]
    _log(f"Running detector prompt editor command: {' '.join(command)}")
    _log("Streaming codex detector-prompt-editor output:")
    proc = subprocess.run(command, input=full_prompt, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Detector prompt editor step failed with exit code {proc.returncode}"
        )

    _log(f"Detector prompt editor completed. Changelog path: {resolved_changelog}")
    return resolved_changelog


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run detector prompt editor via codex exec.",
    )
    parser.add_argument(
        "--known-mistakes-path",
        type=Path,
        required=True,
        help="Path to known mistakes markdown file.",
    )
    parser.add_argument(
        "--results-check-output-path",
        type=Path,
        required=True,
        help="Path to results-check output JSON (example: run_dir/analisys_report_check.json).",
    )
    parser.add_argument(
        "--current-detector-prompt-path",
        type=Path,
        required=True,
        help="Path to detector prompt file to edit (example: prompts/detector.md).",
    )
    parser.add_argument(
        "--changelog-path",
        type=Path,
        required=True,
        help="Path to markdown changelog output (example: evaluation/detector_prompt_changelog.md).",
    )
    parser.add_argument(
        "--prompt-path",
        type=Path,
        default=None,
        help="Path to editor prompt template (default: prompts/detector_prompt_editor.md).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5.3-codex",
        help="Codex model for detector prompt editor (default: gpt-5.3-codex).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        default="high",
        help="Reasoning effort for model (default: high).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    changelog = run_detector_prompt_editor(
        known_mistakes_path=args.known_mistakes_path,
        results_check_output_path=args.results_check_output_path,
        current_detector_prompt_path=args.current_detector_prompt_path,
        changelog_path=args.changelog_path,
        prompt_path=args.prompt_path,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    print(f"Detector prompt editor changelog path: {changelog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
