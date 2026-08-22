#!/usr/bin/env python3
"""Run platform qualification against the active checkout.

Historical qualification modules retain the release/version assumptions they
were introduced with.  This wrapper binds the active CI run to the version and
source tree in the current checkout without rewriting frozen release evidence.
"""
from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

with (ROOT / "pyproject.toml").open("rb") as fh:
    release = str(tomllib.load(fh)["project"]["version"])

from tools import platform_qualification as qualification

qualification.RELEASE = release

# The historical platform runner launches the frozen machine-control evidence
# script.  Active-branch CI must instead record the current source tree while
# leaving the frozen 0.50.0 manifest untouched.
_original_run = qualification.run
_historical_machine_tool = str(ROOT / "tools/machine_control_qualification.py")
_current_machine_tool = str(ROOT / "tools/machine_control_qualification_current.py")


def _run_current(cmd, *, cwd=ROOT, env=None, timeout=180):
    if isinstance(cmd, list) and _historical_machine_tool in cmd:
        cmd = [_current_machine_tool if part == _historical_machine_tool else part for part in cmd]
    return _original_run(cmd, cwd=cwd, env=env, timeout=timeout)


qualification.run = _run_current

# spark.sql returns list[map[text, any]].  Index the guaranteed single-row SQL
# result directly; using get(..., map_of()) weakens the fallback to map[any, any]
# and correctly fails Saga's type checker.
def _qualify_spark_current() -> dict:
    if importlib.util.find_spec("pyspark") is None:
        return qualification.gate(
            "spark-runtime",
            "READY_UNEXECUTED",
            reason="pyspark is not installed on this host; CI installs it and executes local[2] qualification",
        )
    try:
        from saga.api import run_source
        from saga.native import Capabilities

        out: list[str] = []
        run_source(
            'use spark\n'
            'let s = spark.local_session("SagaQualification", 2)\n'
            'print(spark.range_count(s, 0, 100))\n'
            'let rows = spark.sql(s, "SELECT 6 * 7 AS answer")\n'
            'print(map_get(rows[0], "answer", 0))\n'
            'spark.stop(s)',
            output=out.append,
            capabilities=Capabilities(allow_process=True),
        )
        if out != ["100", "42"]:
            raise RuntimeError(f"unexpected output {out!r}")
        return qualification.gate(
            "spark-runtime",
            "PASS",
            detail="local[2] Range/DataFrame count and Spark SQL executed through Saga",
        )
    except Exception as exc:
        return qualification.gate("spark-runtime", "FAIL", reason=f"{type(exc).__name__}: {exc}")


qualification.qualify_spark = _qualify_spark_current

if __name__ == "__main__":
    raise SystemExit(qualification.main())
