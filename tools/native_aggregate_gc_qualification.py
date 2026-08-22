#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.aot import AOTError
from saga.native_codegen import build_native_codegen

REL = "0.34.0"


def run(exe: Path) -> tuple[int, str, str]:
    p = subprocess.run([str(exe)], text=True, capture_output=True, timeout=30)
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=f"validation/native-aggregate-gc-qualification-{REL}.json")
    args = ap.parse_args()
    checks: list[dict[str, object]] = []

    def mark(name: str, ok: bool, detail: object = None) -> None:
        checks.append({"name": name, "pass": bool(ok), "detail": detail})
        if not ok:
            print(f"FAIL {name}: {detail}", file=sys.stderr)

    cc = shutil.which("clang") or shutil.which("cc") or shutil.which("gcc")
    mark("C compiler available", cc is not None, cc)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        models = root / "models.saga"
        main_src = root / "main.saga"
        models.write_text('''module models
public enum State { Ready, Running, Done }
public class Box(var value: int) {
  fn add(delta: int) -> int { self.value = self.value + delta; return self.value }
}
public fn make(value: int) -> Box = Box(value)
public fn state() -> State = State.Running
''', encoding="utf-8")
        main_src.write_text('''use "models.saga" as m
fn listDemo() -> int {
  let xs: list[int] = [1, 2, 3]
  return append(xs, 4)[3]
}
fn mapDemo() -> int {
  let m0: map[text, int] = map_of("a", 1)
  return map_get(map_put(m0, "b", 7), "b", 0)
}
fn setDemo() -> bool = set_contains(set_add(set_of(1, 2), 3), 3)
let box: m.Box = m.make(40)
print(listDemo())
print(mapDemo())
print(setDemo())
print(box.add(2))
print(m.state())
''', encoding="utf-8")
        build_dir = root / "build"
        try:
            first = build_native_codegen(main_src, root / "app", build_dir=build_dir)
            rc, out, err = run(first.output)
            mark("aggregate native executable preserves observable results", rc == 0 and out == "4\n7\ntrue\n42\nm.State.Running\n", {"rc": rc, "stdout": out, "stderr": err})
            abi_files = list((build_dir / "abi").glob("*.nabi.json"))
            abis = [json.loads(p.read_text()) for p in abi_files]
            model_abi = next(x for x in abis if x.get("module") == "models")
            kinds = {x.get("kind") for x in model_abi.get("exports", [])}
            mark("native ABI exports enum and class", {"enum", "class", "fn"}.issubset(kinds), model_abi)
            mark("managed heap memory model is ABI-bound", model_abi.get("memory_model") == "managed-ref-mark-sweep-preview", model_abi.get("memory_model"))

            second = build_native_codegen(main_src, root / "app", build_dir=build_dir)
            mark("unchanged aggregate build is full cache hit", not second.compiled_objects and not second.support_rebuilt and not second.startup_rebuilt and not second.linked, json.loads(second.report.read_text()))

            models.write_text(models.read_text().replace("self.value + delta", "self.value + delta + 1"), encoding="utf-8")
            third = build_native_codegen(main_src, root / "app", build_dir=build_dir)
            mark("class method implementation change rebuilds defining object only", third.compiled_objects == ("project/models.saga",), list(third.compiled_objects))

            # Private layout changes are still native ABI changes because constructor/object layout changes.
            models.write_text('''module models
public enum State { Ready, Running, Done }
public class Box(private let secret: text, var value: int) {
  fn add(delta: int) -> int { self.value = self.value + delta; return self.value }
}
public fn make(value: int) -> Box = Box("s", value)
public fn state() -> State = State.Running
''', encoding="utf-8")
            fourth = build_native_codegen(main_src, root / "app", build_dir=build_dir)
            mark("class layout ABI change invalidates importer", set(fourth.compiled_objects) == {"project/main.saga", "project/models.saga"}, list(fourth.compiled_objects))

            if cc:
                support_header = next((build_dir / "support").glob("*/saga_native_abi034.h"))
                support_obj = next((build_dir / "support").glob("*/saga_native_abi034.o"))
                harness = root / "gc.c"
                harness.write_text(r'''#include "saga_native_abi034.h"
#include <stdio.h>
int main(void) {
  uint64_t mark = saga_gc_root_mark();
  SagaRef root = saga_object_new(UINT64_C(1), 1); saga_gc_root_ref(&root);
  SagaRef list = saga_list_new(SAGA_HV_REF, 1); saga_gc_root_ref(&list);
  SagaRef leaf = saga_object_new(UINT64_C(2), 0); saga_gc_root_ref(&leaf);
  saga_list_push(list, (SagaHeapValue){SAGA_HV_REF,{.ref=leaf}});
  saga_object_set(root,0,(SagaHeapValue){SAGA_HV_REF,{.ref=list}});
  list=NULL; leaf=NULL; saga_gc_collect();
  printf("%llu %d %d\n", (unsigned long long)saga_gc_live_objects(), saga_allocator_live_bytes()>0, saga_allocator_peak_bytes()>=saga_allocator_live_bytes());
  root=NULL; saga_gc_collect();
  printf("%llu\n", (unsigned long long)saga_gc_live_objects());
  saga_gc_unwind_roots(mark); saga_gc_shutdown(); return 0;
}
''', encoding="utf-8")
                gc_exe = root / "gc"
                cp = subprocess.run([cc, "-std=c11", "-I", str(support_header.parent), str(harness), str(support_obj), "-o", str(gc_exe)], text=True, capture_output=True)
                grc, gout, gerr = run(gc_exe) if cp.returncode == 0 else (-1, "", cp.stderr)
                mark("mark/sweep traces nested managed references", cp.returncode == 0 and grc == 0 and gout == "3 1 1\n0\n", {"compile": cp.stderr, "stdout": gout, "stderr": gerr})

                tagged_harness = root / "tagged-gc.c"
                tagged_harness.write_text(r'''#include "saga_native_abi034.h"
#include <stdio.h>
int main(void) {
  uint64_t mark = saga_gc_root_mark();
  SagaRef leaf = saga_object_new(UINT64_C(7),0);
  SagaTagged tagged = {0}; tagged.type_id=UINT64_C(8); tagged.tag=0; tagged.arity=1;
  tagged.kinds[0]=SAGA_HV_REF; tagged.payload[0].ref=leaf; saga_gc_root_tagged(&tagged); leaf=NULL;
  saga_gc_collect(); printf("%llu\n",(unsigned long long)saga_gc_live_objects());
  tagged.payload[0].ref=NULL; saga_gc_collect(); printf("%llu\n",(unsigned long long)saga_gc_live_objects());
  saga_gc_unwind_roots(mark); saga_gc_shutdown(); return 0;
}
''', encoding="utf-8")
                tagged_exe = root / "tagged-gc"
                tcp = subprocess.run([cc, "-std=c11", "-I", str(support_header.parent), str(tagged_harness), str(support_obj), "-o", str(tagged_exe)], text=True, capture_output=True)
                trc, tout, terr = run(tagged_exe) if tcp.returncode == 0 else (-1, "", tcp.stderr)
                mark("tagged-union GC root traces managed payload", tcp.returncode == 0 and trc == 0 and tout == "1\n0\n", {"compile": tcp.stderr, "stdout": tout, "stderr": terr})

            tagged = root / "tagged.saga"
            tagged.write_text('enum Result { Ok(int), Err(text) }\nmatch Result.Ok(42) { case Result.Ok(v) { print(v) } case Result.Err(e) { print(e) } }\n', encoding="utf-8")
            tagged_result = build_native_codegen(tagged, root / "tagged", build_dir=root / "tagged-build")
            trc, tout, terr = run(tagged_result.output)
            mark("payload tagged union lowers directly to native ABI", trc == 0 and tout == "42\n", {"stdout": tout, "stderr": terr})

            inherited = root / "inherit.saga"
            inherited.write_text('class Base(let x:int) {}\nclass Child(let y:int) extends Base {}\nprint(1)\n', encoding="utf-8")
            try:
                build_native_codegen(inherited, root / "inherit", build_dir=root / "inherit-build")
                closed = False
            except AOTError:
                closed = True
            mark("unstable inheritance/virtual layout fails closed", closed, None)

            tagged_ref = root / "tagged-ref.saga"
            tagged_ref.write_text('fn maybe()->option[list[int]] { return some([1]) }\nprint(1)\n', encoding="utf-8")
            try:
                build_native_codegen(tagged_ref, root / "tagged-ref", build_dir=root / "tagged-ref-build")
                closed = False
            except AOTError:
                closed = True
            mark("managed references inside Option/Result fail closed until GC descriptors exist", closed, None)
        except Exception as exc:
            mark("qualification completed", False, f"{type(exc).__name__}: {exc}")

    report = {
        "schema": 1,
        "release": REL,
        "profile": "Native Aggregate & Managed Heap Preview",
        "checks": checks,
        "passed": sum(1 for x in checks if x["pass"]),
        "total": len(checks),
        "pass": bool(checks) and all(x["pass"] for x in checks),
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    print(f"{report['passed']}/{report['total']} checks passed")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
