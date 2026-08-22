from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from saga.debugger import debug_file, profile_file
from saga.native_codegen import (
    build_native_codegen,
    _dispatch_type_register_symbol,
    _virtual_symbol,
    _symbol_component,
)


class RuntimeScale037Tests(unittest.TestCase):
    def write(self, root: Path, name: str, source: str) -> Path:
        path = root / name
        path.write_text(source, encoding="utf-8")
        return path

    def run_binary(self, path: Path) -> list[str]:
        p = subprocess.run([str(path)], text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.splitlines()

    def test_cross_module_generic_function_and_class_specialize_in_caller(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "lib.saga", '''
module lib
public fn identity[T](value: T) -> T = value
public class Box[T](let value: T) { fn get() -> T = self.value }
''')
            main = self.write(root, "main.saga", '''
use "lib.saga" as lib
print(lib.identity(41))
print(lib.identity("open"))
let n: lib.Box[int] = lib.Box(42)
let t: lib.Box[text] = lib.Box("world")
print(n.get())
print(t.get())
''')
            result = build_native_codegen(main, root / "app", build_dir=root / "build")
            self.assertEqual(self.run_binary(result.output), ["41", "open", "42", "world"])
            generated = "\n".join(p.read_text(encoding="utf-8") for p in (root / "build" / "generated").glob("*.c"))
            self.assertGreaterEqual(generated.count("_g"), 4)

    def test_open_world_external_subtype_can_register_after_base_compilation(self):
        cc = shutil.which("clang") or shutil.which("cc")
        if not cc:
            self.skipTest("C compiler unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "base.saga", '''
module m
public class Base() { fn speak() -> text = "base" }
''')
            result = build_native_codegen(src, root / "app", build_dir=root / "build")
            support = next((root / "build" / "support").glob("*"))
            support_obj = next(support.glob("saga_native_abi035.o"))
            module_obj = next(obj for obj in result.objects if "base.saga" in obj.name)
            header = next((root / "build" / "abi").glob("*.nabi.h"))
            header_text = header.read_text(encoding="utf-8")
            type_macro = "SAGA_TYPE_" + _symbol_component("m.Base").upper()
            slot_macro = "SAGA_SLOT_" + _symbol_component("m.Base.speak").upper()
            self.assertIn(type_macro, header_text)
            self.assertIn(slot_macro, header_text)
            register = _dispatch_type_register_symbol("m.Base")
            virtual = _virtual_symbol("m.Base", "speak")
            harness = root / "extension.c"
            harness.write_text(f'''#include "{header.name}"
#include <stdio.h>
static void external_speak(SagaRef self, const void *const *args, void *result) {{
    (void)self; (void)args;
    SagaText *out=(SagaText*)result;
    *out=(SagaText){{(const uint8_t*)"external",8,NULL}};
}}
int main(void) {{
    const uint64_t extension_type=UINT64_C(0xe37e37e37e37e37e);
    {register}();
    saga_dispatch_register_type(extension_type,{type_macro});
    saga_dispatch_register_method(extension_type,{slot_macro},external_speak);
    SagaRef value=saga_object_new(extension_type,0);
    SagaText out={virtual}(value);
    fwrite(out.data,1,(size_t)out.len,stdout); fputc('\\n',stdout);
    saga_gc_shutdown();
    return 0;
}}
''', encoding="utf-8")
            exe = root / "extension"
            build = subprocess.run([
                cc, "-std=c11", "-pthread", "-I", str(support), "-I", str(header.parent),
                str(harness), str(module_obj), str(support_obj), "-o", str(exe),
            ], text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertEqual(self.run_binary(exe), ["external"])

    def test_open_world_registry_allows_concurrent_idempotent_registration(self):
        cc = shutil.which("clang") or shutil.which("cc")
        if not cc:
            self.skipTest("C compiler unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "base.saga", '''
module concurrent
public class Base() { fn value() -> int = 1 }
''')
            result = build_native_codegen(src, root / "app", build_dir=root / "build")
            support = next((root / "build" / "support").glob("*"))
            support_obj = next(support.glob("saga_native_abi035.o"))
            module_obj = next(obj for obj in result.objects if "base.saga" in obj.name)
            header = next((root / "build" / "abi").glob("*.nabi.h"))
            type_macro = "SAGA_TYPE_" + _symbol_component("concurrent.Base").upper()
            slot_macro = "SAGA_SLOT_" + _symbol_component("concurrent.Base.value").upper()
            register = _dispatch_type_register_symbol("concurrent.Base")
            virtual = _virtual_symbol("concurrent.Base", "value")
            harness = root / "concurrent.c"
            harness.write_text(f'''#include "{header.name}"
#include <threads.h>
#include <stdint.h>
static SagaRef shared;
static void external_value(SagaRef self,const void *const *args,void *result){{(void)self;(void)args;*((int64_t*)result)=7;}}
static int worker(void *unused){{
  (void)unused;
  for(int i=0;i<2000;i++){{
    {register}();
    saga_dispatch_register_type(UINT64_C(0xce37000000000001),{type_macro});
    saga_dispatch_register_method(UINT64_C(0xce37000000000001),{slot_macro},external_value);
    if({virtual}(shared)!=7)return 10;
  }}
  return 0;
}}
int main(void){{
  {register}();
  saga_dispatch_register_type(UINT64_C(0xce37000000000001),{type_macro});
  saga_dispatch_register_method(UINT64_C(0xce37000000000001),{slot_macro},external_value);
  shared=saga_object_new(UINT64_C(0xce37000000000001),0);
  thrd_t ts[4]; for(int i=0;i<4;i++)if(thrd_create(&ts[i],worker,NULL)!=thrd_success)return 20;
  for(int i=0;i<4;i++){{int rc=0;thrd_join(ts[i],&rc);if(rc)return rc;}}
  saga_gc_shutdown(); return 0;
}}
''', encoding="utf-8")
            exe = root / "concurrent"
            build = subprocess.run([cc, "-std=c11", "-pthread", "-I", str(support), "-I", str(header.parent), str(harness), str(module_obj), str(support_obj), "-o", str(exe)], text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_low_pause_major_gc_bounds_mark_and_sweep_work_per_poll(self):
        cc = shutil.which("clang") or shutil.which("cc")
        if not cc:
            self.skipTest("C compiler unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", "print(1)\n")
            build_native_codegen(src, root / "app", build_dir=root / "build")
            support = next((root / "build" / "support").glob("*"))
            support_obj = next(support.glob("saga_native_abi035.o"))
            harness = root / "low_pause.c"
            harness.write_text(r'''#include "saga_native_abi035.h"
#include <stdio.h>
int main(void) {
    uint64_t mark=saga_gc_root_mark();
    SagaRef root=saga_object_new(UINT64_C(7),0); saga_gc_root_ref(&root);
    for(int i=0;i<50;i++) (void)saga_object_new(UINT64_C(9),0);
    saga_gc_low_pause_enable(7);
    uint64_t polls=0;
    do { saga_gc_poll(); polls++; if(polls>1000) return 41; } while(saga_gc_phase()!=SAGA_GC_IDLE);
    if(saga_gc_pause_budget()!=7 || saga_gc_max_pause_work()>7) return 42;
    if(saga_gc_incremental_sweeps()<1 || saga_gc_live_objects()!=1) return 43;
    printf("polls=%llu max=%llu live=%llu\n",(unsigned long long)polls,(unsigned long long)saga_gc_max_pause_work(),(unsigned long long)saga_gc_live_objects());
    saga_gc_unwind_roots(mark); root=NULL; saga_gc_collect(); saga_gc_shutdown(); return 0;
}
''', encoding="utf-8")
            exe = root / "low_pause"
            build = subprocess.run([cc, "-std=c11", "-pthread", "-I", str(support), str(harness), str(support_obj), "-o", str(exe)], text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            out = self.run_binary(exe)
            self.assertEqual(len(out), 1)
            self.assertIn("max=7", out[0])
            self.assertIn("live=1", out[0])

    def test_python_debug_record_watch_and_profile(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", '''
var total: int = 0
for i in 1..5 { total = total + i }
print(total)
''')
            record = root / "debug.json"
            report = debug_file(src, watches=["total"], record_path=record, max_events=100)
            self.assertEqual(report["schema"], "saga.debug-record.v1")
            saved = json.loads(record.read_text(encoding="utf-8"))
            self.assertFalse(saved["truncated"])
            self.assertTrue(any(event["watch"].get("total") not in {None, "<unbound>"} for event in saved["events"]))
            profile_path = root / "profile.json"
            profile = profile_file(src, report_path=profile_path, top=5)
            self.assertEqual(profile["schema"], "saga.statement-profile.v1")
            self.assertGreater(profile["statement_events"], 0)
            self.assertGreaterEqual(profile["python_heap_peak_bytes"], profile["python_heap_current_bytes"])


if __name__ == "__main__":
    unittest.main()
