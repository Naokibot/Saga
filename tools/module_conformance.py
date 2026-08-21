#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.api import compile_file, run_file
from saga.errors import SourceError
from saga.module_interface import build_module_interface, load_module_interface
from tools.evidence_context import source_binding

REL = "0.50.0"
DIAG = re.compile(r"SAGA-[A-Z]\d+")


def write(root: Path, name: str, source: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.strip() + "\n", encoding="utf-8")
    return path


def python_program(path: Path, *, check_only: bool = False) -> tuple[str, str | None]:
    output: list[str] = []
    try:
        if check_only:
            compile_file(str(path))
        else:
            run_file(str(path), output=output.append)
        return "\n".join(output), None
    except SourceError as exc:
        return "\n".join(output), exc.diagnostic_id


def go_program(binary: Path, path: Path, *, check_only: bool = False) -> tuple[str, str | None, str]:
    mode = "check" if check_only else "run"
    result = subprocess.run([str(binary), mode, str(path)], text=True, capture_output=True, timeout=30)
    error = None
    if result.returncode:
        match = DIAG.search(result.stdout + result.stderr)
        error = match.group(0) if match else f"EXIT-{result.returncode}"
    return result.stdout.rstrip("\n"), error, result.stderr[-1000:]


def program_case(binary: Path, case_id: str, root: Path, main: Path, *, expected_output: str = "", expected_error: str | None = None) -> dict:
    py_out, py_err = python_program(main, check_only=expected_error is not None)
    go_out, go_err, go_stderr = go_program(binary, main, check_only=expected_error is not None)
    passed = py_out == go_out and py_err == go_err and (
        py_err == expected_error if expected_error is not None else py_err is None and py_out == expected_output
    )
    row = {
        "id": case_id,
        "python_output": py_out,
        "go_output": go_out,
        "python_diagnostic_id": py_err,
        "go_diagnostic_id": go_err,
        "expected_output": expected_output,
        "expected_diagnostic_id": expected_error,
        "pass": passed,
    }
    if not passed and go_stderr:
        row["go_stderr"] = go_stderr
    return row


def build_go_binary(temp: Path) -> Path:
    binary = temp / ("saga-native.exe" if sys.platform.startswith("win") else "saga-native")
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


def go_module(binary: Path, action: str, *args: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(binary), "module", action, *(str(v) for v in args)], text=True, capture_output=True, timeout=30)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-implementation conformance for Saga Natural Module Core 0.30")
    parser.add_argument("--output", default=str(ROOT / f"validation/module-conformance-{REL}.json"))
    args = parser.parse_args()
    records: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="saga-module-conformance-") as td0:
        temp = Path(td0)
        binary = build_go_binary(temp)

        # MC001: public namespace function.
        root = temp / "c1"; root.mkdir()
        write(root, "models.saga", 'module models\npublic fn twice(x:int)->int=x*2')
        main_file = write(root, "main.saga", 'use "models.saga" as m\nprint(m.twice(21))')
        records.append(program_case(binary, "MC001-public-namespace", root, main_file, expected_output="42"))

        # MC002: internal member is not visible to importer.
        root = temp / "c2"; root.mkdir()
        write(root, "models.saga", 'module models\ninternal fn hidden()->int=99')
        main_file = write(root, "main.saga", 'use "models.saga" as m\nprint(m.hidden())')
        records.append(program_case(binary, "MC002-internal-hidden", root, main_file, expected_error="SAGA-T106"))

        # MC003: qualified nominal class.
        root = temp / "c3"; root.mkdir()
        write(root, "models.saga", 'module models\npublic class User(let name:text){fn greet()->text="Hello "+self.name}')
        main_file = write(root, "main.saga", 'use "models.saga" as m\nlet u:m.User=m.User("Aki")\nprint(u.greet())')
        records.append(program_case(binary, "MC003-qualified-class", root, main_file, expected_output="Hello Aki"))

        # MC004: imported public base class at typecheck and runtime.
        root = temp / "c4"; root.mkdir()
        write(root, "models.saga", 'module models\npublic class User(let name:text){fn greet()->text="Hello "+self.name}')
        main_file = write(root, "main.saga", 'use "models.saga" as m\nclass Local(let id:int) extends m.User{fn label()->text=self.name+":"+text(self.id)}\nlet x=Local("Aki",7)\nprint(x.greet())\nprint(x.label())')
        records.append(program_case(binary, "MC004-qualified-inheritance", root, main_file, expected_output="Hello Aki\nAki:7"))

        # MC005: same spelling from different namespaces remains nominally distinct.
        root = temp / "c5"; root.mkdir()
        write(root, "a.saga", 'module a\npublic class User(let name:text){}')
        write(root, "b.saga", 'module b\npublic class User(let name:text){}')
        main_file = write(root, "main.saga", 'use "a.saga" as a\nuse "b.saga" as b\nlet value:a.User=b.User("B")')
        records.append(program_case(binary, "MC005-qualified-nominal-identity", root, main_file, expected_error="SAGA-T103"))

        # MC006: one canonical alias per source module.
        root = temp / "c6"; root.mkdir()
        write(root, "models.saga", 'module models\npublic fn value()->int=1')
        main_file = write(root, "main.saga", 'use "models.saga" as m\nuse "models.saga"\nprint(m.value())')
        records.append(program_case(binary, "MC006-canonical-alias", root, main_file, expected_error="SAGA-P109"))

        # MC007: internal nominal type cannot leak into public ABI.
        root = temp / "c7"; root.mkdir()
        main_file = write(root, "main.saga", 'module main\nclass Secret(let value:int){}\npublic fn reveal(x:Secret)->int=x.value')
        records.append(program_case(binary, "MC007-public-internal-leak", root, main_file, expected_error="SAGA-T118"))

        # MC008: dependency alias nominal type cannot leak into public ABI in 0.30.
        root = temp / "c8"; root.mkdir()
        write(root, "dep.saga", 'module dep\npublic class User(let name:text){}')
        main_file = write(root, "main.saga", 'module facade\nuse "dep.saga" as d\npublic fn make()->d.User=d.User("x")')
        records.append(program_case(binary, "MC008-public-dependency-leak", root, main_file, expected_error="SAGA-T118"))

        # MC009: Python and Go emit the same common interface.
        root = temp / "c9"; root.mkdir()
        module = write(root, "models.saga", 'module models\npublic class User(let name:text){fn greet()->text=self.name}\npublic fn twice(x:int)->int=x*2\npublic let answer:int=42')
        py_iface = build_module_interface(module, output=root / "python.smi.json")
        go_result = go_module(binary, "compile", module, root / "go.smi.json")
        go_iface = json.loads((root / "go.smi.json").read_text(encoding="utf-8")) if go_result.returncode == 0 else {}
        same = (
            py_iface.get("exports") == go_iface.get("exports")
            and py_iface.get("abi_sha256") == go_iface.get("abi_sha256")
            and py_iface.get("build_sha256") == go_iface.get("build_sha256")
        )
        records.append({"id": "MC009-interface-abi-parity", "python_abi": py_iface.get("abi_sha256"), "go_abi": go_iface.get("abi_sha256"), "pass": same})

        # MC010: implementation-only dependency changes preserve importer freshness.
        root = temp / "c10"; root.mkdir()
        dep = write(root, "dep.saga", 'module dep\npublic fn value()->int=1')
        parent = write(root, "parent.saga", 'module parent\nuse "dep.saga" as d\npublic fn doubled()->int=d.value()*2')
        build_module_interface(parent)
        parent_iface = root / "parent.smi.json"
        before = load_module_interface(parent_iface, source=parent)
        write(root, "dep.saga", 'module dep\npublic fn value()->int=2')
        dep_iface = build_module_interface(dep)
        py_fresh = dep_iface["abi_sha256"] == before["dependencies"][0]["abi_sha256"]
        try:
            load_module_interface(parent_iface, source=parent)
        except ValueError:
            py_fresh = False
        go_module(binary, "compile", parent, root / "go-parent.smi.json")
        write(root, "dep.saga", 'module dep\npublic fn value()->int=3')
        go_module(binary, "compile", dep, root / "dep.smi.json")
        go_verify = go_module(binary, "verify", root / "go-parent.smi.json", parent)
        records.append({"id": "MC010-implementation-change-keeps-importer-fresh", "python_fresh": py_fresh, "go_fresh": go_verify.returncode == 0, "pass": py_fresh and go_verify.returncode == 0})

        # MC011: public dependency ABI change invalidates importer interface.
        root = temp / "c11"; root.mkdir()
        dep = write(root, "dep.saga", 'module dep\npublic fn value()->int=1')
        parent = write(root, "parent.saga", 'module parent\nuse "dep.saga" as d\npublic fn doubled()->int=d.value()*2')
        build_module_interface(parent)
        go_module(binary, "compile", parent, root / "go-parent.smi.json")
        write(root, "dep.saga", 'module dep\npublic fn value()->text="1"')
        build_module_interface(dep)
        py_stale = False
        try:
            load_module_interface(root / "parent.smi.json", source=parent)
        except ValueError:
            py_stale = True
        go_module(binary, "compile", dep, root / "dep.smi.json")
        go_verify = go_module(binary, "verify", root / "go-parent.smi.json", parent)
        records.append({"id": "MC011-abi-change-invalidates-importer", "python_stale": py_stale, "go_stale": go_verify.returncode != 0, "pass": py_stale and go_verify.returncode != 0})

        # MC012: stale SMI must fall back to source and expose the new source type error.
        root = temp / "c12"; root.mkdir()
        module = write(root, "models.saga", 'module models\npublic fn twice(x:int)->int=x*2')
        build_module_interface(module)
        go_module(binary, "compile", module, root / "go.smi.json")
        # Go loader looks for models.smi.json; retain a stale Go-compatible artifact there.
        shutil.copy2(root / "go.smi.json", root / "models.smi.json")
        main_file = write(root, "main.saga", 'use "models.saga" as m\nprint(m.twice(2))')
        write(root, "models.saga", 'module models\npublic fn twice(x:int)->int="bad"')
        records.append(program_case(binary, "MC012-stale-interface-source-fallback", root, main_file, expected_error="SAGA-T103"))

        # MC013: public enum identity and SMI ABI are common across both implementations.
        root = temp / "c13"; root.mkdir()
        module = write(root, "models.saga", 'module models\npublic enum Status { Ready, Done }\npublic fn status()->Status=Status.Ready')
        main_file = write(root, "main.saga", 'use "models.saga" as m\nlet s:m.Status=m.status()\nmatch s { case m.Status.Ready { print("ready") } case m.Status.Done { print("done") } }')
        program = program_case(binary, "MC013-public-enum", root, main_file, expected_output="ready")
        py_iface = build_module_interface(module, output=root / "python.smi.json")
        go_result = go_module(binary, "compile", module, root / "go.smi.json")
        go_iface = json.loads((root / "go.smi.json").read_text(encoding="utf-8")) if go_result.returncode == 0 else {}
        enum_parity = py_iface.get("exports") == go_iface.get("exports") and py_iface.get("abi_sha256") == go_iface.get("abi_sha256") and py_iface.get("build_sha256") == go_iface.get("build_sha256")
        program["interface_parity"] = enum_parity
        program["pass"] = bool(program["pass"]) and enum_parity
        records.append(program)

        # MC014: payload-bearing tagged union matches and shares the exact SMI ABI.
        root = temp / "c14"; root.mkdir()
        module = write(root, "models.saga", 'module models\npublic enum Result { Ok(int), Err(text) }\npublic fn make(x:int)->Result=Result.Ok(x)')
        main_file = write(root, "main.saga", 'use "models.saga" as m\nmatch m.make(9) { case m.Result.Ok(v) { print(v) } case m.Result.Err(e) { print(e) } }')
        program = program_case(binary, "MC014-payload-tagged-union", root, main_file, expected_output="9")
        py_iface = build_module_interface(module, output=root / "python.smi.json")
        go_result = go_module(binary, "compile", module, root / "go.smi.json")
        go_iface = json.loads((root / "go.smi.json").read_text(encoding="utf-8")) if go_result.returncode == 0 else {}
        parity = py_iface.get("exports") == go_iface.get("exports") and py_iface.get("abi_sha256") == go_iface.get("abi_sha256") and py_iface.get("build_sha256") == go_iface.get("build_sha256")
        program["interface_parity"] = parity
        program["pass"] = bool(program["pass"]) and parity
        records.append(program)

    try:
        binding = source_binding(REL)
    except RuntimeError:
        # Development runs before the final release manifest exists are useful
        # for fixing semantics. Release evidence is regenerated after manifest
        # creation and is then source-bound.
        binding = {"source_manifest": None, "source_tree_sha256": None, "source_bound": False}
    doc = {
        "schema": 1,
        "release": REL,
        **binding,
        "profile": "Natural Module Core 0.30 cross-implementation module graph conformance",
        "python_implementation": "Saga Python reference",
        "go_implementation": "Saga Go independent Standard Core",
        "total": len(records),
        "passed": sum(bool(r.get("pass")) for r in records),
        "pass": all(bool(r.get("pass")) for r in records),
        "cases": records,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": doc["total"], "passed": doc["passed"], "pass": doc["pass"]}, indent=2))
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
