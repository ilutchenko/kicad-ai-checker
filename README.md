# kischk

KiCad schematic checker (early stage).

Current code implements two foundational modules:
- `project loader`: discovers root schematic and resolves hierarchical sheets.
- `schematic parser`: parses `.kicad_sch` S-expressions into an AST.

## Module: Project Loader

Path: `src/kischk/kicad/project.py`

### Purpose
Build a deterministic list of schematic files that belong to a project, starting from a project root directory.

### Main API
- `load_project(project_root: str | Path) -> LoadedProject`

### Input
- `project_root`: filesystem path to KiCad project directory.

### Output
`LoadedProject` dataclass:
- `project_root: Path`
- `project_file: Path | None`
- `root_schematic: Path`
- `schematic_files: tuple[Path, ...]`
- `hierarchy: dict[Path, tuple[Path, ...]]` where key is parent schematic and value is child sheet schematic files.

### How it works
1. Validate `project_root` exists and is a directory.
2. Select `.kicad_pro` file:
- if exactly one exists, use it
- if multiple exist, try `<dir_name>.kicad_pro`
- otherwise raise `ProjectLoaderError`
3. Select root `.kicad_sch`:
- if project file exists, expect same basename (`<project>.kicad_sch`)
- if no project file, infer from available `.kicad_sch` files (single file or `<dir_name>.kicad_sch`)
4. Recursively scan each schematic for hierarchical sheet references:
- locate `(sheet ...)` blocks
- read `(property "Sheetfile" "...")`
- resolve child path relative to parent schematic directory
5. Validate each referenced child exists.
6. Detect cyclic sheet hierarchy and raise `ProjectLoaderError`.

### Error model
Raises `ProjectLoaderError` for:
- missing/invalid project root
- ambiguous or missing root project/schematic
- missing referenced child sheet files
- cyclic hierarchy
- malformed sheet block parentheses

## Module: Schematic Parser (AST)

Path: `src/kischk/kicad/sch_parser.py` and `src/kischk/kicad/sch_model.py`

### Purpose
Parse KiCad S-expression text into a typed AST for further analysis (connectivity, semantic checks, reporting).

### Main API
- `parse_schematic_file(path: str | Path) -> ParsedSchematic`
- `parse_loaded_project(loaded: LoadedProject) -> ParsedProject`
- `parse_project(project_root: str | Path) -> ParsedProject` (loader + parser shortcut)
- `parse_sexpr(text: str, source: Path | None = None) -> SExprList`

### Input
- Single schematic file path (`parse_schematic_file`), or
- `LoadedProject` object from loader (`parse_loaded_project`), or
- project root path (`parse_project`).

### Output
AST dataclasses from `sch_model.py`:
- `SExprAtom(value: str, quoted: bool)`
- `SExprList(items: tuple[SExprNode, ...])`
- `ParsedSchematic(path: Path, root: SExprList)`
- `ParsedProject(schematics: tuple[ParsedSchematic, ...])`

### Parser behavior
- Supports nested lists, symbols, quoted strings, comments (`; ...`), and whitespace.
- Preserves string-vs-symbol distinction via `quoted` flag on atoms.
- Validates schematic top-level node starts with `kicad_sch`.
- Produces precise parse errors with `file:line:column`.

### Error model
Raises `SchematicParseError` for:
- invalid S-expression syntax (unexpected EOF, trailing content, unterminated string, etc.)
- invalid root node (not `kicad_sch`)

## End-to-end data flow

1. `load_project(project_root)` discovers all related schematic files.
2. `parse_loaded_project(loaded)` parses each file into AST.
3. Resulting `ParsedProject` becomes input for future phases:
- typed schematic model extraction
- connectivity graph construction
- LLM-assisted checks
- report generation

## Minimal usage example

```python
from kischk.kicad.project import load_project
from kischk.kicad.sch_parser import parse_loaded_project

loaded = load_project("test_kicad_project")
parsed = parse_loaded_project(loaded)

print(loaded.root_schematic)
print(len(loaded.schematic_files))
print(parsed.schematics[0].root.items[0])  # SExprAtom("kicad_sch", quoted=False)
```

## Current tests

- `tests/test_project_loader.py`
- `tests/test_sch_parser.py`

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
