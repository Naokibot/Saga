#!/usr/bin/env python3
"""Run machine-control qualification against the active checkout.

The frozen machine-control qualification keeps its original 0.50.0 manifest
binding for reproducibility.  Development CI uses this wrapper to bind evidence
to the current source tree without mutating historical release evidence.
"""
from __future__ import annotations

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


qualification.RELEASE = release
qualification.source_binding = current_source_binding

if __name__ == "__main__":
    raise SystemExit(qualification.main())
