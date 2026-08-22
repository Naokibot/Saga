#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.aot import AOTError
from saga.native_codegen import build_native_codegen, native_function_symbol

REL = "0.50.0"


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def run(exe: Path) -> tuple[int, str, str]:
    p = subprocess.run([str(exe)], text=True, capture_output=True, timeout=20)
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=f"validation/native-codegen-qualification-{REL}.json")
    args = ap.parse_args()
    report: dict[str, object] = {
        "schema": 1,
        "release": REL,
        "profile": "Native Codegen ABI 0.35",
        "checks": [],
        "pass": False,
    }

    def mark(name: str, ok: bool, detail: object = None) -> None:
        report["checks"].append({"name": name, "pass": bool(ok), "detail": detail})
        if not ok:
            print(f"FAIL {name}: {detail}", file=sys.stderr)

    cc = shutil.which("clang") or shutil.which("cc") or shutil.which("gcc")
    nm = shutil.which("nm")
    objdump = shutil.which("objdump")
    file_cmd = shutil.which("file")
    if not cc:
        mark("C compiler available", False, "clang/cc/gcc not found")
    else:
        mark("C compiler available", True, subprocess.check_output([cc, "--version"], text=True).splitlines()[0])

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        models = root / "models.saga"
        main_src = root / "main.saga"
        models.write_text('''module models
public fn twice(value: int) -> int = value * 2
public fn fact(n: int) -> int {
  if n <= 1 { return 1 }
  return n * fact(n - 1)
}
''', encoding="utf-8")
        main_src.write_text('''use "models.saga" as m
fn plusOne(value: int) -> int = m.twice(value) + 1
print(plusOne(20))
print(m.fact(5))
''', encoding="utf-8")
        build_dir = root / "build"
        exe = root / "app"
        try:
            first = build_native_codegen(main_src, exe, build_dir=build_dir)
            rc, out, err = run(exe)
            mark("direct-native executable runs", rc == 0 and out == "41\n120\n", {"rc": rc, "stdout": out, "stderr": err})
            mark("first build compiles two module objects", len(first.compiled_objects) == 2 and first.linked, list(first.compiled_objects))
            build_report = json.loads(first.report.read_text(encoding="utf-8"))
            mark("Go runtime is not linked", build_report.get("go_runtime_linked") is False, build_report)

            model_obj = next(p for p in first.objects if "models.saga" in p.name)
            main_obj = next(p for p in first.objects if "main.saga" in p.name)
            symbol = native_function_symbol("models", "twice")
            if file_cmd and os.name != "nt":
                desc = subprocess.check_output([file_cmd, str(model_obj)], text=True)
                mark("module is real relocatable object", "relocatable" in desc.lower(), desc.strip())
            if nm and os.name != "nt":
                model_nm = subprocess.check_output([nm, str(model_obj)], text=True)
                main_nm = subprocess.check_output([nm, str(main_obj)], text=True)
                final_nm = subprocess.check_output([nm, str(exe)], text=True)
                mark("callee object defines direct native symbol", f"T {symbol}" in model_nm, symbol)
                mark("caller object has native relocation to callee", f"U {symbol}" in main_nm, symbol)
                mark("final executable contains no Go runtime symbols", "runtime.main" not in final_nm and "crosscall" not in final_nm, None)
            if objdump and os.name != "nt":
                dis = subprocess.run([objdump, "-d", f"--disassemble={symbol}", str(model_obj)], text=True, capture_output=True)
                mark("Saga function has machine-code body", dis.returncode == 0 and symbol in dis.stdout and len(dis.stdout.splitlines()) > 6, dis.stdout[:1000])

            abi_json = next(p for p in (build_dir / "abi").glob("*.nabi.json") if json.loads(p.read_text())["module"] == "models")
            abi_header = next(p for p in (build_dir / "abi").glob("*.nabi.h") if "models.saga" in p.name)
            abi = json.loads(abi_json.read_text(encoding="utf-8"))
            mark("native ABI manifest exposes stable symbol", abi.get("abi_version") == "0.35" and any(e.get("symbol") == symbol for e in abi.get("exports", [])), abi)

            support_obj = next((build_dir / "support").rglob("saga_native_abi035.o" if os.name != "nt" else "saga_native_abi035.obj"))
            harness = root / "harness.c"
            harness.write_text(f'#include "{abi_header.name}"\n#include <stdio.h>\nint main(void) {{ printf("%lld\\n", (long long){symbol}(21)); return 0; }}\n', encoding="utf-8")
            harness_exe = root / "harness"
            p = subprocess.run([cc, "-pthread", str(harness), str(model_obj), str(support_obj), "-I", str(abi_header.parent), "-I", str(support_obj.parent), "-o", str(harness_exe)], text=True, capture_output=True)
            hrc, hout, herr = run(harness_exe) if p.returncode == 0 else (-1, "", p.stderr)
            mark("external C ABI client links Saga module directly", p.returncode == 0 and hrc == 0 and hout == "42\n", {"compile": p.stderr, "stdout": hout, "stderr": herr})

            second = build_native_codegen(main_src, exe, build_dir=build_dir)
            mark("unchanged build is complete cache hit", not second.compiled_objects and not second.support_rebuilt and not second.startup_rebuilt and not second.linked, json.loads(second.report.read_text()))

            models.write_text(models.read_text().replace("value * 2", "value * 3"), encoding="utf-8")
            third = build_native_codegen(main_src, exe, build_dir=build_dir)
            rc3, out3, _ = run(exe)
            mark("implementation-only change rebuilds callee object only", third.compiled_objects == ("project/models.saga",) and third.reused_objects == ("project/main.saga",) and rc3 == 0 and out3.startswith("61\n"), list(third.compiled_objects))

            models.write_text(models.read_text() + "public fn spare() -> int = 7\n", encoding="utf-8")
            fourth = build_native_codegen(main_src, exe, build_dir=build_dir)
            mark("public ABI change invalidates importer object", set(fourth.compiled_objects) == {"project/main.saga", "project/models.saga"}, list(fourth.compiled_objects))

            # Clean-build reproducibility on the same host/toolchain.
            clean1 = root / "clean1"
            clean2 = root / "clean2"
            out1 = root / "clean-app-1"
            out2 = root / "clean-app-2"
            one = build_native_codegen(main_src, out1, build_dir=clean1)
            two = build_native_codegen(main_src, out2, build_dir=clean2)
            one_objs = {p.name: sha(p) for p in one.objects}
            two_objs = {p.name: sha(p) for p in two.objects}
            mark("clean module objects are byte reproducible", one_objs == two_objs, {"first": one_objs, "second": two_objs})
            mark("clean executables are byte reproducible", sha(out1) == sha(out2), {"first": sha(out1), "second": sha(out2)})

            unsupported = root / "unsupported.saga"
            unsupported.write_text('class Base[T](let value: T) {}\nclass Child(let other: int) extends Base[int] {}\nprint(1)\n', encoding="utf-8")
            try:
                build_native_codegen(unsupported, root / "unsupported-app", build_dir=root / "unsupported-build")
                fail_closed = False
            except AOTError:
                fail_closed = True
            mark("generic inheritance remains fail closed", fail_closed, None)
        except Exception as exc:
            mark("qualification completed", False, f"{type(exc).__name__}: {exc}")

    report["pass"] = bool(report["checks"]) and all(item["pass"] for item in report["checks"])
    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out_path)
    print(f"{sum(1 for x in report['checks'] if x['pass'])}/{len(report['checks'])} checks passed")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
