#!/usr/bin/env python3
"""Run machine-control qualification against the active checkout.

The frozen machine-control qualification keeps its original 0.50.0 manifest
binding for reproducibility. Development CI uses this wrapper to bind evidence
to the current source tree without mutating historical release evidence.
"""
from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

with (ROOT / "pyproject.toml").open("rb") as fh:
    release = str(tomllib.load(fh)["project"]["version"])

from tools import machine_control_qualification as qualification
from tools.review_evidence import build_manifest


def current_source_binding(_release: str) -> dict[str, str]:
    current = build_manifest(ROOT)
    return {
        "source_manifest_sha256": "",
        "source_tree_sha256": str(current["tree_sha256"]),
    }


def requested_output() -> Path:
    for index, value in enumerate(sys.argv[:-1]):
        if value == "--output":
            return Path(sys.argv[index + 1])
    return ROOT / "validation" / f"machine-control-{release}.json"


def report_failures(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"MACHINE_CONTROL_REPORT_ERROR: {exc}")
        return
    failed = [item for item in data.get("checks", []) if item.get("pass") is not True]
    if not failed:
        return
    print("MACHINE_CONTROL_FAILED_CHECKS:")
    for item in failed:
        detail = str(item.get("detail", "")).strip().replace("\n", " | ")
        print(f"- {item.get('name', '<unnamed>')}: {detail[-1200:]}")


qualification.RELEASE = release
qualification.source_binding = current_source_binding

if __name__ == "__main__":
    rc = qualification.main()
    if rc != 0:
        report_failures(requested_output())
    raise SystemExit(rc)
