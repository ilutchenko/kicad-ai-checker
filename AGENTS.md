
# Description of the project

This is a project that will check KiCad schematic correctness using external LLM API.
It's a python project, aiming to work with .kicad_sch files.
In kicad-dev-docs/ you can find docs describing kicad files formats.
In test_kicad_project/ you can find an example of the real kicad project.
Update .gitignore file when needed. 

Here is approximate but not strict plan of the project realization.
### Phase A — Core analyzer (no KiCad UI integration yet)

Goal: reliably detect electrical/semantic mistakes from schematic sources.

1. **Project loader**
    
    - Input: project root, find root schematic, resolve hierarchical sheets.
    - Note: each sheet is its own `.kicad_sch` file in hierarchical designs.
2. **Parser / model builder**
    
    - Parse `.kicad_sch` S-expressions into an AST (preserve UUIDs, positions, fields, pins, nets).
    - Use KiCad’s file format docs as the ground truth.
3. **Connectivity extraction**    
    - Build a **net graph**: pins ↔ wires ↔ labels ↔ hierarchical ports.
    - Normalize names (power symbols, global labels, hierarchical labels).
4. **LLM-assisted checks**
        - Summarize local context (component + immediate nets + reference designators).
        - Ask LLM for “expected connections” templates (e.g., MCU typical app circuit), or interpret datasheet constraints when available.
5. **Report format**
    - JSON for machine use + human-readable Markdown/HTML.
    - Include stable identifiers so UI can highlight/zoom later.

### Phase B — “Plugin” UX (minimal viable integration)

Goal: user runs checks from inside KiCad.

Options in order of practicality:

1. **Action Plugin in PCB Editor that runs the analyzer**
    
    - Even though it’s schematic-focused, you can still provide a KiCad entry point (Tools menu) using the existing plugin mechanism in KiCad.
    - It launches your analyzer, points it at the current project directory, then shows results in a dialog (and/or opens the report).
2. **IPC-based integration (schematic-aware UI later)**
    
    - As IPC matures, use it to query active document, navigate sheets, and highlight items. The IPC API is specifically intended to enable plug-ins and remote control, but it’s still evolving.

### Phase C — Deep KiCad integration

- Jump-to-marker inside schematic (by UUID), annotate graphics, quick-fixes (add missing caps, swap nets, etc.).
- This will likely depend on IPC capabilities for `eeschema` as they stabilize.

## 3) Source code structure (approximate)

A structure that cleanly separates KiCad specifics, analysis, and UI:

```
kicad-schematic-checker/
  pyproject.toml
  README.md

  src/kischk/
    __init__.py

    cli/
      main.py              # `kischk check path/to/project`
      args.py
      output_formats.py    # json, md, html

    kicad/
      project.py           # locate root sheet, resolve hierarchy
      sch_parser.py        # parse .kicad_sch s-expr -> AST
      sch_model.py         # typed model objects (Symbol, Pin, Wire, Label...)
      connectivity.py      # build net graph
      coords.py            # sheet transforms, positions, bounding boxes

    llm/
      provider.py          # OpenAI/others adapter
      prompts.py
      context.py           # build minimal context from net graph
      datasheets/
        fetch.py           # download/cache datasheets
        parse.py           # (optional) extract tables/constraints

    report/
      schema.py            # Finding, Location, Evidence
      render_md.py
      render_html.py

    integrations/
      kicad_action_plugin/
        __init__.py
        plugin.py          # thin wrapper for KiCad menu entry (pcbnew)
        ui.py              # wx dialogs, show findings
      ipc_client/
        client.py          # future: talk to KiCad IPC server
        proto/             # generated protobuf stubs (pinned versions)

  tests/
    fixtures/
      simple_project/
      hierarchy_project/
    test_parser.py
```
