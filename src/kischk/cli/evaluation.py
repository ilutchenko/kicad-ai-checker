from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from kischk.cli.check_schematic import run_main_cycle


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[kischk-eval {timestamp}] {message}", flush=True)


def run_evaluation(
    project_dir: str | Path,
    runs_root: str | Path = "artifacts/runs",
    detector_prompt_path: str | Path | None = None,
    detector_model: str = "gpt-5.3-codex",
    detector_reasoning_effort: str = "xhigh",
) -> Path:
    """Run evaluation loop.

    Current implementation runs one detect/evaluate iteration only.
    """
    project_root = Path(project_dir).expanduser().resolve()
    runs_root_path = Path(runs_root).expanduser().resolve()

    _log("Starting evaluation loop (1 iteration for now).")
    run_dir = run_main_cycle(
        project_dir=project_root,
        runs_root=runs_root_path,
        run_detector=True,
        detector_prompt_path=detector_prompt_path,
        detector_model=detector_model,
        detector_reasoning_effort=detector_reasoning_effort,
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
    )
    print(f"Evaluation run directory: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
