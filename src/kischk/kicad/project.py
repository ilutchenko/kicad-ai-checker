from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Set


SHEET_START_RE = re.compile(r"\(sheet\b")
SHEET_FILE_RE = re.compile(r'\(property\s+"Sheetfile"\s+"([^"\\]*(?:\\.[^"\\]*)*)"')


class ProjectLoaderError(RuntimeError):
    """Raised when project loading fails."""


@dataclass(frozen=True)
class LoadedProject:
    project_root: Path
    project_file: Path | None
    root_schematic: Path
    schematic_files: tuple[Path, ...]
    hierarchy: dict[Path, tuple[Path, ...]]


def load_project(project_root: str | Path) -> LoadedProject:
    """Load a KiCad project and resolve hierarchical sheet schematic files."""
    root = Path(project_root).expanduser().resolve()
    if not root.exists():
        raise ProjectLoaderError(f"Project root does not exist: {root}")
    if not root.is_dir():
        raise ProjectLoaderError(f"Project root must be a directory: {root}")

    project_file = _select_project_file(root)
    root_schematic = _select_root_schematic(root, project_file)

    ordered: List[Path] = []
    hierarchy: Dict[Path, List[Path]] = {}
    visited: Set[Path] = set()

    def walk(current: Path, stack: List[Path]) -> None:
        current = current.resolve()
        if current in stack:
            cycle_start = stack.index(current)
            chain = " -> ".join(str(p) for p in [*stack[cycle_start:], current])
            raise ProjectLoaderError(f"Cyclic hierarchy detected: {chain}")
        if current in visited:
            return

        if not current.exists():
            raise ProjectLoaderError(f"Schematic file does not exist: {current}")
        if not current.is_file():
            raise ProjectLoaderError(f"Schematic path is not a file: {current}")

        visited.add(current)
        ordered.append(current)

        next_stack = [*stack, current]
        children = _extract_sheet_files(current)

        resolved_children: List[Path] = []
        for child in children:
            child_path = (current.parent / child).resolve()
            resolved_children.append(child_path)
            walk(child_path, next_stack)

        hierarchy[current] = resolved_children

    walk(root_schematic, [])

    normalized_hierarchy = {k: tuple(v) for k, v in hierarchy.items()}
    return LoadedProject(
        project_root=root,
        project_file=project_file,
        root_schematic=root_schematic,
        schematic_files=tuple(ordered),
        hierarchy=normalized_hierarchy,
    )


def _select_project_file(project_root: Path) -> Path | None:
    project_files = sorted(project_root.glob("*.kicad_pro"))
    if not project_files:
        return None
    if len(project_files) == 1:
        return project_files[0].resolve()

    by_dirname = project_root / f"{project_root.name}.kicad_pro"
    if by_dirname.exists():
        return by_dirname.resolve()

    names = ", ".join(p.name for p in project_files)
    raise ProjectLoaderError(
        f"Multiple .kicad_pro files in {project_root}: {names}. "
        "Please keep only one project file in the root."
    )


def _select_root_schematic(project_root: Path, project_file: Path | None) -> Path:
    if project_file is not None:
        candidate = project_file.with_suffix(".kicad_sch")
        if candidate.exists():
            return candidate.resolve()

        raise ProjectLoaderError(
            "Could not locate root schematic for project file "
            f"{project_file}. Expected {candidate.name} in {project_root}."
        )

    schematics = sorted(project_root.glob("*.kicad_sch"))
    if not schematics:
        raise ProjectLoaderError(f"No .kicad_sch files found in {project_root}")
    if len(schematics) == 1:
        return schematics[0].resolve()

    by_dirname = project_root / f"{project_root.name}.kicad_sch"
    if by_dirname.exists():
        return by_dirname.resolve()

    names = ", ".join(p.name for p in schematics)
    raise ProjectLoaderError(
        f"Multiple .kicad_sch files in {project_root}: {names}. "
        "Could not infer root schematic."
    )


def _extract_sheet_files(schematic_file: Path) -> list[str]:
    text = schematic_file.read_text(encoding="utf-8")
    sheet_files: List[str] = []

    for match in SHEET_START_RE.finditer(text):
        block = _slice_balanced_block(text, match.start())
        if block is None:
            raise ProjectLoaderError(
                f"Unbalanced parentheses in sheet block of {schematic_file}"
            )

        file_match = SHEET_FILE_RE.search(block)
        if file_match is None:
            continue

        value = _unescape_kicad_string(file_match.group(1)).strip()
        if value:
            sheet_files.append(value)

    return sheet_files


def _slice_balanced_block(text: str, start: int) -> str | None:
    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def _unescape_kicad_string(value: str) -> str:
    return value.replace(r'\"', '"').replace(r"\\", "\\")
