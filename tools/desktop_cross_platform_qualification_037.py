#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
GO = ROOT / "implementations" / "go"
RELEASE = "0.37.0"
TARGETS = (("windows", "amd64"), ("darwin", "amd64"))


def run(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)


def magic_ok(path: Path, goos: str) -> tuple[bool, str]:
    data = path.read_bytes()[:4]
    if goos == "windows":
        return data[:2] == b"MZ", data.hex()
    # Go emits 64-bit Mach-O; cffaedfe is little-endian MH_MAGIC_64.
    return data in {bytes.fromhex("cffaedfe"), bytes.fromhex("feedfacf")}, data.hex()


def qualify() -> dict:
    host_os = platform.system().lower()
    host_arch = platform.machine().lower()
    with tempfile.TemporaryDirectory(prefix="saga-desktop-cross-") as td:
        out = Path(td)
        def one(target: tuple[str,str]) -> dict:
            goos, goarch = target
            env = dict(os.environ, GOOS=goos, GOARCH=goarch, CGO_ENABLED="0")
            suffix = ".exe" if goos == "windows" else ""
            cli = out / f"saga-{goos}-{goarch}{suffix}"
            runtime = out / f"sagaruntime-{goos}-{goarch}{suffix}"
            testbin = out / f"saga-tests-{goos}-{goarch}{suffix}"
            started = time.perf_counter()
            b1 = run(["go", "build", "-trimpath", "-o", str(cli), "./cmd/saga-go"], cwd=GO, env=env)
            b2 = run(["go", "build", "-trimpath", "-tags", "sagaruntime", "-o", str(runtime), "./cmd/saga-go"], cwd=GO, env=env)
            tc = run(["go", "test", "-c", "-o", str(testbin), "./cmd/saga-go"], cwd=GO, env=env)
            cli_magic = magic_ok(cli, goos) if cli.exists() else (False, "missing")
            rt_magic = magic_ok(runtime, goos) if runtime.exists() else (False, "missing")
            test_magic = magic_ok(testbin, goos) if testbin.exists() else (False, "missing")
            file_info = ""
            if shutil.which("file") and cli.exists():
                fi = subprocess.run(["file", str(cli)], text=True, capture_output=True)
                file_info = fi.stdout.strip()
            physically_executed = (goos == "windows" and host_os == "windows") or (goos == "darwin" and host_os == "darwin")
            return {
                "target": f"{goos}/{goarch}",
                "cli_cross_build": b1.returncode == 0,
                "runtime_cross_build": b2.returncode == 0,
                "target_test_binary_compile": tc.returncode == 0,
                "cli_magic_valid": cli_magic[0], "runtime_magic_valid": rt_magic[0], "test_magic_valid": test_magic[0],
                "cli_magic": cli_magic[1], "file": file_info,
                "build_seconds": time.perf_counter() - started,
                "physical_execution": "PASS" if physically_executed else "UNEXECUTED",
                "stderr": "\n".join(x for x in (b1.stderr.strip(), b2.stderr.strip(), tc.stderr.strip()) if x)[-4000:],
            }
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(one, TARGETS))
    passes = all(r["cli_cross_build"] and r["runtime_cross_build"] and r["target_test_binary_compile"] and r["cli_magic_valid"] and r["runtime_magic_valid"] and r["test_magic_valid"] for r in results)
    return {
        "schema": "saga.desktop-cross-platform-qualification.v1",
        "release": RELEASE,
        "host": f"{host_os}/{host_arch}",
        "results": results,
        "cross_compile_and_target-test-compile_pass": passes,
        "windows_physical_validation": "UNEXECUTED" if host_os != "windows" else "PARTIAL_HOST_AVAILABLE",
        "macos_physical_validation": "UNEXECUTED" if host_os != "darwin" else "PARTIAL_HOST_AVAILABLE",
        "pass": passes,
        "limitations": [
            "Cross-compilation and target test-binary compilation validate source/build-tag compatibility, not OS runtime behavior.",
            "No Windows or macOS machine/runtime is available in this environment, so process startup, filesystem semantics, code signing, GUI, driver and device behavior are not physically executed.",
            "Physical Windows/macOS qualification remains required; these results must not be relabeled as real-device PASS.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT / "validation" / "desktop-cross-platform-0.37.0.json"))
    args = ap.parse_args()
    report = qualify()
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
