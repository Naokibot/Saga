#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from saga.package import build_lock
from saga.production import production_check
from evidence_context import source_binding

REL = "0.49.0"


def run(cmd: list[str], cwd: Path = ROOT, timeout: int = 120) -> tuple[bool, str]:
    p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.returncode == 0, p.stdout


def main() -> int:
    checks: list[dict[str, object]] = []
    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "pass": bool(ok), "detail": detail[-4000:]})

    ok, out = run([sys.executable, "-m", "unittest", "tests.test_production_industrial_049"])
    record("Production & Industrial 0.49 unit/cross-implementation tests", ok, out)

    ok, out = run([sys.executable, "-m", "unittest", "tests.test_language", "tests.test_natural_language", "tests.test_modules_030", "tests.test_standard_language", "tests.test_generic_relations_013"])
    record("Language/type/module regression", ok, out)

    ok, out = run([sys.executable, "-m", "unittest", "tests.test_ecosystem_011", "tests.test_fullstack", "tests.test_runtime_safety_038", "tests.test_runtime_scale_037", "tests.test_security_profile_024"])
    record("Ecosystem/fullstack/runtime/security regression", ok, out)

    ok, out = run([sys.executable, "-m", "unittest", "tests.test_precision_machine_046", "tests.test_advanced_motion_047", "tests.test_machine_control_028", "tests.test_machine_control_036", "tests.test_control_4khz_044", "tests.test_production_industrial_049"])
    record("Industrial control retained regression", ok, out)

    go = shutil.which("go")
    if go:
        ok, out = run([go, "test", "./..."], ROOT / "implementations/go")
        record("Go full regression", ok, out)
        ok, out = run([go, "vet", "./..."], ROOT / "implementations/go")
        record("Go vet", ok, out)
        ok, out = run([go, "test", "-race", "./cmd/saga-go", "-run", "TestProductionIndustrial049ControlGuardAndContract|TestAdvancedMotion047PortableSurface", "-count=1"], ROOT / "implementations/go")
        record("Go race changed industrial paths", ok, out)
    else:
        record("Go full regression", False, "Go toolchain missing")
        record("Go vet", False, "Go toolchain missing")
        record("Go race changed industrial paths", False, "Go toolchain missing")

    # Exercise the actual CLI-level production gate including native byte reproducibility.
    with tempfile.TemporaryDirectory(prefix="saga-prod-qual-") as td:
        root = Path(td)
        for name, n in (("core", 21), ("control", 42)):
            d = root / name; d.mkdir()
            (d / "saga.toml").write_text(f'[project]\nname="{name}"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\n', encoding="utf-8")
            (d / "main.saga").write_text(f'fn value() -> int {{ return {n} }}\nprint(value())\n', encoding="utf-8")
            build_lock(d)
        (root / "saga-workspace.toml").write_text('[workspace]\nmembers=["core","control"]\n', encoding="utf-8")
        report = production_check(root, native=True)
        record("Workspace production gate with native reproducibility", bool(report.get("ready")), json.dumps(report, ensure_ascii=False, sort_keys=True))

    doc = {
        "schema": 1,
        "release": REL,
        **source_binding(REL),
        "profile": "Production & Industrial 0.49",
        "checks": checks,
        "pass": bool(checks) and all(bool(x["pass"]) for x in checks),
        "commercial_readiness_claim": "production-candidate-local-evidence",
        "unconditional_go_rust_cpp_replacement_claimed": False,
        "external_gates_required": [
            "independent third-party security audit bound to exact release",
            "native physical Windows/macOS/Linux host qualification",
            "public signed registry interoperability and recovery drills",
            "multi-month/year field operation and ecosystem adoption evidence",
            "physical machine/HIL and applicable functional-safety certification",
        ],
    }
    out = ROOT / "validation" / "production-industrial-0.49.0.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
