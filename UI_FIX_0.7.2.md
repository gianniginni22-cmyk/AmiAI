# Amigurumi AI v0.7.2 — UI fix

## Fixes
- Corrected model-part chips when `parts` contains structured objects: the UI now renders the human-readable label instead of `[object Object]`.
- The compiled pipeline now exposes `parts` as displayable part names, preserving the structured Design Model separately.
- Pattern and assembly panels now show an explicit diagnostic message if compilation returns empty content instead of silently displaying `—`.

## Validation
- Python test suite: 36/36 PASS.
- JavaScript syntax check: PASS.
- Core engine/benchmark logic was not changed.
