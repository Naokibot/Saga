#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.api import compile_source, run_source
from saga.errors import SourceError
from tools.evidence_context import source_binding

REL = "0.46.0"
DIAG = re.compile(r"SAGA-[A-Z]\d+")


def build_go(temp: Path) -> Path:
    binary = temp / "saga-go"
    result = subprocess.run(
        ["go", "build", "-o", str(binary), "./cmd/saga-go"],
        cwd=ROOT / "implementations" / "go",
        text=True,
        capture_output=True,
        timeout=120,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return binary


def python_run(source: str) -> tuple[list[str], str | None]:
    output: list[str] = []
    try:
        run_source(source, output=output.append)
        return output, None
    except SourceError as exc:
        return output, exc.diagnostic_id


def python_check(source: str) -> str | None:
    try:
        compile_source(source)
        return None
    except SourceError as exc:
        return exc.diagnostic_id


def go_case(binary: Path, root: Path, name: str, source: str, mode: str) -> tuple[list[str], str | None, str]:
    path = root / f"{name}.saga"
    path.write_text(source.strip() + "\n", encoding="utf-8")
    result = subprocess.run([str(binary), mode, str(path)], text=True, capture_output=True, timeout=30)
    diag = None
    if result.returncode:
        match = DIAG.search(result.stdout + result.stderr)
        diag = match.group(0) if match else f"EXIT-{result.returncode}"
    return result.stdout.rstrip("\n").splitlines(), diag, result.stderr[-1000:]


def float_lines(lines: list[str]) -> list[float]:
    return [float(line.strip()) for line in lines]


def close_lists(left: list[float], right: list[float], *, atol: float = 1e-12) -> bool:
    return len(left) == len(right) and all(math.isclose(a, b, rel_tol=1e-12, abs_tol=atol) for a, b in zip(left, right))


def main() -> int:
    cases: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="saga-046-precision-machine-") as td0:
        temp = Path(td0)
        binary = build_go(temp)

        deterministic = '''
use machine
let controller = machine.pid2(1.0, 0.0, 0.0, 1.0, 0.0, 0.0, -10.0, 10.0)
print(machine.pid2_step(controller, 2.0, 0.5, 0.0, 0.01))
print(machine.motor_feedforward(0.2, 1.5, 0.1, 2.0, 3.0))
let observer = machine.alpha_beta(0.5, 0.1, 0.0, 0.0)
let estimate = machine.alpha_beta_step(observer, 2.0, 0.1)
print(estimate[0])
print(estimate[1])
'''
        expected = ["1.5", "3.5", "1", "2"]
        py_out, py_diag = python_run(deterministic)
        go_out, go_diag, go_err = go_case(binary, temp, "pid-observer-feedforward", deterministic, "run")
        passed = py_diag is None and go_diag is None and py_out == go_out == expected
        cases.append({
            "id": "pid2-observer-feedforward-parity",
            "expected": expected,
            "python_output": py_out,
            "go_output": go_out,
            "python_diagnostic_id": py_diag,
            "go_diagnostic_id": go_diag,
            "pass": passed,
            **({"go_stderr": go_err} if not passed and go_err else {}),
        })

        foc = '''
use machine
let abc = machine.clarke(1.0, -0.5, -0.5)
print(abc[0])
print(abc[1])
print(abc[2])
let dq = machine.park(abc[0], abc[1], 0.0)
print(dq[0])
print(dq[1])
let uv = machine.inverse_park(dq[0], dq[1], 0.0)
print(uv[0])
print(uv[1])
let duty = machine.svpwm(1.0, 0.0, 4.0)
print(duty[0])
print(duty[1])
print(duty[2])
'''
        py_out, py_diag = python_run(foc)
        go_out, go_diag, go_err = go_case(binary, temp, "foc", foc, "run")
        py_values = float_lines(py_out) if py_diag is None else []
        go_values = float_lines(go_out) if go_diag is None else []
        expected_values = [1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.6875, 0.3125, 0.3125]
        passed = (
            py_diag is None and go_diag is None
            and close_lists(py_values, expected_values)
            and close_lists(go_values, expected_values)
            and close_lists(py_values, go_values)
        )
        cases.append({
            "id": "foc-transform-svpwm-parity",
            "expected_numeric": expected_values,
            "python_output": py_out,
            "go_output": go_out,
            "python_diagnostic_id": py_diag,
            "go_diagnostic_id": go_diag,
            "tolerance": {"relative": 1e-12, "absolute": 1e-12},
            "pass": passed,
            **({"go_stderr": go_err} if not passed and go_err else {}),
        })

        notch = '''
use machine
let f = machine.notch(1000.0, 120.0, 5.0)
print(machine.filter_step(f, 1.0))
print(machine.filter_step(f, 1.0))
machine.filter_reset(f)
print(machine.filter_step(f, 1.0))
print(machine.filter_step(f, 1.0))
'''
        py_out, py_diag = python_run(notch)
        go_out, go_diag, go_err = go_case(binary, temp, "notch", notch, "run")
        py_values = float_lines(py_out) if py_diag is None else []
        go_values = float_lines(go_out) if go_diag is None else []
        reset_ok = len(py_values) == 4 and py_values[:2] == py_values[2:] and len(go_values) == 4 and go_values[:2] == go_values[2:]
        passed = py_diag is None and go_diag is None and reset_ok and close_lists(py_values, go_values, atol=2e-12)
        cases.append({
            "id": "notch-reset-and-numeric-parity",
            "python_output": py_out,
            "go_output": go_out,
            "python_diagnostic_id": py_diag,
            "go_diagnostic_id": go_diag,
            "cross_implementation_absolute_tolerance": 2e-12,
            "pass": passed,
            **({"go_stderr": go_err} if not passed and go_err else {}),
        })

        budget = '''
use machine
let b = machine.deadline_budget(1000, 900)
print(machine.budget_stats_json(b))
'''
        py_out, py_diag = python_run(budget)
        go_out, go_diag, go_err = go_case(binary, temp, "budget", budget, "run")
        py_doc = json.loads(py_out[0]) if py_diag is None and len(py_out) == 1 else {}
        go_doc = json.loads(go_out[0]) if go_diag is None and len(go_out) == 1 else {}
        expected_doc = {
            "period_us": 1000,
            "budget_us": 900,
            "samples": 0,
            "violations": 0,
            "last_elapsed_us": 0,
            "max_elapsed_us": 0,
            "timing_class": "hosted-soft-realtime",
        }
        passed = py_diag is None and go_diag is None and py_doc == go_doc == expected_doc
        cases.append({
            "id": "deadline-budget-observer-shape",
            "expected": expected_doc,
            "python": py_doc,
            "go": go_doc,
            "python_diagnostic_id": py_diag,
            "go_diagnostic_id": go_diag,
            "pass": passed,
            **({"go_stderr": go_err} if not passed and go_err else {}),
        })

        invalid = '''
use machine
let p = machine.pid2("not-a-number", 0.0, 0.0, 1.0, 0.0, 0.0, -1.0, 1.0)
'''
        py_diag = python_check(invalid)
        _, go_diag, go_err = go_case(binary, temp, "invalid-pid2-type", invalid, "check")
        passed = py_diag == go_diag == "SAGA-T105"
        cases.append({
            "id": "pid2-static-type-rejection",
            "expected_diagnostic_id": "SAGA-T105",
            "python_diagnostic_id": py_diag,
            "go_diagnostic_id": go_diag,
            "pass": passed,
            **({"go_stderr": go_err} if not passed and go_err else {}),
        })

    binding = source_binding(REL)
    doc = {
        "schema": 1,
        "release": REL,
        **binding,
        "profile": "Precision Machine Control 0.46",
        "total": len(cases),
        "passed": sum(bool(row["pass"]) for row in cases),
        "pass": all(bool(row["pass"]) for row in cases),
        "cases": cases,
        "boundaries": {
            "physical_device_access_required_for_math": False,
            "hosted_deadline_budget_is_hard_realtime": False,
            "hosted_foc_math_is_a_physical_current_loop_qualification": False,
            "certified_machine_safety_function_changed": False,
        },
    }
    out = ROOT / f"validation/precision-machine-{REL}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": doc["total"], "passed": doc["passed"], "pass": doc["pass"]}, indent=2))
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
