You compare a known mistakes list against the output of our schematic checker.

Your task is semantic matching, not string matching.
Mistake names and wording may differ. Focus on whether the checker identified the same underlying issue.

Inputs:
1. known mistakes file
2. schematic checker output report
3. output path for your result JSON

## Matching rules
A known mistake is considered detected if the checker output clearly identifies the same underlying technical issue, even if:
- the name is different
- the wording is different
- the scope is broader or narrower, but still clearly includes that mistake

A known mistake is NOT detected if:
- the checker only mentions something vaguely related
- the checker reports a consequence, but not the actual mistake
- the checker output is too ambiguous to confidently map to the known mistake

## Output
Write a JSON file with this exact structure:

{
  "mistakes": [
    {
      "name": "<mistake name from known mistakes list>",
      "detected": true,
      "matched_report_items": ["name of matching checker finding 1"],
      "reason": "short explanation of why this known mistake is considered detected or not detected"
    }
  ],
  "summary": {
    "total": 0,
    "detected": 0,
    "missed": 0
  }
}

Use boolean true/false, not strings.
Be strict but fair.

Here are locations of: known mistakes file, output of schematic checker, your output json:
