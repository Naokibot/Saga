#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.native_codegen import build_native_codegen, _constructor_symbol, _virtual_symbol
from tools.evidence_context import source_binding

REL = "0.50.0"


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(path)], text=True, capture_output=True, timeout=30)


def main() -> int:
    ap = argparse.ArgumentParser(description="Saga Native Runtime ABI 0.35 qualification")
    ap.add_argument("--output", default=str(ROOT / f"validation/native-runtime-qualification-{REL}.json"))
    args = ap.parse_args()
    checks: list[dict[str, object]] = []

    def mark(name: str, passed: bool, detail: object = None) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})
        if not passed:
            print(f"FAIL {name}: {detail}", file=sys.stderr)

    cc = shutil.which("clang") or shutil.which("cc") or shutil.which("gcc")
    mark("C11 compiler available", cc is not None, cc)

    with tempfile.TemporaryDirectory(prefix="saga-native-runtime-035-") as td:
        root = Path(td)
        src = root / "main.saga"
        src.write_text('''module runtime
public interface Greeter { fn greet() -> text }
public abstract class Person(let name: text) implements Greeter {
  override fn greet() -> text = "Hello " + self.name
  abstract fn role() -> text
}
public class Student(let school: text) extends Person {
  override fn greet() -> text = "Student " + self.name
  override fn role() -> text = "student"
}
public class Box[T](let value: T) { fn get() -> T = self.value }
fn first[T](xs: list[T]) -> T = xs[0]
fn maybe() -> option[list[int]] = some([4, 5])
fn outcome(s: Student) -> result[Student, text] = ok(s)
fn control() -> int { try { return 3 } finally { print("finally") } }
let s = Student("Aki", "Saga High")
let g: Greeter = s
let b: Box[text] = Box(g.greet())
print(b.get())
print(unwrap(maybe())[1])
print(unwrap_ok(outcome(s)).role())
print(first([8, 9]))
print(control())
try { print(5 % 0) } catch error { print(error.kind) } finally { print("done") }
''', encoding="utf-8")
        build_dir = root / "build"
        result = build_native_codegen(src, root / "app", build_dir=build_dir)
        executed = run(result.output)
        expected = "Student Aki\n5\nstudent\n8\nfinally\n3\nNativeFailure\ndone\n"
        mark("combined 0.35 native program executes", executed.returncode == 0 and executed.stdout == expected,
             {"returncode": executed.returncode, "stdout": executed.stdout, "stderr": executed.stderr})

        abi_path = next((build_dir / "abi").glob("*.nabi.json"))
        abi = json.loads(abi_path.read_text(encoding="utf-8"))
        mark("ABI identity is 0.35", abi.get("abi_version") == "0.35" and abi.get("language_version") == "0.35", {"abi": abi.get("abi_version"), "language": abi.get("language_version")})
        mark("generational/incremental/concurrent-sweep memory model is ABI-bound", abi.get("memory_model") == "managed-ref-generational-incremental-concurrent-sweep-0.35", abi.get("memory_model"))
        mark("open-world dispatch protocol is declared", abi.get("dispatch_model") == "open-world-registry-stable-slot-type-id-v1" and abi.get("runtime_feature_level") == "0.38", {"dispatch": abi.get("dispatch_model"), "feature_level": abi.get("runtime_feature_level")})

        classes = {item.get("name"): item for item in abi.get("exports", []) if item.get("kind") == "class"}
        student = classes.get("Student", {})
        greeter = classes.get("Greeter", {})
        dispatch_ok = (
            student.get("base") == "runtime.Person"
            and bool(greeter.get("interface"))
            and any(m.get("dispatch_slot") and m.get("dispatch_symbol") for m in greeter.get("methods", []))
        )
        mark("inheritance/interface/virtual dispatch descriptors exported", dispatch_ok, {"Student": student, "Greeter": greeter})

        generated = "\n".join(p.read_text(encoding="utf-8") for p in (build_dir / "generated").glob("*.c"))
        mark("generic specializations have concrete native symbols", generated.count("_g") >= 4 and "Box[" not in generated.split("/*", 1)[0], {"specialization_marker_count": generated.count("_g")})

        support_dir = next((build_dir / "support").glob("*"))
        support_obj = next(support_dir.glob("saga_native_abi035.o" if sys.platform != "win32" else "saga_native_abi035.obj"))
        support_header = support_dir / "saga_native_abi035.h"
        header = support_header.read_text(encoding="utf-8")
        mark("owned text / managed Option-Result / exception APIs exported",
             all(token in header for token in ["SagaText", "SagaOption", "SagaResult", "SagaExceptionFrame", "saga_gc_root_option", "saga_gc_root_result", "saga_abi035_text_concat", "saga_exception_enter"]), None)

        if cc is not None and not sys.platform.startswith("win"):
            virtual_harness = root / "virtual.c"
            ctor = _constructor_symbol("runtime", "Student")
            dispatch = _virtual_symbol("runtime.Greeter", "greet")
            virtual_harness.write_text(
                '#include "' + abi_path.name.replace('.nabi.json', '.nabi.h') + '"\n#include <stdio.h>\n'
                'int main(void){ SagaText n={(const uint8_t*)"Kai",3,NULL}; SagaText school={(const uint8_t*)"Saga",4,NULL};\n'
                f'  SagaRef s={ctor}(n,school); SagaText out={dispatch}(s);\n'
                '  fwrite(out.data,1,(size_t)out.len,stdout); fputc(\'\\n\',stdout); saga_gc_shutdown(); return 0; }\n',
                encoding="utf-8",
            )
            module_obj = next(obj for obj in result.objects if "main.saga" in obj.name)
            virtual_exe = root / "virtual"
            cp = subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-pedantic", "-pthread", "-I", str(support_dir), "-I", str(build_dir / "abi"), str(virtual_harness), str(module_obj), str(support_obj), "-o", str(virtual_exe)], text=True, capture_output=True)
            vr = run(virtual_exe) if cp.returncode == 0 else None
            mark("external C client calls virtual dispatch symbol", cp.returncode == 0 and vr is not None and vr.returncode == 0 and vr.stdout == "Student Kai\n", {"compile_stderr": cp.stderr, "stdout": vr.stdout if vr else "", "stderr": vr.stderr if vr else ""})

            gc_harness = root / "gc.c"
            gc_harness.write_text(r'''#include "saga_native_abi035.h"
#include <stdio.h>
int main(void){
  uint64_t mark=saga_gc_root_mark();
  SagaRef root=saga_list_new(SAGA_HV_REF,4); saga_gc_root_ref(&root);
  saga_gc_collect_minor(); saga_gc_collect_minor();
  if(saga_gc_old_objects()<1 || saga_gc_promotions()<1) return 31;
  SagaRef orphan=saga_list_new(SAGA_HV_I64,1);
  saga_list_push(orphan,(SagaHeapValue){SAGA_HV_I64,{.i64=77}});
  saga_gc_step(0);
  if(saga_gc_phase()!=SAGA_GC_MARKING) return 32;
  saga_list_push(root,(SagaHeapValue){SAGA_HV_REF,{.ref=orphan}}); orphan=NULL;
  for(int i=0;i<10000 && saga_gc_phase()==SAGA_GC_MARKING;i++) saga_gc_step(1);
  if(saga_gc_phase()==SAGA_GC_SWEEP_PENDING) saga_gc_step(1);
  SagaRef kept=saga_list_get(root,0).value.ref;
  if(!kept || saga_list_get(kept,0).value.i64!=77) return 33;
  /* Give the next major cycle genuinely dead work so the optional sweep
     thread is exercised instead of repeatedly starting empty cycles. */
  for(int i=0;i<20;i++){ SagaRef dead=saga_list_new(SAGA_HV_I64,1); saga_list_push(dead,(SagaHeapValue){SAGA_HV_I64,{.i64=i}}); }
  saga_gc_step(0);
  for(int i=0;i<10000 && saga_gc_phase()==SAGA_GC_MARKING;i++) saga_gc_step(1);
  if(saga_gc_phase()==SAGA_GC_SWEEP_PENDING) saga_gc_step(1);
  if(saga_gc_concurrent_sweep_available() && saga_gc_concurrent_sweeps()<1) return 35;
  printf("minor=%llu major=%llu concurrent=%llu\n",(unsigned long long)saga_gc_minor_collections(),(unsigned long long)saga_gc_major_collections(),(unsigned long long)saga_gc_concurrent_sweeps());
  saga_gc_unwind_roots(mark); root=NULL; saga_gc_collect();
  if(saga_gc_live_objects()!=0) return 34;
  saga_gc_shutdown(); return 0;
}
''', encoding="utf-8")
            gc_exe = root / "gc"
            cp = subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-pedantic", "-pthread", "-I", str(support_dir), str(gc_harness), str(support_obj), "-o", str(gc_exe)], text=True, capture_output=True)
            gr = run(gc_exe) if cp.returncode == 0 else None
            gc_ok = cp.returncode == 0 and gr is not None and gr.returncode == 0 and "minor=" in gr.stdout and "major=" in gr.stdout
            if gc_ok and "clang" in Path(cc).name:
                gc_ok = cp.stderr == ""
            mark("generational promotion + incremental mutation barrier + sweep complete", gc_ok, {"compile_stderr": cp.stderr, "stdout": gr.stdout if gr else "", "stderr": gr.stderr if gr else ""})

    try:
        binding = source_binding(REL)
    except RuntimeError:
        binding = {"source_manifest_sha256": None, "source_tree_sha256": None, "source_bound": False}
    report = {
        "schema": 1,
        "release": REL,
        **binding,
        "profile": "Native Runtime ABI 0.35 Preview",
        "checks": checks,
        "passed": sum(1 for row in checks if row["pass"]),
        "total": len(checks),
        "pass": bool(checks) and all(row["pass"] for row in checks),
        "limitations": [
            "Open-world dispatch is available to 0.37-generated/registered types; mixed use with older pre-registration binaries requires rebuild or an explicit registrar shim.",
            "GC provides budgeted incremental major mark/sweep and incremental nursery mark/sweep in low-pause mode; the synchronous minor API remains as a compatibility wrapper, and fully concurrent marking/compaction is not claimed.",
            "Public cross-module generic function/class specialization is supported; generic inheritance and generic methods remain fail-closed.",
            "Nested Option/Result descriptors inside generic heap slots are not part of ABI 0.35.",
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    print(f"{report['passed']}/{report['total']} checks passed")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
