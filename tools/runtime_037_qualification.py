#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.evidence_context import source_binding

RELEASE = "0.37.0"


def main() -> int:
    cmd = [sys.executable, "-m", "unittest", "-q", "tests.test_runtime_scale_037"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    report = {
        "schema": "saga.runtime-qualification.0.37.v1",
        "release": RELEASE,
        **source_binding(RELEASE),
        "suite": "tests.test_runtime_scale_037",
        "cases": 5,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "features": [
            "cross-module generic function/class specialization",
            "open-world external subtype registration",
            "concurrent idempotent dispatch registration",
            "bounded low-pause major mark/sweep polling",
            "Python debugger recording/watches/profiling",
        ],
        "pass": proc.returncode == 0,
    }
    out = ROOT / "validation" / "runtime-qualification-0.37.0.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("release", "suite", "cases", "pass", "source_tree_sha256")}, indent=2))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
