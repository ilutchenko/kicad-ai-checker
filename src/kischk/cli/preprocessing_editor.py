from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from kischk.cli.codex_usage import run_codex_exec


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[kischk-preprocessing-editor {timestamp}] {message}", flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_prompt_path() -> Path:
    return _repo_root() / "prompts" / "preprocessing_editor.md"


def _build_prompt(prompt_template: str, analysis_process_log_path: Path) -> str:
    return (
        prompt_template.rstrip()
        + "\n\n"
        + f"analysis_process.md path: {analysis_process_log_path}\n"
    )


def run_preprocessing_editor(
    analysis_process_log_path: str | Path,
    prompt_path: str | Path | None = None,
    model: str = "gpt-5.3-codex",
    reasoning_effort: str = "high",
    usage_stats_path: str | Path | None = None,
) -> Path:
    resolved_analysis_process_log = Path(analysis_process_log_path).expanduser().resolve()

    resolved_prompt = (
        Path(prompt_path).expanduser().resolve()
        if prompt_path is not None
        else _default_prompt_path()
    )

    _log(f"Using prompt template: {resolved_prompt}")
    prompt_template = resolved_prompt.read_text(encoding="utf-8")
    full_prompt = _build_prompt(
        prompt_template=prompt_template,
        analysis_process_log_path=resolved_analysis_process_log,
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
    _log(f"Running preprocessing editor command: {' '.join(command)}")
    _log("Streaming codex preprocessing-editor output:")
    run_codex_exec(
        command=command,
        prompt=full_prompt,
        log=_log,
        usage_stats_path=usage_stats_path,
        usage_step="preprocessing_editor",
        model=model,
        reasoning_effort=reasoning_effort,
    )

    _log("Preprocessing editor completed.")
    return resolved_analysis_process_log


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run preprocessing editor via codex exec.",
    )
    parser.add_argument(
        "--analysis-process-log-path",
        type=Path,
        required=True,
        help="Path to analysis process markdown log (example: run_dir/analysis_process.md).",
    )
    parser.add_argument(
        "--prompt-path",
        type=Path,
        default=None,
        help="Path to editor prompt template (default: prompts/preprocessing_editor.md).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5.3-codex",
        help="Codex model for preprocessing editor (default: gpt-5.3-codex).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        default="high",
        help="Reasoning effort for model (default: high).",
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

    analysis_log = run_preprocessing_editor(
        analysis_process_log_path=args.analysis_process_log_path,
        prompt_path=args.prompt_path,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        usage_stats_path=args.usage_stats_path,
    )
    print(f"Preprocessing editor analysis log path: {analysis_log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
