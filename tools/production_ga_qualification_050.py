#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = "0.50.0"
PARTIAL = ROOT / "validation" / "production-ga-0.50.0.partial.json"
FINAL = ROOT / "validation" / "production-ga-0.50.0.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from evidence_context import source_binding
from saga.package import build_lock
from saga.production import _source_digest, production_check
from saga.project import find_project
from saga.stdlib.machine_control import PIDController
from saga.stdlib.machine_motion import FOCCurrentLoop

PY = sys.executable
BATCHES = [
    ("Python core/language/control regression", [
        "tests.test_language", "tests.test_natural_language", "tests.test_modules_030", "tests.test_standard_language", "tests.test_generic_relations_013",
        "tests.test_language_synthesis_045", "tests.test_precision_machine_046", "tests.test_advanced_motion_047", "tests.test_machine_control_028", "tests.test_machine_control_036",
        "tests.test_control_4khz_044", "tests.test_production_industrial_049", "tests.test_control_ga_050",
    ]),
    ("Python ecosystem/runtime/security regression", ["tests.test_ecosystem_011", "tests.test_fullstack", "tests.test_runtime_safety_038", "tests.test_runtime_scale_037", "tests.test_security_profile_024"]),
    ("Python native runtime/codegen", ["tests.test_native_runtime_035", "tests.test_native_codegen_032"]),
    ("Python native aggregate GC", ["tests.test_native_aggregate_gc_034"]),
    ("Python autonomy/drone/diagnostics/lsp regression", ["tests.test_autonomy_machine_042", "tests.test_diagnostics_090", "tests.test_drone_control_040", "tests.test_drone_vision_comm_041", "tests.test_fine_control_043", "tests.test_human_value_033", "tests.test_iso_candidate_070", "tests.test_lsp_090"]),
    ("Python platform/security/remaining regression", ["tests.test_migration_029", "tests.test_native_object_031", "tests.test_security_010", "tests.test_standardization", "tests.test_unbounded_parallel_080", "tests.test_virtual_hil_048"]),
    ("Python platform profile regression", ["tests.test_platform_profiles_026"]),
    ("Python review regression A", ["tests.test_review_0101", "tests.test_review_091", "tests.test_review_alt_0262", "tests.test_review_fixes", "tests.test_review_hardening_0261", "tests.test_review_pass2_029"]),
    ("Python review regression B", ["tests.test_review_pass3_029", "tests.test_review_pass4_029", "tests.test_review_pass5_029", "tests.test_review_pass6_029", "tests.test_review_pass7_029", "tests.test_review_readiness_026"]),
]
REQUIRED = [
    "Python compileall",
    *(name for name, _ in BATCHES),
    "Python resource-leak regression",
    "Internal security audit",
    "Specification final-candidate lint",
    "Go full regression",
    "Go vet",
    "Go Race Detector control paths",
    "20k deterministic control invariant cases",
    "0.50 direct-native reproducibility and execution",
    "Machine production gate pass + source-mismatch rejection",
]


def current_binding() -> dict[str, str]:
    return source_binding(REL)


def load_partial(binding: dict[str, str]) -> dict[str, dict[str, object]]:
    if not PARTIAL.is_file():
        return {}
    try:
        doc = json.loads(PARTIAL.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if doc.get("release") != REL:
        return {}
    for key in ("source_manifest_sha256", "source_tree_sha256"):
        if doc.get(key) != binding.get(key):
            return {}
    checks = doc.get("checks") if isinstance(doc.get("checks"), list) else []
    return {str(c.get("name")): c for c in checks if isinstance(c, dict) and c.get("name")}


def save_partial(binding: dict[str, str], checks: dict[str, dict[str, object]]) -> None:
    PARTIAL.parent.mkdir(parents=True, exist_ok=True)
    ordered = [checks[name] for name in REQUIRED if name in checks]
    PARTIAL.write_text(json.dumps({"schema": 1, "release": REL, **binding, "checks": ordered}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Resumable, source-bound Saga 0.50 Production GA qualification")
    ap.add_argument("--reset", action="store_true", help="discard prior checkpoint before running")
    ap.add_argument("--finalize-only", action="store_true", help="do not run checks; only finalize current checkpoint")
    args = ap.parse_args()

    binding = current_binding()
    if args.reset:
        PARTIAL.unlink(missing_ok=True)
        FINAL.unlink(missing_ok=True)
    checks = load_partial(binding)

    def passed(name: str) -> bool:
        return bool(checks.get(name, {}).get("pass"))

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks[name] = {"name": name, "pass": bool(ok), "detail": str(detail)[-12000:]}
        save_partial(binding, checks)
        print(f"[{ 'PASS' if ok else 'FAIL' }] {name}", flush=True)

    def run(name: str, cmd: list[str], cwd: Path = ROOT, timeout: int = 120) -> None:
        if passed(name):
            print(f"[SKIP/PASS] {name}", flush=True)
            return
        try:
            p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
            record(name, p.returncode == 0, p.stdout)
        except subprocess.TimeoutExpired as exc:
            record(name, False, f"timeout after {timeout}s\n{exc.stdout or ''}")
        except Exception as exc:
            record(name, False, f"{type(exc).__name__}: {exc}")

    if not args.finalize_only:
        run("Python compileall", [PY, "-m", "compileall", "-q", "saga", "tools"])
        for name, mods in BATCHES:
            run(name, [PY, "-m", "unittest", *mods], timeout=180)
        run("Python resource-leak regression", [PY, "-Werror::ResourceWarning", "-m", "unittest", "tests.test_review_fixes"], timeout=120)
        run("Internal security audit", [PY, "tools/internal_security_audit.py"])
        run("Specification final-candidate lint", [PY, "tools/spec_review_lint.py"])

        go = shutil.which("go")
        if go:
            run("Go full regression", [go, "test", "./..."], ROOT / "implementations/go", timeout=180)
            run("Go vet", [go, "vet", "./..."], ROOT / "implementations/go", timeout=180)
            run("Go Race Detector control paths", [go, "test", "-race", "./cmd/saga-go", "-run", "TestControlGA050TransitiveControlProfile|TestControlGA050MoveRemainsContextualIdentifier|TestProductionIndustrial049ControlGuardAndContract|TestAdvancedMotion047PortableSurface", "-count=1"], ROOT / "implementations/go", timeout=180)
        else:
            record("Go full regression", False, "Go toolchain missing")
            record("Go vet", False, "Go toolchain missing")
            record("Go Race Detector control paths", False, "Go toolchain missing")

        if not passed("20k deterministic control invariant cases"):
            try:
                rng = random.Random(50050)
                pid = PIDController.create(Decimal("1.2"), Decimal("0.4"), Decimal("0.03"), Decimal("-1"), Decimal("1"))
                pid.set_integral_limits(Decimal("-0.5"), Decimal("0.5"))
                for _ in range(10_000):
                    out = pid.step(Decimal(str(rng.uniform(-10, 10))), Decimal(str(rng.uniform(-10, 10))), Decimal(str(rng.uniform(0.0001, 0.02))))
                    assert Decimal("-1") <= out <= Decimal("1")
                    assert Decimal("-0.5") <= pid.integral <= Decimal("0.5")
                foc = FOCCurrentLoop(Decimal("2"), Decimal("80"), Decimal("2"), Decimal("80"), Decimal("0.08"), Decimal("0.00012"), Decimal("0.00012"), Decimal("0.018"), Decimal("25"), Decimal("24"), Decimal("12"))
                for _ in range(10_000):
                    foc.step(Decimal(str(rng.uniform(-40, 40))), Decimal(str(rng.uniform(-40, 40))), Decimal(str(rng.uniform(-50, 50))), Decimal(str(rng.uniform(-50, 50))), Decimal(str(rng.uniform(-50, 50))), Decimal(str(rng.uniform(-6.3, 6.3))), Decimal(str(rng.uniform(-5000, 5000))), Decimal(str(rng.uniform(5, 60))), Decimal(str(rng.uniform(0.00001, 0.002))))
                    assert all(Decimal(0) <= d <= Decimal(1) for d in (foc.duty_a, foc.duty_b, foc.duty_c))
                    assert abs(foc.integral_d) <= foc.voltage_limit and abs(foc.integral_q) <= foc.voltage_limit
                record("20k deterministic control invariant cases", True, "PID 10,000 + FOC 10,000 bounded-output/integrator cases")
            except Exception as exc:
                record("20k deterministic control invariant cases", False, f"{type(exc).__name__}: {exc}")

        if not passed("0.50 direct-native reproducibility and execution"):
            try:
                with tempfile.TemporaryDirectory(prefix="saga050-native-") as td:
                    root = Path(td); src = root / "control.saga"
                    src.write_text('@control_tick(1000,500)\nfn tick(x:int)->int{return helper(x)}\n@control_safe\nfn helper(x:int)->int{return x+1}\nprint(tick(41))\n', encoding="utf-8")
                    outs = [root / "a", root / "b"]
                    for out in outs:
                        p = subprocess.run([PY, "-m", "saga", "build", str(src), "--target", "native", "--profile", "codegen", "--output", str(out)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
                        if p.returncode:
                            raise RuntimeError(p.stdout)
                    hashes = [hashlib.sha256(x.read_bytes()).hexdigest() for x in outs]
                    if hashes[0] != hashes[1]:
                        raise RuntimeError(f"native hashes differ: {hashes}")
                    p = subprocess.run([str(outs[0])], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
                    if p.returncode != 0 or p.stdout.strip() != "42":
                        raise RuntimeError("native control sample did not execute as expected: " + p.stdout)
                    record("0.50 direct-native reproducibility and execution", True, hashes[0])
            except Exception as exc:
                record("0.50 direct-native reproducibility and execution", False, f"{type(exc).__name__}: {exc}")

        if not passed("Machine production gate pass + source-mismatch rejection"):
            try:
                with tempfile.TemporaryDirectory(prefix="saga050-machine-gate-") as td:
                    root = Path(td)
                    (root / "saga.toml").write_text('[project]\nname="motor"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\n', encoding="utf-8")
                    (root / "main.saga").write_text('@control_tick(1000,500)\nfn tick(x:int)->int{return helper(x)}\n@control_safe\nfn helper(x:int)->int{return x+1}\n', encoding="utf-8")
                    build_lock(root)
                    project = find_project(root); assert project is not None
                    digest = _source_digest(project)
                    ev = root / "evidence"; ev.mkdir()
                    for name, kind in (("hazard.json", "hazard-analysis"), ("wcet.json", "wcet"), ("hil.json", "hil")):
                        (ev / name).write_text(json.dumps({"schema": 1, "kind": kind, "pass": True, "project_source_sha256": digest, "saga_release": REL}), encoding="utf-8")
                    (root / "machine-safety.toml").write_text('[safety]\nprofile="machine-production-ga-1"\nexternal_emergency_stop=true\nsto_or_interlock=true\nhardware_watchdog=true\ntarget="rtos"\nhazard_analysis="evidence/hazard.json"\nwcet_evidence="evidence/wcet.json"\nhil_evidence="evidence/hil.json"\n', encoding="utf-8")
                    good = production_check(root, machine=True)
                    if not good.get("ready"):
                        raise RuntimeError(json.dumps(good))
                    (ev / "hil.json").write_text(json.dumps({"schema": 1, "kind": "hil", "pass": True, "project_source_sha256": "0" * 64, "saga_release": REL}), encoding="utf-8")
                    bad = production_check(root, machine=True)
                    if bad.get("ready"):
                        raise RuntimeError("source-mismatched HIL evidence was accepted")
                    record("Machine production gate pass + source-mismatch rejection", True, "valid source-bound case passes; altered binding fails")
            except Exception as exc:
                record("Machine production gate pass + source-mismatch rejection", False, f"{type(exc).__name__}: {exc}")

    missing = [name for name in REQUIRED if name not in checks]
    failed = [name for name in REQUIRED if name in checks and not checks[name].get("pass")]
    doc = {
        "schema": 2,
        "release": REL,
        **binding,
        "profile": "Saga 0.50 Production GA — Control Language & Toolchain",
        "checks": [checks[name] for name in REQUIRED if name in checks],
        "pass": not missing and not failed,
        "scope": "language-toolchain-production-ga",
        "machine_certification_claimed": False,
        "external_machine_gates": [
            "target-specific hard-real-time/WCET qualification",
            "physical HIL and fieldbus/motor/drive qualification",
            "system hazard analysis and independent E-stop/STO/interlock",
            "applicable SIL/PL or other regulatory certification when required",
        ],
        "missing_checks": missing,
        "failed_checks": failed,
        "qualification_mode": "resumable-source-bound",
    }
    if doc["pass"]:
        FINAL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
