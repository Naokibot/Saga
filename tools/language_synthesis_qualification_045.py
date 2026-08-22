#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.api import compile_source, run_file, run_source
from saga.errors import SourceError
from saga.module_interface import build_module_interface
from tools.evidence_context import source_binding

REL = "0.45.0"
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


def python_run(source: str) -> tuple[str, str | None]:
    output: list[str] = []
    try:
        run_source(source, output=output.append)
        return "\n".join(output), None
    except SourceError as exc:
        return "\n".join(output), exc.diagnostic_id


def python_check(source: str) -> str | None:
    try:
        compile_source(source)
        return None
    except SourceError as exc:
        return exc.diagnostic_id


def go_case(binary: Path, root: Path, name: str, source: str, mode: str) -> tuple[str, str | None, str]:
    path = root / f"{name}.saga"
    path.write_text(source.strip() + "\n", encoding="utf-8")
    result = subprocess.run([str(binary), mode, str(path)], text=True, capture_output=True, timeout=30)
    diag = None
    if result.returncode:
        match = DIAG.search(result.stdout + result.stderr)
        diag = match.group(0) if match else f"EXIT-{result.returncode}"
    return result.stdout.rstrip("\n"), diag, result.stderr[-1000:]


def main() -> int:
    cases: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="saga-045-synthesis-") as td0:
        temp = Path(td0)
        binary = build_go(temp)

        run_cases = [
            (
                "async-await-defer",
                '''
                async fn double(x:int)->int { return x*2 }
                fn cleanup()->unit { print("cleanup") }
                fn answer()->int { defer cleanup(); return await double(21) }
                print(answer())
                ''',
                "cleanup\n42",
            ),
            (
                "contextual-words",
                '''
                fn await()->int=20
                fn move()->int=22
                let async=await()+move()
                var defer=async
                defer=defer+1
                let using=defer+1
                let taskgroup=using+1
                fn echo(await:int)->int=await
                print(async)
                print(defer)
                print(using)
                print(taskgroup)
                print(echo(46))
                ''',
                "42\n43\n44\n45\n46",
            ),
            (
                "taskgroup",
                '''
                async fn work()->unit { print("worker") }
                taskgroup { work() }
                print("done")
                ''',
                "worker\ndone",
            ),
            (
                "task-pool-using-move",
                '''
                use task
                fn identity(x:int)->int=x
                using pool=task.pool(1) {
                  let f=task.submit(pool,identity,9)
                  print(task.await(f))
                }
                var pool=task.pool(1)
                task.shutdown(move pool)
                pool=task.pool(1)
                task.shutdown(move pool)
                print("ok")
                ''',
                "9\nok",
            ),
        ]
        for name, source, expected in run_cases:
            py_out, py_diag = python_run(source)
            go_out, go_diag, go_err = go_case(binary, temp, name, source, "run")
            passed = py_diag is None and go_diag is None and py_out == go_out == expected
            row: dict[str, object] = {
                "id": name,
                "expected": expected,
                "python_output": py_out,
                "go_output": go_out,
                "python_diagnostic_id": py_diag,
                "go_diagnostic_id": go_diag,
                "pass": passed,
            }
            if not passed and go_err:
                row["go_stderr"] = go_err
            cases.append(row)

        invalid = '''
        use task
        let pool=task.pool(1)
        task.shutdown(move pool)
        task.shutdown(pool)
        '''
        py_diag = python_check(invalid)
        _, go_diag, go_err = go_case(binary, temp, "use-after-move", invalid, "check")
        passed = py_diag == go_diag == "SAGA-T180"
        row = {
            "id": "use-after-move-static-rejection",
            "expected_diagnostic_id": "SAGA-T180",
            "python_diagnostic_id": py_diag,
            "go_diagnostic_id": go_diag,
            "pass": passed,
        }
        if not passed and go_err:
            row["go_stderr"] = go_err
        cases.append(row)

        module = temp / "jobs.saga"
        module.write_text("module jobs\npublic async fn answer()->int { return 42 }\n", encoding="utf-8")
        py_iface = build_module_interface(module, output=temp / "python.smi.json")
        go_result = subprocess.run(
            [str(binary), "module", "compile", str(module), str(temp / "go.smi.json")],
            text=True,
            capture_output=True,
            timeout=30,
        )
        go_iface = json.loads((temp / "go.smi.json").read_text(encoding="utf-8")) if go_result.returncode == 0 else {}
        export = next((e for e in py_iface.get("exports", []) if e.get("name") == "answer"), {})
        passed = (
            go_result.returncode == 0
            and export.get("return") == "future[int]"
            and py_iface.get("exports") == go_iface.get("exports")
            and py_iface.get("abi_sha256") == go_iface.get("abi_sha256")
        )
        cases.append({
            "id": "async-module-abi-parity",
            "python_return": export.get("return"),
            "python_abi_sha256": py_iface.get("abi_sha256"),
            "go_abi_sha256": go_iface.get("abi_sha256"),
            "pass": passed,
            **({"go_stderr": go_result.stderr[-1000:]} if not passed else {}),
        })

    binding = source_binding(REL)
    doc = {
        "schema": 1,
        "release": REL,
        **binding,
        "profile": "Language Synthesis 0.45",
        "total": len(cases),
        "passed": sum(bool(row["pass"]) for row in cases),
        "pass": all(bool(row["pass"]) for row in cases),
        "cases": cases,
        "boundaries": {
            "hosted_async_is_hard_real_time": False,
            "move_is_general_borrow_checker": False,
            "physical_hardware_qualification_changed": False,
        },
    }
    out = ROOT / f"validation/language-synthesis-{REL}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": doc["total"], "passed": doc["passed"], "pass": doc["pass"]}, indent=2))
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
