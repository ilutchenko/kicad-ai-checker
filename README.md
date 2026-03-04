# kischk

KiCad schematic checker (early stage).

Current code implements two foundational modules:
- `project loader`: discovers root schematic and resolves hierarchical sheets.
- `schematic parser`: parses `.kicad_sch` S-expressions into an AST.
- `netlist module`: exports/parses KiCad netlist (`kicadsexpr`) from the root schematic.
- `electrical builder`: converts AST into compact LLM-ready electrical model (components/pins/nets).

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
3. `build_electrical_project(project_root)` exports/parses KiCad netlist and converts AST to compact electrical model.
4. Resulting `ElectricalProject` becomes input for future phases:
- typed schematic model extraction
- connectivity graph construction
- LLM-assisted checks
- report generation

## Module: Electrical Builder (Compact Model)

Path: `src/kischk/kicad/electrical_builder.py` and `src/kischk/kicad/electrical_model.py`

### Purpose
Reduce verbose KiCad AST into electrical information needed for rule checks and LLM prompts.

### Main API
- `build_electrical_project(project_root: str | Path) -> ElectricalProject`
- `build_electrical_from_parsed(loaded: LoadedProject, parsed: ParsedProject, netlist: NetlistData | None = None) -> ElectricalProject`

### Input
- `LoadedProject` + `ParsedProject`, optionally `NetlistData`.
- In `build_electrical_project`, netlist is auto-loaded:
- prefer `<root_schematic_basename>.net` if present
- otherwise export via `kicad-cli sch export netlist --format kicadsexpr`

### Output
`ElectricalProject` dataclass:
- `schematics: tuple[ElectricalSchematic, ...]`
- `nets: tuple[ElectricalNet, ...]`

`ElectricalSchematic`:
- `path`
- `sheet_path` (hierarchical path like `/Root/STM32`)
- `components`

`ElectricalComponent`:
- `reference`, `value`, `lib_id`, `unit`, `uuid`
- `footprint`, `datasheet`, `description`, `lcsc`, `custom_fields` (non-standard user fields only)
- `pins`

`ElectricalPin`:
- `pin_number`, `pin_name`, `direction`
- `is_no_connect`
- `net_id`, `net_name`

`ElectricalNet`:
- `net_id` from KiCad netlist `code` when netlist is available, otherwise geometry fallback (`N0001`, ...)
- optional `net_name`
- `members` (`reference`, `pin_number`)
- attached `labels`
- `is_global`

### Extraction logic
1. Parse library pin definitions from `lib_symbols` to get pin names/directions/relative coordinates.
2. Parse symbol instances (`symbol`) to build components and pin instances.
3. If netlist is available, assign pin `net_id/net_name` from netlist `(net code/name)` by `(ref, pin)`.
4. If netlist provides `pintype`, use it as pin direction in output.
5. If netlist is unavailable, fallback to geometry connectivity (`wire`, `junction`, labels, hierarchy links).

### Error model
Raises `ElectricalBuildError` for internal model consistency problems (for example, missing parsed schematics or unsupported rotations). Netlist export/parse failures are non-fatal in `build_electrical_project` and trigger geometry fallback.

## Module: Netlist

Path: `src/kischk/kicad/netlist.py`

### Purpose
Get reliable net connectivity from KiCad-generated netlist instead of inferring all nets from graphics primitives.

### Main API
- `export_netlist(schematic_file, output_file, fmt=\"kicadsexpr\") -> Path`
- `load_or_export_project_netlist(project_root) -> NetlistData`
- `parse_netlist_file(path) -> NetlistData`

### Output
- `NetlistData(nets=...)`
- `NetlistNet(code, name, net_class, nodes=...)`
- `NetlistNode(ref, pin, pintype, pinfunction)`

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
- `tests/test_netlist.py`
- `tests/test_electrical_builder.py`

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
