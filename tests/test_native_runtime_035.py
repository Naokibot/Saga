from __future__ import annotations

from pathlib import Path
import json
import subprocess
import tempfile
import unittest

from saga.native_codegen import AOTError, build_native_codegen, _constructor_symbol, _virtual_symbol


class NativeRuntime035Tests(unittest.TestCase):
    def write(self, root: Path, name: str, source: str) -> Path:
        path = root / name
        path.write_text(source, encoding="utf-8")
        return path

    def run_binary(self, path: Path) -> list[str]:
        result = subprocess.run([str(path)], text=True, capture_output=True, check=True)
        return result.stdout.splitlines()

    def test_inheritance_interface_and_virtual_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", '''
interface Greeter { fn greet() -> text }
abstract class Person(private var age: int, let name: text) implements Greeter {
    fn birthday() { self.age = self.age + 1 }
    override fn greet() -> text = "Hello " + self.name
    abstract fn role() -> text
}
class Student(let school: text) extends Person {
    override fn greet() -> text = "Student " + self.name
    override fn role() -> text = "student"
}
fn asPerson(x: Person) -> Person = x
fn asGreeter(x: Greeter) -> Greeter = x
let s = Student(15, "Aki", "Saga High")
let p: Person = asPerson(s)
let g: Greeter = asGreeter(s)
p.birthday()
print(p.greet())
print(p.role())
print(g.greet())
''')
            result = build_native_codegen(src, root / "app", build_dir=root / "build")
            self.assertEqual(self.run_binary(result.output), ["Student Aki", "student", "Student Aki"])
            abi = json.loads(next((root / "build" / "abi").glob("*.nabi.json")).read_text())
            classes = [item for item in abi["exports"] if item["kind"] == "class"]
            # Internal classes are not exported, but ABI identity still uses 0.35.
            self.assertEqual(abi["abi_version"], "0.35")

    def test_managed_option_result_and_owned_text(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", '''
class Box(let value: int) { fn get() -> int = self.value }
fn maybe() -> option[list[int]] = some([4, 5, 6])
fn outcome() -> result[Box, text] = ok(Box(42))
fn greeting(name: text) -> text = "Hello " + name + "!"
let xs: option[list[int]] = maybe()
let result: result[Box, text] = outcome()
print(unwrap(xs)[1])
print(unwrap_ok(result).get())
print(greeting("Saga"))
''')
            result = build_native_codegen(src, root / "app", build_dir=root / "build")
            self.assertEqual(self.run_binary(result.output), ["5", "42", "Hello Saga!"])

    def test_exception_unwind_nested_catch_and_finally(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", '''
fn nested() {
    try { throw "first" }
    catch error { print(error.message) throw "second" }
    finally { print("inner-finally") }
}
try { nested() }
catch error { print(error.kind) print(error.message) }
finally { print("outer-finally") }
''')
            result = build_native_codegen(src, root / "app", build_dir=root / "build")
            self.assertEqual(self.run_binary(result.output), ["first", "inner-finally", "Thrown", "second", "outer-finally"])

    def test_generic_function_and_aggregate_monomorphization(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", '''
fn first[T](items: list[T]) -> T = items[0]
class Box[T](let value: T) { fn get() -> T = self.value }
print(first(["a", "b"]))
print(first([7, 8]))
let n: Box[int] = Box(42)
let t: Box[text] = Box("hello")
print(n.get())
print(t.get())
''')
            result = build_native_codegen(src, root / "app", build_dir=root / "build")
            self.assertEqual(self.run_binary(result.output), ["a", "7", "42", "hello"])
            generated = "\n".join(p.read_text() for p in (root / "build" / "generated").glob("*.c"))
            self.assertGreaterEqual(generated.count("_g"), 4)

    def test_generational_incremental_and_concurrent_sweep_gc(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", "print(1)")
            build_native_codegen(src, root / "app", build_dir=root / "build")
            support = next((root / "build" / "support").glob("*"))
            obj = next(support.glob("saga_native_abi035.o"))
            harness = root / "gc.c"
            harness.write_text(r'''
#include "saga_native_abi035.h"
#include <stdio.h>
int main(void) {
    uint64_t mark=saga_gc_root_mark();
    SagaRef root=saga_list_new(SAGA_HV_REF,1); saga_gc_root_ref(&root);
    saga_gc_collect_minor(); saga_gc_collect_minor();
    if (saga_gc_promotions() < 1 || saga_gc_old_objects() < 1) return 10;
    SagaRef child=saga_list_new(SAGA_HV_I64,1);
    saga_list_push(child,(SagaHeapValue){SAGA_HV_I64,{.i64=7}});
    saga_list_push(root,(SagaHeapValue){SAGA_HV_REF,{.ref=child}}); child=NULL;
    saga_gc_collect_minor();
    SagaRef kept=saga_list_get(root,0).value.ref;
    if (saga_list_get(kept,0).value.i64 != 7) return 11;
    /* Two remembered old objects that reference each other used to recurse
       forever in minor marking. The old-object mark bit now guards that scan. */
    SagaRef a=saga_list_new(SAGA_HV_REF,4), b=saga_list_new(SAGA_HV_REF,4);
    saga_gc_root_ref(&a); saga_gc_root_ref(&b);
    saga_gc_collect_minor(); saga_gc_collect_minor();
    SagaRef ya=saga_list_new(SAGA_HV_I64,1), yb=saga_list_new(SAGA_HV_I64,1);
    saga_list_push(a,(SagaHeapValue){SAGA_HV_REF,{.ref=ya}});
    saga_list_push(b,(SagaHeapValue){SAGA_HV_REF,{.ref=yb}});
    saga_list_push(a,(SagaHeapValue){SAGA_HV_REF,{.ref=b}});
    saga_list_push(b,(SagaHeapValue){SAGA_HV_REF,{.ref=a}});
    ya=NULL; yb=NULL; saga_gc_collect_minor();
    if (!saga_list_get(a,0).value.ref || !saga_list_get(b,0).value.ref) return 14;
    /* Incremental-major insertion barrier: orphan is unreachable when the
       major cycle begins. Mutating the already-marked root must shade it. */
    SagaRef orphan=saga_list_new(SAGA_HV_I64,1);
    saga_list_push(orphan,(SagaHeapValue){SAGA_HV_I64,{.i64=99}});
    saga_gc_step(0);
    if (saga_gc_phase()!=SAGA_GC_MARKING) return 15;
    saga_list_push(root,(SagaHeapValue){SAGA_HV_REF,{.ref=orphan}}); orphan=NULL;
    for(int i=0;i<100;i++) { SagaRef x=saga_list_new(SAGA_HV_I64,1); saga_list_push(x,(SagaHeapValue){SAGA_HV_I64,{.i64=i}}); }
    for(int i=0;i<10000 && saga_gc_phase()!=SAGA_GC_SWEEP_PENDING;i++) saga_gc_step(1);
    SagaRef barrier_kept=saga_list_get(root,1).value.ref;
    if (!barrier_kept || saga_list_get(barrier_kept,0).value.i64 != 99) return 16;
    if (saga_gc_major_collections() < 1) return 12;
    if (saga_gc_concurrent_sweep_available() && saga_gc_concurrent_sweeps() < 1) return 13;
    saga_gc_step(1);
    saga_gc_unwind_roots(mark); root=NULL; saga_gc_collect();
    printf("%llu %llu %llu\n", (unsigned long long)saga_gc_minor_collections(), (unsigned long long)saga_gc_major_collections(), (unsigned long long)saga_gc_live_objects());
    saga_gc_shutdown(); return 0;
}
''', encoding="utf-8")
            exe = root / "gc"
            cc = subprocess.run(["clang", "-std=c11", "-pthread", "-I", str(support), str(harness), str(obj), "-o", str(exe)], text=True, capture_output=True)
            self.assertEqual(cc.returncode, 0, cc.stderr)
            run = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(run.stdout.strip().endswith(" 0"), run.stdout)

    def test_c_header_exposes_virtual_dispatch_symbol(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", """
module m
public abstract class Base(let name: text) { abstract fn greet() -> text }
public class Child(let id: int) extends Base { override fn greet() -> text = "child:" + self.name }
""")
            result = build_native_codegen(src, root / "app", build_dir=root / "build")
            support = next((root / "build" / "support").glob("*"))
            support_obj = next(support.glob("saga_native_abi035.o"))
            module_obj = next(obj for obj in result.objects if "main.saga" in obj.name)
            abi_header = next((root / "build" / "abi").glob("*.nabi.h"))
            ctor = _constructor_symbol("m", "Child")
            dispatch = _virtual_symbol("m.Base", "greet")
            header_text = abi_header.read_text()
            self.assertIn(ctor, header_text)
            self.assertIn(dispatch, header_text)
            harness = root / "virtual.c"
            harness.write_text(
                '#include "' + abi_header.name + '"\n#include <stdio.h>\n'
                'int main(void) {\n'
                '  SagaText name=(SagaText){(const uint8_t*)"Aki",3,NULL};\n'
                f'  SagaRef child={ctor}(name,7);\n'
                f'  SagaText out={dispatch}(child);\n'
                "  fwrite(out.data,1,(size_t)out.len,stdout); fputc('\\n',stdout);\n"
                '  saga_gc_shutdown(); return 0;\n}\n', encoding="utf-8")
            exe = root / "virtual"
            cc = subprocess.run(["clang", "-std=c11", "-pthread", "-I", str(support), "-I", str(root / "build" / "abi"), str(harness), str(module_obj), str(support_obj), "-o", str(exe)], text=True, capture_output=True)
            self.assertEqual(cc.returncode, 0, cc.stderr)
            run = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout, "child:Aki\n")

    def test_owned_text_root_lifetime_and_reclamation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", "print(1)")
            build_native_codegen(src, root / "app", build_dir=root / "build")
            support = next((root / "build" / "support").glob("*"))
            obj = next(support.glob("saga_native_abi035.o"))
            harness = root / "text.c"
            harness.write_text(r'''
#include "saga_native_abi035.h"
#include <stdio.h>
int main(void) {
    uint64_t mark=saga_gc_root_mark();
    SagaText a=(SagaText){(const uint8_t*)"hello",5,NULL};
    SagaText b=(SagaText){(const uint8_t*)" world",6,NULL};
    SagaText text=saga_abi035_text_concat(a,b);
    saga_gc_root_text(&text);
    if (!saga_abi035_text_is_owned(text)) return 20;
    saga_gc_collect();
    if (saga_gc_live_objects() != 1) return 21;
    fwrite(text.data,1,(size_t)text.len,stdout); fputc('\n',stdout);
    saga_gc_unwind_roots(mark); text=(SagaText){0}; saga_gc_collect();
    printf("live=%llu\n",(unsigned long long)saga_gc_live_objects());
    saga_gc_shutdown(); return 0;
}
''', encoding="utf-8")
            exe=root/"text"
            cc=subprocess.run(["clang","-std=c11","-pthread","-I",str(support),str(harness),str(obj),"-o",str(exe)],text=True,capture_output=True)
            self.assertEqual(cc.returncode,0,cc.stderr)
            run=subprocess.run([str(exe)],text=True,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(run.stdout.splitlines(),["hello world","live=0"])

    def test_native_runtime_failure_unwinds_to_catch(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=self.write(root,"main.saga",'''try { print(5 % 0) }
catch error { print(error.kind) print(error.message) }
finally { print("done") }
''')
            result=build_native_codegen(src,root/"app",build_dir=root/"build")
            self.assertEqual(self.run_binary(result.output),["NativeFailure","SAGA-R102: modulo by zero","done"])


    def test_mutated_local_is_preserved_across_longjmp(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", """
var value = 1
try { value = 2 throw \"jump\" }
catch error { print(value) print(error.message) }
print(value)
""")
            result = build_native_codegen(src, root / "app", build_dir=root / "build")
            self.assertEqual(self.run_binary(result.output), ["2", "jump", "2"])

    def test_return_break_and_continue_run_finally_before_transfer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = self.write(root, "main.saga", """
fn direct() -> int { try { return 1 } finally { print("return-finally") } }
fn caught() -> int { try { throw "x" } catch error { return 2 } finally { print("catch-finally") } }
var x = 0
while true { try { x = x + 1 break } finally { print("break-finally") } }
var y = 0
while y < 2 { y = y + 1 try { continue } finally { print("continue-finally") } }
print(direct())
print(caught())
print(x)
print(y)
""")
            result = build_native_codegen(src, root / "app", build_dir=root / "build")
            self.assertEqual(self.run_binary(result.output), [
                "break-finally", "continue-finally", "continue-finally",
                "return-finally", "1", "catch-finally", "2", "1", "2",
            ])


if __name__ == "__main__":
    unittest.main()
