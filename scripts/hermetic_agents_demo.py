#!/usr/bin/env python3
"""Deterministic e2e proof for hermetic agents.

The harness models three locked-down roles:

* a code writer that can read only the problem spec and code guide,
* a test writer that can read only the problem spec and test guide,
* a QA arbiter that can read both outputs plus a hidden oracle.

It intentionally includes one wrong generated test expectation. The QA step must
assign that disagreement to the test writer instead of blindly blaming the
implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


SPEC = """# Problem Spec: invoice token normalizer

Implement `normalize_invoice_line(line: str) -> dict`.

Input is one invoice token in this exact form:

```text
<name>:<quantity>@<unit_price>
```

Rules:

1. `name` is stripped and case-folded.
2. `quantity` is parsed as a base-10 integer and must be greater than zero.
3. `unit_price` is parsed as decimal dollars and rounded to integer cents with
   round-half-up behavior.
4. The return value is a dict with keys `name`, `quantity`, and `unit_cents`.
5. Invalid input raises `ValueError`.
"""


CODE_GUIDE = """# Code Writer Guide

You can read the problem spec and this guide only.

Deliver `solution.py`. Do not read or infer generated tests. Prefer a small,
direct implementation over framework code. Use decimal arithmetic for cents.
"""


TEST_GUIDE = """# Test Writer Guide

You can read the problem spec and this guide only.

Deliver machine-readable test cases and a Python test file. Do not read or infer
the implementation. Cover happy path, whitespace, rounding, and invalid input.
"""


QA_GUIDE = """# QA Arbiter Guide

You can read the spec, both agent outputs, and the hidden oracle.

When implementation behavior disagrees with a generated test, compare both sides
with the spec oracle. Assign blame to the implementation, test writer, both, or
the spec. Do not reveal hidden cases to the writer agents.
"""


SOLUTION = '''from decimal import Decimal, ROUND_HALF_UP


def normalize_invoice_line(line: str) -> dict:
    try:
        name_part, rest = line.split(":", 1)
        quantity_part, price_part = rest.split("@", 1)
        name = name_part.strip().casefold()
        quantity = int(quantity_part.strip())
        cents = int(
            (Decimal(price_part.strip()) * Decimal("100")).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
    except Exception as exc:
        raise ValueError(f"invalid invoice line: {line!r}") from exc

    if not name or quantity <= 0 or cents < 0:
        raise ValueError(f"invalid invoice line: {line!r}")

    return {"name": name, "quantity": quantity, "unit_cents": cents}
'''


TEST_CASES = [
    {
        "id": "basic",
        "line": "widget:2@3.50",
        "expected": {"name": "widget", "quantity": 2, "unit_cents": 350},
    },
    {
        "id": "round-half-up",
        "line": "bolt:1@1.005",
        "expected": {"name": "bolt", "quantity": 1, "unit_cents": 101},
    },
    {
        "id": "uppercase-name",
        "line": "Gizmo:4@2.00",
        # Intentional test-writer bug: the spec says names are case-folded.
        "expected": {"name": "Gizmo", "quantity": 4, "unit_cents": 200},
    },
]


TEST_FILE = '''import importlib.util
from pathlib import Path


CASES = {cases_json}


def load_solution():
    path = Path(__file__).with_name("solution.py")
    spec = importlib.util.spec_from_file_location("solution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_cases():
    solution = load_solution()
    for case in CASES:
        assert solution.normalize_invoice_line(case["line"]) == case["expected"]
'''


HIDDEN_CASES = [
    {"id": "hidden-whitespace-casefold", "line": "  Widget XL  :3@10.235"},
    {"id": "hidden-small-rounding", "line": "nut:9@0.015"},
]


@dataclass(frozen=True)
class Artifact:
    logical_path: str
    digest: str
    bytes: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_for(path: Path, root: Path) -> Artifact:
    data = path.read_bytes()
    return Artifact(
        logical_path=path.relative_to(root).as_posix(),
        digest=sha256_bytes(data),
        bytes=len(data),
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def forbidden_inputs_for(role: str) -> list[str]:
    if role == "code_writer":
        return [
            "outputs/test_writer/test_cases.json",
            "outputs/test_writer/test_solution.py",
        ]
    if role == "test_writer":
        return ["outputs/code_writer/solution.py"]
    return []


def manifest_for(role: str, allowed_inputs: list[Path], output_dir: Path, root: Path) -> dict[str, Any]:
    return {
        "role": role,
        "allowed_inputs": [artifact_for(path, root).__dict__ for path in allowed_inputs],
        "output_dir": output_dir.relative_to(root).as_posix(),
        "forbidden_inputs": forbidden_inputs_for(role),
    }


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    allowed = {item["logical_path"] for item in manifest["allowed_inputs"]}
    leaked = sorted(allowed & set(manifest["forbidden_inputs"]))
    return {
        "role": manifest["role"],
        "passed": not leaked,
        "leaked_paths": leaked,
        "allowed_input_count": len(allowed),
    }


def oracle(line: str) -> dict[str, Any]:
    try:
        name_part, rest = line.split(":", 1)
        quantity_part, price_part = rest.split("@", 1)
        name = name_part.strip().casefold()
        quantity = int(quantity_part.strip())
        cents = int(
            (Decimal(price_part.strip()) * Decimal("100")).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
    except Exception as exc:
        raise ValueError(f"invalid invoice line: {line!r}") from exc

    if not name or quantity <= 0 or cents < 0:
        raise ValueError(f"invalid invoice line: {line!r}")
    return {"name": name, "quantity": quantity, "unit_cents": cents}


def import_solution(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("hermetic_solution", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load solution from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["hermetic_solution"] = module
    spec.loader.exec_module(module)
    return module


def qa_arbitrate(solution_path: Path, cases_path: Path) -> dict[str, Any]:
    solution = import_solution(solution_path)
    generated_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    disagreements: list[dict[str, Any]] = []
    generated_results: list[dict[str, Any]] = []

    for case in generated_cases:
        actual = solution.normalize_invoice_line(case["line"])
        test_expected = case["expected"]
        oracle_expected = oracle(case["line"])
        passed = actual == test_expected
        generated_results.append({"id": case["id"], "passed": passed})
        if passed:
            continue

        if actual == oracle_expected and test_expected != oracle_expected:
            blame = "test_writer"
        elif actual != oracle_expected and test_expected == oracle_expected:
            blame = "code_writer"
        elif actual != oracle_expected and test_expected != oracle_expected:
            blame = "both"
        else:
            blame = "spec_gap"

        disagreements.append(
            {
                "case": case["id"],
                "line": case["line"],
                "implementation": actual,
                "test_expected": test_expected,
                "oracle_expected": oracle_expected,
                "blame": blame,
            }
        )

    hidden_results = []
    for case in HIDDEN_CASES:
        actual = solution.normalize_invoice_line(case["line"])
        hidden_results.append({"id": case["id"], "passed": actual == oracle(case["line"])})

    if disagreements and {item["blame"] for item in disagreements} == {"test_writer"}:
        verdict = "test_writer_fault"
    elif disagreements:
        verdict = "needs_human_review"
    else:
        verdict = "implementation_and_tests_agree"

    return {
        "verdict": verdict,
        "generated_case_results": generated_results,
        "hidden_oracle_results": hidden_results,
        "disagreements": disagreements,
    }


def run_demo(workdir: Path) -> dict[str, Any]:
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    write_text(workdir / "spec/problem.md", SPEC)
    write_text(workdir / "guides/code-writer.md", CODE_GUIDE)
    write_text(workdir / "guides/test-writer.md", TEST_GUIDE)
    write_text(workdir / "guides/qa-arbiter.md", QA_GUIDE)

    code_manifest = manifest_for(
        "code_writer",
        [workdir / "spec/problem.md", workdir / "guides/code-writer.md"],
        workdir / "outputs/code_writer",
        workdir,
    )
    test_manifest = manifest_for(
        "test_writer",
        [workdir / "spec/problem.md", workdir / "guides/test-writer.md"],
        workdir / "outputs/test_writer",
        workdir,
    )
    write_json(workdir / "manifests/code_writer.json", code_manifest)
    write_json(workdir / "manifests/test_writer.json", test_manifest)
    write_text(workdir / "outputs/code_writer/solution.py", SOLUTION)
    write_json(workdir / "outputs/test_writer/test_cases.json", TEST_CASES)
    write_text(
        workdir / "outputs/test_writer/test_solution.py",
        TEST_FILE.format(cases_json=json.dumps(TEST_CASES, indent=2, sort_keys=True)),
    )

    leak_checks = [validate_manifest(code_manifest), validate_manifest(test_manifest)]
    qa = qa_arbitrate(workdir / "outputs/code_writer/solution.py", workdir / "outputs/test_writer/test_cases.json")

    summary = {
        "status": "success" if all(item["passed"] for item in leak_checks) and qa["verdict"] == "test_writer_fault" else "failed",
        "demo": "hermetic_agents",
        "model": "deterministic local harness",
        "claim": "code and test writers receive disjoint context manifests derived from the same spec; QA arbitrates disagreements with a hidden oracle",
        "dag": [
            ["spec/problem.md", "code_writer"],
            ["spec/problem.md", "test_writer"],
            ["outputs/code_writer/solution.py", "qa_arbiter"],
            ["outputs/test_writer/test_cases.json", "qa_arbiter"],
            ["hidden_oracle", "qa_arbiter"],
        ],
        "agents": {
            "code_writer": {
                "allowed_inputs": ["spec/problem.md", "guides/code-writer.md"],
                "cannot_see": forbidden_inputs_for("code_writer"),
            },
            "test_writer": {
                "allowed_inputs": ["spec/problem.md", "guides/test-writer.md"],
                "cannot_see": forbidden_inputs_for("test_writer"),
            },
            "qa_arbiter": {
                "allowed_inputs": [
                    "spec/problem.md",
                    "guides/qa-arbiter.md",
                    "outputs/code_writer/solution.py",
                    "outputs/test_writer/test_cases.json",
                    "hidden_oracle",
                ],
                "feedback_policy": "may assign blame backward on the DAG without revealing forbidden artifacts",
            },
        },
        "leak_checks": leak_checks,
        "qa": qa,
        "artifacts": {
            "spec": artifact_for(workdir / "spec/problem.md", workdir).__dict__,
            "guides": {
                "code_writer": artifact_for(workdir / "guides/code-writer.md", workdir).__dict__,
                "test_writer": artifact_for(workdir / "guides/test-writer.md", workdir).__dict__,
                "qa_arbiter": artifact_for(workdir / "guides/qa-arbiter.md", workdir).__dict__,
            },
            "outputs": {
                "code_writer": artifact_for(workdir / "outputs/code_writer/solution.py", workdir).__dict__,
                "test_writer_cases": artifact_for(workdir / "outputs/test_writer/test_cases.json", workdir).__dict__,
                "test_writer_pytest": artifact_for(workdir / "outputs/test_writer/test_solution.py", workdir).__dict__,
            },
        },
    }
    return summary


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    disagreement = summary["qa"]["disagreements"][0]
    text = f"""# Hermetic Agents E2E Result

Status: `{summary["status"]}`

Verdict: `{summary["qa"]["verdict"]}`

The code writer saw only `spec/problem.md` and `guides/code-writer.md`.
The test writer saw only `spec/problem.md` and `guides/test-writer.md`.
The QA arbiter saw both outputs and a hidden oracle.

Disagreement assigned to `{disagreement["blame"]}`:

```json
{json.dumps(disagreement, indent=2, sort_keys=True)}
```
"""
    write_text(path, text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    default_metrics_dir = Path(os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", "docs/metrics"))
    parser.add_argument("--out", type=Path, default=default_metrics_dir / "hermetic-agents-e2e.json")
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="hermetic-agents-") as temp_root:
        workdir = args.workdir or (Path(temp_root) / "run")
        summary = run_demo(workdir)

    write_json(args.out, summary)
    if args.transcript:
        write_markdown(args.transcript, summary)

    if args.self_test:
        assert summary["status"] == "success", summary
        assert summary["qa"]["verdict"] == "test_writer_fault", summary["qa"]
        assert all(item["passed"] for item in summary["leak_checks"]), summary["leak_checks"]
        assert all(item["passed"] for item in summary["qa"]["hidden_oracle_results"]), summary["qa"]


if __name__ == "__main__":
    main()
