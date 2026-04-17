from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import json
from typing import Any

from kischk.kicad import (
    ElectricalComponent,
    ElectricalNet,
    ElectricalPin,
    ElectricalProject,
    ElectricalSchematic,
    NetMember,
    build_electrical_project,
)


def _format_timestamp(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return current.strftime("%Y%m%d_%H%M%S")


def _create_run_directory(runs_root: Path, now: datetime | None = None) -> Path:
    timestamp = _format_timestamp(now)
    run_dir = runs_root / timestamp
    suffix = 1

    while run_dir.exists():
        run_dir = runs_root / f"{timestamp}_{suffix:02d}"
        suffix += 1

    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _pin_to_dict(pin: ElectricalPin) -> dict[str, Any]:
    return {
        "pin_number": pin.pin_number,
        "pin_name": pin.pin_name,
        "direction": pin.direction,
        "is_no_connect": pin.is_no_connect,
        "net_id": pin.net_id,
        "net_name": pin.net_name,
    }


def _component_to_dict(component: ElectricalComponent) -> dict[str, Any]:
    return {
        "uuid": component.uuid,
        "reference": component.reference,
        "value": component.value,
        "lib_id": component.lib_id,
        "unit": component.unit,
        "footprint": component.footprint,
        "datasheet": component.datasheet,
        "description": component.description,
        "lcsc": component.lcsc,
        "custom_fields": component.custom_fields,
        "sheet_path": component.sheet_path,
        "schematic_path": str(component.schematic_path),
        "pins": [_pin_to_dict(pin) for pin in component.pins],
    }


def _member_to_dict(member: NetMember) -> dict[str, Any]:
    return {
        "component_uuid": member.component_uuid,
        "reference": member.reference,
        "pin_number": member.pin_number,
    }


def _net_to_dict(net: ElectricalNet) -> dict[str, Any]:
    return {
        "net_id": net.net_id,
        "net_name": net.net_name,
        "members": [_member_to_dict(member) for member in net.members],
        "labels": list(net.labels),
        "is_global": net.is_global,
    }


def _schematic_to_dict(schematic: ElectricalSchematic) -> dict[str, Any]:
    return {
        "path": str(schematic.path),
        "sheet_path": schematic.sheet_path,
        "components": [_component_to_dict(component) for component in schematic.components],
    }


def _project_to_dict(project: ElectricalProject) -> dict[str, Any]:
    return {
        "schematics": [_schematic_to_dict(schematic) for schematic in project.schematics],
        "nets": [_net_to_dict(net) for net in project.nets],
    }


def run_main_cycle(project_dir: str | Path, runs_root: str | Path = "artifacts/runs") -> Path:
    project_root = Path(project_dir).expanduser().resolve()
    runs_root_path = Path(runs_root).expanduser().resolve()

    run_dir = _create_run_directory(runs_root_path)

    electrical = build_electrical_project(project_root)
    output_path = run_dir / "processed_net_graph.json"
    payload = {
        "project_root": str(project_root),
        "run_dir": str(run_dir),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "electrical_project": _project_to_dict(electrical),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return run_dir


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one kischk automation cycle: preprocess project and store outputs.",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    run_dir = run_main_cycle(args.project_dir, runs_root=args.runs_root)
    print(f"Run directory: {run_dir}")
    print(f"Preprocessing output: {run_dir / 'processed_net_graph.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
