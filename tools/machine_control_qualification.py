#!/usr/bin/env python3
"""Non-destructive qualification for Saga's hosted machine-control profile.

The default qualification never opens a physical actuator or bus device.  It
validates control algorithms, capability boundaries, both language
implementations, examples, and cross-platform compilation.  Hardware inventory
is evidence only: detecting a device is not a live PASS.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.evidence_context import source_binding

RELEASE = "0.50.0"


def run(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 120) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout)
    return proc.returncode == 0, proc.stdout


def inventory() -> dict[str, list[str]]:
    dev = Path("/dev")
    sysfs = Path("/sys")
    patterns = {
        "i2c": ["i2c-*"],
        "spi": ["spidev*"],
        "uart": ["ttyUSB*", "ttyACM*"],
    }
    result: dict[str, list[str]] = {}
    for name, globs in patterns.items():
        found: list[str] = []
        if dev.exists():
            for pattern in globs:
                found.extend(str(p) for p in sorted(dev.glob(pattern)))
        result[name] = sorted(set(found))
    result["pwm"] = [str(p) for p in sorted((sysfs / "class/pwm").glob("pwmchip*"))] if (sysfs / "class/pwm").exists() else []
    result["iio"] = [str(p) for p in sorted((sysfs / "bus/iio/devices").glob("iio:device*"))] if (sysfs / "bus/iio/devices").exists() else []
    result["can"] = []
    net = sysfs / "class/net"
    if net.exists():
        for iface in sorted(net.iterdir()):
            type_file = iface / "type"
            try:
                if type_file.read_text().strip() == "280":  # ARPHRD_CAN
                    result["can"].append(iface.name)
            except OSError:
                pass
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT / "validation" / f"machine-control-{RELEASE}.json"))
    ap.add_argument("--cross-builds", action="store_true", help="also compile the machine profile for portable target OS/architectures")
    args = ap.parse_args()
    checks: list[dict[str, object]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "pass": bool(ok), "detail": detail[-2400:]})

    ok, out = run([sys.executable, "-m", "pytest", "-q", "tests/test_machine_control_028.py", "tests/test_machine_control_036.py", "tests/test_precision_machine_046.py", "tests/test_advanced_motion_047.py", "tests/test_production_industrial_049.py"])
    check("Python machine-control regression", ok, out)

    go = shutil.which("go")
    if go:
        ok, out = run([go, "test", "./cmd/saga-go", "-run", "TestMachine|TestPrecisionMachine046|TestAdvancedMotion047|TestProductionIndustrial049", "-count=1"], cwd=ROOT / "implementations/go")
        check("Go Native machine-control regression", ok, out)
        ok, out = run([go, "vet", "./cmd/saga-go"], cwd=ROOT / "implementations/go")
        check("Go Native machine-control vet", ok, out)
    else:
        check("Go Native machine-control regression", False, "Go toolchain is not installed")
        check("Go Native machine-control vet", False, "Go toolchain is not installed")

    example_paths = sorted((ROOT / "examples/machine").glob("*.saga"))
    for path in example_paths:
        ok, out = run([sys.executable, "-m", "saga", "check", str(path)])
        check(f"Python checker: {path.name}", ok, out)

    # Cross-building validates that Linux-only hardware code is cleanly isolated.
    # It is opt-in because compiling five targets is intentionally heavier than
    # the default non-motion qualification.  Every output goes to a temporary
    # directory so qualification never overwrites a developer build artifact.
    if go and args.cross_builds:
        import os
        import tempfile
        targets = [("linux", "amd64"), ("linux", "arm64"), ("windows", "amd64"), ("darwin", "amd64"), ("darwin", "arm64")]
        with tempfile.TemporaryDirectory(prefix="saga-machine-cross-") as td:
            for goos, goarch in targets:
                env = os.environ.copy(); env.update({"GOOS": goos, "GOARCH": goarch, "CGO_ENABLED": "0"})
                suffix = ".exe" if goos == "windows" else ""
                output = Path(td) / f"saga-{goos}-{goarch}{suffix}"
                proc = subprocess.run([go, "build", "-trimpath", "-o", str(output), "./cmd/saga-go"], cwd=ROOT / "implementations/go",
                                      env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
                check(f"cross-build {goos}/{goarch}", proc.returncode == 0 and output.exists(), proc.stdout)

    hw = inventory()
    doc = {
        "schema": 1,
        "release": RELEASE,
        **source_binding(RELEASE),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": {"system": platform.system(), "machine": platform.machine()},
        "timing_class": "hosted-soft-realtime",
        "industrial_protocols": ["modbus-rtu", "modbus-tcp", "socketcan", "can-fd", "ethercat-framing", "canopen-framing", "i2c-dev", "spidev", "uart", "plc-process-image"],
        "motion_control": ["pid", "two-dof-pid", "foc-current-loop", "integrated-encoder", "online-rls", "mpc2", "disturbance-observer", "stribeck-friction", "electronic-gearing", "motor-feedforward", "alpha-beta-observer", "biquad-notch", "clarke-park", "svpwm", "deadline-budget-observer", "timestamped-control-guard", "explicit-control-tick-contract", "trapezoidal-profile", "jerk-limited-s-curve", "supervised-axis", "synchronized-multi-axis", "state-space", "lqr-design", "linear-kalman", "dh-kinematics", "resolved-rate", "watchdog", "safety-latch"],
        "saga_only_application_surface": True,
        "saga_only_scope": "Supported control algorithms, sequencing, protocol framing and process-image logic are callable from Saga source; physical drivers remain runtime/OS/device backends.",
        "hard_realtime_claimed": False,
        "physical_motion_executed": False,
        "checks": checks,
        "hardware_inventory": hw,
        "physical_qualification": "UNEXECUTED",
        "physical_qualification_reason": "Default qualification is deliberately non-destructive. Physical buses, motors, servos, encoders, interlocks, and emergency-stop circuitry require an operator-controlled hardware lab.",
    }
    doc["pass"] = bool(checks) and all(bool(item["pass"]) for item in checks)
    out_path = Path(args.output); out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
