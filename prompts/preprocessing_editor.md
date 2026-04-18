This project checks KiCad schematic correctness using an external LLM API.

You are an editor of preprocessing tools located in `src/kischk/kicad`.

The detector LLM sometimes creates ad hoc scripts to further analyze the preprocessed schematic JSON.
This indicates that the preprocessing output is missing derived data that should be computed in Python beforehand.

Your task is to improve preprocessing so the detector can do more reasoning directly from the prepared JSON and spend fewer tokens on custom analysis scripts.

You can use:
1. source code in `src/kischk/kicad`
2. `analysis_process.md` from the latest detector run
3. KiCad file format docs in `kicad-dev-docs/`

## Objective
Improve preprocessing to make downstream LLM detection:
- more accurate
- more efficient in tokens
- less dependent on ad hoc scripts
- more structured and easier to reason over

## What to look for in analysis_process.md
Identify:
- repeated manual inspections
- repeated script patterns
- data the detector had to derive itself
- missing summaries or indexes
- missing normalized component or pin metadata
- missing net relationship information
- missing functional grouping

## Preferred preprocessing improvements
Add derived data such as:
- power net classification
- ground net classification
- pin electrical role summaries
- per-component connection summaries
- per-net endpoint summaries
- driver/load style summaries where possible
- decoupling/support-network detection
- pull-up/pull-down detection
- regulator feedback network summaries
- connector signal grouping
- suspicious floating or single-ended nets
- component value normalization
- footprint/package normalization
- cross-links that reduce long JSON traversal

Prefer adding deterministic computed fields over adding raw duplicated data.

## Constraints
- Keep the output machine-readable and LLM-friendly
- Preserve backward compatibility where reasonable
- Avoid unnecessary schema bloat
- Favor stable, reusable derived features over case-specific heuristics

## Required deliverables
After making code changes:
1. update the preprocessing implementation
2. provide a concise changelog
3. explain which detector scripts or repeated detector actions this change eliminates or simplifies
4. add or update tests if the repository has a test framework

Here are locations of analisys_process.md file:
