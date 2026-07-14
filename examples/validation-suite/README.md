# AutomationML Validation Suite

This folder contains ready-to-upload AML examples for the AutomationML editor.
Every case is serialized twice:

- `json/*.json` for AML JSON import
- `xml/*.aml` for AML XML import

`manifest.json` lists the expected validation result for every file. The SDK
tests consume these same public examples, so the files are both demo material
and regression coverage.

In the manifest, `expected_valid` means "no validation errors". Some positive
cases intentionally include warning-level AML best-practice findings. Cases
marked as warning are valid AML documents that exist specifically to demonstrate
non-blocking inheritance and class-realization guidance.

Warning-focused filenames follow `size_domain_polarity_focus`, using hyphens
inside each part when a part contains multiple words. For example:
`small_robot-cell_warning_missing-inherited-attribute`.

## Catalog

| Case | Size | Expected | Purpose |
| --- | --- | --- | --- |
| `small-valid-motor` | small | valid | Minimal resolved motor example. |
| `small-invalid-unresolved-references` | small | invalid | Unresolved system unit, role, interface, and attribute type paths. |
| `small_robot-cell_warning_missing-inherited-attribute` | small | valid with warnings | Focused inherited `cycleTime` attribute materialization warning. |
| `medium-valid-robot-cell` | medium | valid | Clean robot cell with lean interfaces and a deep `Asset -> Cell -> RobotModule` attribute chain. |
| `medium_robot-cell_warning_missing-inherited-attribute-and-class-interface` | medium | valid with warnings | Explicit missing inherited attributes and missing class interfaces on instances. |
| `medium-invalid-duplicates-and-links` | medium | invalid | Duplicate IDs, duplicate class paths, missing role, and broken internal link. |
| `big-valid-packaging-line` | big | valid with warnings | Multi-cell packaging line for graph/tree scalability and warning checks. |
| `big-invalid-mixed-references` | big | invalid with warnings | Larger mixed-reference failure set with duplicate IDs, broken links, and warning coverage. |

## Regenerate

Run this from `automationml-sdk` after changing the example definitions:

```bash
$env:PYTHONPATH=".\src"; .\.venv\Scripts\python.exe .\tools\generate_validation_examples.py
```

Then run the SDK tests to verify that JSON and XML stay in sync.
