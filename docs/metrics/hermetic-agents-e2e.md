# Hermetic Agents E2E Result

Status: `success`

Verdict: `test_writer_fault`

The code writer saw only `spec/problem.md` and `guides/code-writer.md`.
The test writer saw only `spec/problem.md` and `guides/test-writer.md`.
The QA arbiter saw both outputs and a hidden oracle.

Disagreement assigned to `test_writer`:

```json
{
  "blame": "test_writer",
  "case": "uppercase-name",
  "implementation": {
    "name": "gizmo",
    "quantity": 4,
    "unit_cents": 200
  },
  "line": "Gizmo:4@2.00",
  "oracle_expected": {
    "name": "gizmo",
    "quantity": 4,
    "unit_cents": 200
  },
  "test_expected": {
    "name": "Gizmo",
    "quantity": 4,
    "unit_cents": 200
  }
}
```
