#!/usr/bin/env python3
"""Run platform qualification against the version declared by this checkout.

The historical platform_qualification module keeps the release it was originally
introduced with for reproducibility. CI and active development should use this
wrapper so generated evidence follows pyproject.toml instead of a stale literal.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

with (ROOT / "pyproject.toml").open("rb") as fh:
    release = str(tomllib.load(fh)["project"]["version"])

from tools import platform_qualification as qualification

qualification.RELEASE = release

if __name__ == "__main__":
    raise SystemExit(qualification.main())
