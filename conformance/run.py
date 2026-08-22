from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUITE = Path(__file__).resolve().parent
manifest = json.loads((SUITE / "manifest.json").read_text(encoding="utf-8"))
failed = []
for test in manifest["tests"]:
    command = [sys.executable, str(ROOT / "saga.py"), "check" if test["mode"] == "check-fail" else "run", str(SUITE / test["file"])]
    if test["mode"] in {"check-fail", "run-fail"}:
        command.extend(["--diagnostic-format", "json", "--language", "en"])
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ok = True
    if test["mode"] == "run":
        ok = result.returncode == test.get("exit_code", 0) and result.stdout.strip() == test["stdout"]
    elif test["mode"] in {"check-fail", "run-fail"}:
        try:
            document = json.loads(result.stderr)
            diagnostic = document.get("diagnostic", {})
        except json.JSONDecodeError:
            diagnostic = {}
        expected_category = test.get("diagnostic_code")
        expected_id = test.get("diagnostic_id")
        ok = (
            result.returncode == test.get("exit_code", result.returncode)
            and (not expected_category or diagnostic.get("code") == expected_category)
            and (not expected_id or diagnostic.get("id") == expected_id)
        )
    print(f"{'PASS' if ok else 'FAIL'} {test['id']} clause {test['clause']}")
    if not ok:
        failed.append({"test": test, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
if failed:
    print(json.dumps(failed, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit(1)
print(f"CONFORMANCE_CANDIDATE_OK {len(manifest['tests'])}")
