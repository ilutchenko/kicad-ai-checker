from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Callable


_TOKEN_KEYS = {
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "reasoning_tokens",
    "prompt_tokens",
    "completion_tokens",
}


def run_codex_exec(
    command: list[str],
    prompt: str,
    log: Callable[[str], None],
    usage_stats_path: str | Path | None = None,
    usage_step: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> None:
    resolved_usage_path = (
        Path(usage_stats_path).expanduser().resolve()
        if usage_stats_path is not None
        else None
    )

    effective_command = list(command)
    if resolved_usage_path is not None and "--json" not in effective_command:
        effective_command.insert(2, "--json")

    proc = subprocess.Popen(
        effective_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("Failed to start codex process with piped IO")

    proc.stdin.write(prompt)
    proc.stdin.close()

    output_lines: list[str] = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        output_lines.append(line)

    returncode = proc.wait()
    output_text = "".join(output_lines)

    if resolved_usage_path is not None:
        usage = _extract_usage_from_jsonl(output_text)
        _append_usage_record(
            usage_path=resolved_usage_path,
            step=usage_step,
            model=model,
            reasoning_effort=reasoning_effort,
            command=effective_command,
            usage=usage,
        )
        if usage is None:
            log("Token usage was not found in codex JSON output.")
        else:
            summary = ", ".join(f"{k}={v}" for k, v in sorted(usage.items()))
            log(f"Token usage: {summary}")

    if returncode != 0:
        raise RuntimeError(f"codex exec failed with exit code {returncode}")


def _append_usage_record(
    usage_path: Path,
    step: str | None,
    model: str | None,
    reasoning_effort: str | None,
    command: list[str],
    usage: dict[str, int] | None,
) -> None:
    usage_path.parent.mkdir(parents=True, exist_ok=True)

    if usage_path.exists():
        data = json.loads(usage_path.read_text(encoding="utf-8"))
    else:
        data = {"calls": []}

    calls = data.get("calls")
    if not isinstance(calls, list):
        calls = []

    calls.append(
        {
            "step": step,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "command": command,
            "usage": usage,
        }
    )

    data["calls"] = calls
    usage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _extract_usage_from_jsonl(text: str) -> dict[str, int] | None:
    best: dict[str, int] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue

        for candidate in _find_usage_candidates(payload):
            normalized = _normalize_usage(candidate)
            if not normalized:
                continue
            best = _select_better_usage(best, normalized)

    return best


def _find_usage_candidates(obj: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    if isinstance(obj, dict):
        usage = obj.get("usage")
        if isinstance(usage, dict):
            out.append(usage)

        if any(key in obj for key in _TOKEN_KEYS):
            out.append(obj)

        for value in obj.values():
            out.extend(_find_usage_candidates(value))
    elif isinstance(obj, list):
        for value in obj:
            out.extend(_find_usage_candidates(value))

    return out


def _normalize_usage(candidate: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for key in _TOKEN_KEYS:
        value = candidate.get(key)
        if isinstance(value, int):
            out[key] = value
        elif isinstance(value, float):
            out[key] = int(value)
    return out


def _select_better_usage(
    current: dict[str, int] | None,
    new: dict[str, int],
) -> dict[str, int]:
    if current is None:
        return new

    current_total = current.get("total_tokens", -1)
    new_total = new.get("total_tokens", -1)
    if new_total > current_total:
        return new
    if new_total == current_total and len(new) > len(current):
        return new
    return current
