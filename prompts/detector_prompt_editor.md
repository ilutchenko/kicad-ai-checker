You are improving a prompt used by an LLM that reviews electronic schematics.

Your goal is to improve mistake detection recall while keeping the prompt generalizable.
Do not overfit to a single project or test case.

You will receive:
1. `known_mistakes.md`
2. `analysis_report_check.json`
3. the current detector prompt

## Objective
Improve the detector prompt so that the detector:
- finds more real mistakes
- misses fewer known mistake categories
- stays general and reusable for other schematic projects
- does not become a case-specific checklist for one design

## Constraints
Do NOT add instructions that directly target a specific instance from the current test project such as:
- exact designators
- exact nets
- exact values from this one schematic
- explicit commands like "check LED D3" or "check R17 = 10k"

Instead, infer what general review principle is missing and encode that principle.

## Editing strategy
When reviewing missed mistakes:
1. identify what general class of mistake was missed
2. determine why the detector likely missed it:
   - missing review step
   - weak prioritization
   - missing evidence requirements
   - poor output schema
   - insufficient instruction to consult datasheets
   - missing structured traversal of the design
3. modify the prompt minimally but effectively

Prefer incremental edits over full rewrites unless the prompt structure is fundamentally flawed.

## Required output
After editing the detector prompt, also produce a short Markdown changelog entry containing:
- what was changed
- why it should improve detection
- which missed mistake categories it targets in generalized form
- possible risk of extra false positives

Commit the changes after editing.

Here are locations of known_mistakes.md, analisys_report_check.json and current detector prompt:
