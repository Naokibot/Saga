from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from saga.native_codegen import build_native_codegen


class RuntimeSafety038Tests(unittest.TestCase):
    def test_incremental_minor_gc_is_budgeted_and_barrier_safe(self):
        cc = shutil.which("clang") or shutil.which("cc")
        if not cc:
            self.skipTest("C compiler unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "main.saga"
            source.write_text("print(1)\n", encoding="utf-8")
            build_native_codegen(source, root / "app", build_dir=root / "build")
            support = next((root / "build" / "support").glob("*"))
            support_obj = next(support.glob("saga_native_abi035.o"))
            harness = root / "minor.c"
            harness.write_text(r'''#include "saga_native_abi035.h"
#include <stdio.h>
int main(void) {
    if(!saga_gc_incremental_minor_available()) return 60;
    saga_gc_low_pause_enable(3);
    uint64_t mark=saga_gc_root_mark();
    SagaRef root=saga_object_new(UINT64_C(1),1); saga_gc_root_ref(&root);
    SagaRef child=saga_object_new(UINT64_C(2),1);
    saga_object_set(root,0,(SagaHeapValue){SAGA_HV_REF,{.ref=child}});
    for(int i=0;i<30;i++) (void)saga_object_new(UINT64_C(9),0);

    /* Start the nursery cycle, then mutate the graph while marking is active. */
    if(saga_gc_minor_step(1)==SAGA_GC_IDLE) return 61;
    SagaRef late=saga_object_new(UINT64_C(3),0);
    saga_object_set(child,0,(SagaHeapValue){SAGA_HV_REF,{.ref=late}});

    uint64_t polls=1;
    while(saga_gc_phase()!=SAGA_GC_IDLE){ saga_gc_poll(); if(++polls>200) return 62; }
    if(saga_gc_max_pause_work()>3) return 63;
    if(saga_gc_live_objects()!=3) return 64;
    if(saga_gc_incremental_minor_collections()!=1) return 65;

    /* A second nursery cycle promotes the surviving graph. */
    do { saga_gc_minor_step(3); if(++polls>400) return 66; } while(saga_gc_phase()!=SAGA_GC_IDLE);
    if(saga_gc_old_objects()!=3 || saga_gc_promotions()!=3) return 67;

    /* Old->young mutation must be remembered and survive the next nursery cycle. */
    SagaRef young=saga_object_new(UINT64_C(4),0);
    saga_object_set(root,0,(SagaHeapValue){SAGA_HV_REF,{.ref=young}});
    for(int i=0;i<12;i++) (void)saga_object_new(UINT64_C(8),0);
    do { saga_gc_minor_step(2); if(++polls>600) return 68; } while(saga_gc_phase()!=SAGA_GC_IDLE);
    if(saga_gc_live_objects()!=4) return 69;
    SagaHeapValue got=saga_object_get(root,0);
    if(got.kind!=SAGA_HV_REF || got.value.ref!=young) return 70;
    printf("minor_polls=%llu max=%llu live=%llu old=%llu inc_minor=%llu\n",
      (unsigned long long)polls,
      (unsigned long long)saga_gc_max_pause_work(),
      (unsigned long long)saga_gc_live_objects(),
      (unsigned long long)saga_gc_old_objects(),
      (unsigned long long)saga_gc_incremental_minor_collections());
    saga_gc_unwind_roots(mark); root=NULL; saga_gc_collect(); saga_gc_shutdown(); return 0;
}
''', encoding="utf-8")
            exe = root / "minor"
            build = subprocess.run([cc, "-std=c11", "-pthread", "-I", str(support), str(harness), str(support_obj), "-o", str(exe)], text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            self.assertIn("max=3", run.stdout)
            self.assertIn("live=4", run.stdout)
            self.assertIn("inc_minor=3", run.stdout)


if __name__ == "__main__":
    unittest.main()
