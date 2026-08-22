#!/usr/bin/env python3
"""Run live registry qualification against the version declared by this checkout."""
from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

with (ROOT / "pyproject.toml").open("rb") as fh:
    release = str(tomllib.load(fh)["project"]["version"])

from tools import review_evidence

review_evidence.RELEASE = release

from tools import registry_live_qualification as qualification

qualification.REL = release

if __name__ == "__main__":
    raise SystemExit(qualification.main())
