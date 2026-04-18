from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from kischk.cli.codex_usage import run_codex_exec


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[kischk-results-check {timestamp}] {message}", flush=True)


def _default_prompt_path() -> Path:
    return Path(__file__).resolve().parents[3] / "prompts" / "results_check.md"


def _build_prompt(
    prompt_template: str,
    known_mistakes_path: Path,
    checker_output_path: Path,
    output_json_path: Path,
) -> str:
    return (
        prompt_template.rstrip()
        + "\n\n"
        + f"known mistakes file: {known_mistakes_path}\n"
        + f"output of schematic checker: {checker_output_path}\n"
        + f"your output json: {output_json_path}\n"
    )


def run_results_check(
    run_dir: str | Path,
    known_mistakes_path: str | Path,
    checker_output_path: str | Path,
    output_json_path: str | Path,
    prompt_path: str | Path | None = None,
    model: str = "gpt-5.4-mini",
    reasoning_effort: str = "medium",
    usage_stats_path: str | Path | None = None,
) -> Path:
    resolved_run_dir = Path(run_dir).expanduser().resolve()
    resolved_known_mistakes = Path(known_mistakes_path).expanduser().resolve()
    resolved_checker_output = Path(checker_output_path).expanduser().resolve()
    resolved_output_json = Path(output_json_path).expanduser().resolve()
    resolved_output_json.parent.mkdir(parents=True, exist_ok=True)

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
        checker_output_path=resolved_checker_output,
        output_json_path=resolved_output_json,
    )

    command = [
        "codex",
        "exec",
        "--cd",
        str(resolved_run_dir),
        "--model",
        model,
        "-c",
        f'reasoning_effort="{reasoning_effort}"',
        "-",
    ]
    _log(f"Running result check command: {' '.join(command)}")
    _log("Streaming codex result-check output:")
    run_codex_exec(
        command=command,
        prompt=full_prompt,
        log=_log,
        usage_stats_path=usage_stats_path,
        usage_step="results_check",
        model=model,
        reasoning_effort=reasoning_effort,
    )

    _log(f"Result check completed. Expected output json: {resolved_output_json}")
    return resolved_output_json


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run detector result checker via codex exec.",
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="Run directory produced by schematic checker.",
    )
    parser.add_argument(
        "--known-mistakes-path",
        type=Path,
        required=True,
        help="Path to known mistakes markdown file.",
    )
    parser.add_argument(
        "--checker-output-path",
        type=Path,
        required=True,
        help="Path to checker output JSON (example: run_dir/analisys_report.json).",
    )
    parser.add_argument(
        "--output-json-path",
        type=Path,
        required=True,
        help="Path for result-check output JSON (example: run_dir/analisys_report_check.json).",
    )
    parser.add_argument(
        "--prompt-path",
        type=Path,
        default=None,
        help="Path to prompt template (default: prompts/results_check.md).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5.4-mini",
        help="Codex model for result checker (default: gpt-5.4-mini).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        default="medium",
        help="Reasoning effort for model (default: medium).",
    )
    parser.add_argument(
        "--usage-stats-path",
        type=Path,
        default=None,
        help="Path to JSON file for codex token usage stats.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    output_path = run_results_check(
        run_dir=args.run_dir,
        known_mistakes_path=args.known_mistakes_path,
        checker_output_path=args.checker_output_path,
        output_json_path=args.output_json_path,
        prompt_path=args.prompt_path,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        usage_stats_path=args.usage_stats_path,
    )
    print(f"Result check output path: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
