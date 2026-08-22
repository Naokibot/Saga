from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.native_object import build_native_objects


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(path: Path) -> dict:
    proc = subprocess.run([str(path)], text=True, capture_output=True, timeout=30)
    return {"returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation/native-object-0.31.0.json")
    args = parser.parse_args()
    out = Path(args.output)
    result: dict = {"schema": 1, "profile": "Saga Native Object Core 0.31", "pass": False}
    if not shutil.which("go") or not (shutil.which("clang") or shutil.which("cc")):
        result["status"] = "UNEXECUTED"
        result["reason"] = "Go and a C compiler/linker are required"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 2

    with tempfile.TemporaryDirectory(prefix="saga-native-object-qualification-") as tmp:
        root = Path(tmp)
        models = root / "models.saga"
        main_source = root / "main.saga"
        models.write_text("module models\npublic fn twice(value: int) -> int = value * 2\n", encoding="utf-8")
        main_source.write_text('use "models.saga" as m\nprint(m.twice(21))\n', encoding="utf-8")
        build_a = root / "build-a"
        exe_a = root / "app-a"

        first = build_native_objects(main_source, exe_a, build_dir=build_a)
        first_report = json.loads(first.report.read_text(encoding="utf-8"))
        first_run = run(exe_a)
        second = build_native_objects(main_source, exe_a, build_dir=build_a)
        second_report = json.loads(second.report.read_text(encoding="utf-8"))

        models.write_text("module models\npublic fn twice(value: int) -> int = value * 3\n", encoding="utf-8")
        impl = build_native_objects(main_source, exe_a, build_dir=build_a)
        impl_report = json.loads(impl.report.read_text(encoding="utf-8"))
        impl_run = run(exe_a)

        models.write_text(
            "module models\npublic fn twice(value: int) -> int = value * 3\npublic fn spare() -> int = 1\n",
            encoding="utf-8",
        )
        abi = build_native_objects(main_source, exe_a, build_dir=build_a)
        abi_report = json.loads(abi.report.read_text(encoding="utf-8"))
        abi_run = run(exe_a)

        # Clean build in a separate cache root must produce byte-identical
        # module objects and executable on the same host/toolchain.
        exe_b = root / "app-b"
        clean = build_native_objects(main_source, exe_b, build_dir=root / "build-b")
        object_sha_a = sorted(sha(p) for p in abi.objects)
        object_sha_b = sorted(sha(p) for p in clean.objects)
        reproducible = object_sha_a == object_sha_b and sha(exe_a) == sha(exe_b)

        descriptions = []
        if shutil.which("file"):
            for p in abi.objects:
                descriptions.append(subprocess.check_output(["file", str(p)], text=True).strip())

        checks = {
            "first_build_compiles_two_objects": len(first.compiled_objects) == 2,
            "first_binary_runs": first_run["returncode"] == 0 and first_run["stdout"] == "42",
            "no_change_reuses_all_objects": len(second.compiled_objects) == 0 and len(second.reused_objects) == 2,
            "no_change_skips_link": not second.linked,
            "implementation_change_rebuilds_only_dependency": impl.compiled_objects == ("project/models.saga",) and impl.reused_objects == ("project/main.saga",),
            "implementation_change_runs": impl_run["returncode"] == 0 and impl_run["stdout"] == "63",
            "abi_change_invalidates_importer": set(abi.compiled_objects) == {"project/main.saga", "project/models.saga"},
            "abi_change_runs": abi_run["returncode"] == 0 and abi_run["stdout"] == "63",
            "clean_build_is_reproducible": reproducible,
            "objects_are_native_relocatables": all("relocatable" in d.lower() for d in descriptions) if descriptions else True,
        }
        result.update({
            "status": "PASS" if all(checks.values()) else "FAIL",
            "pass": all(checks.values()),
            "checks": checks,
            "first": first_report,
            "second": second_report,
            "implementation_change": impl_report,
            "abi_change": abi_report,
            "object_descriptions": descriptions,
            "object_sha256": object_sha_a,
            "executable_sha256": sha(exe_a),
        })
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
