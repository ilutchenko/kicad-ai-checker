from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from kischk.cli.check_schematic import run_main_cycle
from kischk.cli.detector_prompt_editor import run_detector_prompt_editor
from kischk.cli.preprocessing_editor import run_preprocessing_editor
from kischk.cli.results_check import run_results_check


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[kischk-eval {timestamp}] {message}", flush=True)


def _is_detected(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def _calculate_detected_total(results_check_output_path: Path) -> tuple[int, int]:
    payload = json.loads(results_check_output_path.read_text(encoding="utf-8"))
    summary = payload.get("summary")
    if isinstance(summary, dict):
        total = summary.get("total")
        detected = summary.get("detected")
        if isinstance(total, int) and isinstance(detected, int):
            return detected, total

    mistakes = payload.get("mistakes")
    if not isinstance(mistakes, list):
        raise ValueError(
            f"Invalid results-check output format: {results_check_output_path} "
            "must contain either summary.total/summary.detected or a list in 'mistakes'."
        )
    total = len(mistakes)
    detected = sum(
        1
        for item in mistakes
        if isinstance(item, dict) and _is_detected(item.get("detected"))
    )
    return detected, total


def run_evaluation(
    project_dir: str | Path,
    runs_root: str | Path = "artifacts/runs",
    detector_prompt_path: str | Path | None = None,
    detector_model: str = "gpt-5.3-codex",
    detector_reasoning_effort: str = "xhigh",
    results_check_prompt_path: str | Path | None = None,
    known_mistakes_path: str | Path | None = None,
    checker_output_path: str | Path | None = None,
    results_check_output_path: str | Path | None = None,
    results_check_model: str = "gpt-5.4-mini",
    results_check_reasoning_effort: str = "medium",
    detector_prompt_editor_prompt_path: str | Path | None = None,
    current_detector_prompt_path: str | Path | None = None,
    detector_prompt_changelog_path: str | Path | None = None,
    detector_prompt_editor_model: str = "gpt-5.3-codex",
    detector_prompt_editor_reasoning_effort: str = "high",
    preprocessing_editor_prompt_path: str | Path | None = None,
    analysis_process_log_path: str | Path | None = None,
    preprocessing_editor_model: str = "gpt-5.3-codex",
    preprocessing_editor_reasoning_effort: str = "high",
    usage_stats_path: str | Path | None = None,
) -> Path:
    """Run evaluation loop.

    Current implementation runs one detect/evaluate iteration only.
    """
    project_root = Path(project_dir).expanduser().resolve()
    runs_root_path = Path(runs_root).expanduser().resolve()

    _log("Starting evaluation loop (1 iteration for now).")
    resolved_usage_stats_path = (
        Path(usage_stats_path).expanduser().resolve()
        if usage_stats_path is not None
        else None
    )
    run_dir = run_main_cycle(
        project_dir=project_root,
        runs_root=runs_root_path,
        run_detector=True,
        detector_prompt_path=detector_prompt_path,
        detector_model=detector_model,
        detector_reasoning_effort=detector_reasoning_effort,
        usage_stats_path=resolved_usage_stats_path,
    )
    if resolved_usage_stats_path is None:
        resolved_usage_stats_path = run_dir / "codex_usage.json"
    _log("Running detector results check.")
    resolved_known_mistakes = (
        Path(known_mistakes_path).expanduser().resolve()
        if known_mistakes_path is not None
        else project_root / "known_mistakes.md"
    )
    resolved_checker_output = (
        Path(checker_output_path).expanduser().resolve()
        if checker_output_path is not None
        else run_dir / "analisys_report.json"
    )
    resolved_results_check_output = (
        Path(results_check_output_path).expanduser().resolve()
        if results_check_output_path is not None
        else run_dir / "analisys_report_check.json"
    )
    run_results_check(
        run_dir=run_dir,
        known_mistakes_path=resolved_known_mistakes,
        checker_output_path=resolved_checker_output,
        output_json_path=resolved_results_check_output,
        prompt_path=results_check_prompt_path,
        model=results_check_model,
        reasoning_effort=results_check_reasoning_effort,
        usage_stats_path=resolved_usage_stats_path,
    )
    detected, total = _calculate_detected_total(resolved_results_check_output)
    _log(f"Known mistakes detected: {detected}/{total}")
    resolved_current_detector_prompt = (
        Path(current_detector_prompt_path).expanduser().resolve()
        if current_detector_prompt_path is not None
        else Path(__file__).resolve().parents[3] / "prompts" / "detector.md"
    )
    resolved_detector_prompt_changelog = (
        Path(detector_prompt_changelog_path).expanduser().resolve()
        if detector_prompt_changelog_path is not None
        else Path(__file__).resolve().parents[3]
        / "evaluation"
        / "detector_prompt_changelog.md"
    )
    _log("Running detector prompt editor.")
    run_detector_prompt_editor(
        known_mistakes_path=resolved_known_mistakes,
        results_check_output_path=resolved_results_check_output,
        current_detector_prompt_path=resolved_current_detector_prompt,
        changelog_path=resolved_detector_prompt_changelog,
        prompt_path=detector_prompt_editor_prompt_path,
        model=detector_prompt_editor_model,
        reasoning_effort=detector_prompt_editor_reasoning_effort,
        usage_stats_path=resolved_usage_stats_path,
    )
    resolved_analysis_process_log = (
        Path(analysis_process_log_path).expanduser().resolve()
        if analysis_process_log_path is not None
        else run_dir / "analysis_process.md"
    )
    _log("Running preprocessing editor.")
    run_preprocessing_editor(
        analysis_process_log_path=resolved_analysis_process_log,
        prompt_path=preprocessing_editor_prompt_path,
        model=preprocessing_editor_model,
        reasoning_effort=preprocessing_editor_reasoning_effort,
        usage_stats_path=resolved_usage_stats_path,
    )
    _log(f"Iteration 1 completed. Run directory: {run_dir}")
    _log("Evaluation loop completed.")
    return run_dir


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run detector evaluation loop (single iteration for now).",
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to KiCad project directory.",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("artifacts/runs"),
        help="Directory where run subdirectories are created (default: artifacts/runs).",
    )
    parser.add_argument(
        "--detector-prompt",
        type=Path,
        default=None,
        help="Path to detector prompt template (default: prompts/detector.md).",
    )
    parser.add_argument(
        "--detector-model",
        type=str,
        default="gpt-5.3-codex",
        help="Model to use for detector (default: gpt-5.3-codex).",
    )
    parser.add_argument(
        "--detector-reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        default="xhigh",
        help="Reasoning effort for detector model (default: xhigh).",
    )
    parser.add_argument(
        "--results-check-prompt",
        type=Path,
        default=None,
        help="Path to results-check prompt template (default: prompts/results_check.md).",
    )
    parser.add_argument(
        "--known-mistakes-path",
        type=Path,
        default=None,
        help="Path to known mistakes file (default: <project_dir>/known_mistakes.md).",
    )
    parser.add_argument(
        "--checker-output-path",
        type=Path,
        default=None,
        help="Path to schematic checker output (default: <run_dir>/analisys_report.json).",
    )
    parser.add_argument(
        "--results-check-output-path",
        type=Path,
        default=None,
        help="Path for results-check output JSON (default: <run_dir>/analisys_report_check.json).",
    )
    parser.add_argument(
        "--results-check-model",
        type=str,
        default="gpt-5.4-mini",
        help="Model to use for results checker (default: gpt-5.4-mini).",
    )
    parser.add_argument(
        "--results-check-reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        default="medium",
        help="Reasoning effort for results checker model (default: medium).",
    )
    parser.add_argument(
        "--detector-prompt-editor-prompt",
        type=Path,
        default=None,
        help="Path to detector prompt editor template (default: prompts/detector_prompt_editor.md).",
    )
    parser.add_argument(
        "--current-detector-prompt-path",
        type=Path,
        default=None,
        help="Path to current detector prompt (default: prompts/detector.md).",
    )
    parser.add_argument(
        "--detector-prompt-changelog-path",
        type=Path,
        default=None,
        help="Path to detector prompt editor changelog markdown (default: evaluation/detector_prompt_changelog.md).",
    )
    parser.add_argument(
        "--detector-prompt-editor-model",
        type=str,
        default="gpt-5.3-codex",
        help="Model to use for detector prompt editor (default: gpt-5.3-codex).",
    )
    parser.add_argument(
        "--detector-prompt-editor-reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        default="high",
        help="Reasoning effort for detector prompt editor model (default: high).",
    )
    parser.add_argument(
        "--preprocessing-editor-prompt",
        type=Path,
        default=None,
        help="Path to preprocessing editor template (default: prompts/preprocessing_editor.md).",
    )
    parser.add_argument(
        "--analysis-process-log-path",
        type=Path,
        default=None,
        help="Path to analysis process log (default: <run_dir>/analysis_process.md).",
    )
    parser.add_argument(
        "--preprocessing-editor-model",
        type=str,
        default="gpt-5.3-codex",
        help="Model to use for preprocessing editor (default: gpt-5.3-codex).",
    )
    parser.add_argument(
        "--preprocessing-editor-reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        default="high",
        help="Reasoning effort for preprocessing editor model (default: high).",
    )
    parser.add_argument(
        "--usage-stats-path",
        type=Path,
        default=None,
        help="Path to JSON file for codex token usage stats (default: <run_dir>/codex_usage.json).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    run_dir = run_evaluation(
        project_dir=args.project_dir,
        runs_root=args.runs_root,
        detector_prompt_path=args.detector_prompt,
        detector_model=args.detector_model,
        detector_reasoning_effort=args.detector_reasoning_effort,
        results_check_prompt_path=args.results_check_prompt,
        known_mistakes_path=args.known_mistakes_path,
        checker_output_path=args.checker_output_path,
        results_check_output_path=args.results_check_output_path,
        results_check_model=args.results_check_model,
        results_check_reasoning_effort=args.results_check_reasoning_effort,
        detector_prompt_editor_prompt_path=args.detector_prompt_editor_prompt,
        current_detector_prompt_path=args.current_detector_prompt_path,
        detector_prompt_changelog_path=args.detector_prompt_changelog_path,
        detector_prompt_editor_model=args.detector_prompt_editor_model,
        detector_prompt_editor_reasoning_effort=args.detector_prompt_editor_reasoning_effort,
        preprocessing_editor_prompt_path=args.preprocessing_editor_prompt,
        analysis_process_log_path=args.analysis_process_log_path,
        preprocessing_editor_model=args.preprocessing_editor_model,
        preprocessing_editor_reasoning_effort=args.preprocessing_editor_reasoning_effort,
        usage_stats_path=args.usage_stats_path,
    )
    print(f"Evaluation run directory: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
