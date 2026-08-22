#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.api import parse_source
from saga.ast_nodes import FunctionDecl
from saga.control_profile import is_control_tick, validate_control_tick


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Saga 0.47 @control_tick allocation-free source profile")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    program = parse_source(args.source.read_text(encoding="utf-8"), str(args.source))
    checked = 0
    violations = 0
    for stmt in program.statements:
        if not isinstance(stmt, FunctionDecl) or not is_control_tick(stmt):
            continue
        checked += 1
        for problem in validate_control_tick(stmt):
            violations += 1
            print(f"{args.source}:{problem.token.line}:{problem.token.column}: {problem.code}: {problem.message}")
    if checked == 0:
        print("no @control_tick functions found")
        return 2
    if violations:
        print(f"FAIL: {violations} profile violation(s) in {checked} control tick(s)")
        return 1
    print(f"PASS: {checked} @control_tick function(s) satisfy the Saga 0.47 source profile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
