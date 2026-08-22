from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from saga.aot import AOTError, build, build_standard_bundle, emit_c
from saga.api import compile_source, run_source
from saga.capability_audit import audit
from saga.cli import _source_path
from saga.debugger import debug_file
from saga.errors import ParseError, TypeCheckError
from saga.project import load_project


class ReviewPass4Natural029Tests(unittest.TestCase):
    def test_postfix_question_propagates_result_success_and_failure(self):
        source = '''
fn source(okay: bool) -> result[int, text] {
    if okay { return ok(4) }
    return err("bad")
}
fn consume(okay: bool) -> result[int, text] {
    let value = source(okay)?
    return ok(value + 1)
}
print(consume(true), consume(false))
'''
        out: list[str] = []
        run_source(source, output=out.append)
        self.assertEqual(out, ["ok(5) err(bad)"])

    def test_postfix_question_propagates_option(self):
        source = '''
fn source(found: bool) -> option[int] {
    if found { return some(9) }
    return none()
}
fn consume(found: bool) -> option[int] {
    let value = source(found)?
    return some(value + 1)
}
print(consume(true), consume(false))
'''
        out: list[str] = []
        run_source(source, output=out.append)
        self.assertEqual(out, ["some(10) none"])

    def test_postfix_question_requires_compatible_enclosing_return(self):
        with self.assertRaises(TypeCheckError):
            compile_source('fn bad() -> int { return some(1)? }')
        with self.assertRaises(TypeCheckError):
            compile_source('fn source()->result[int,int]{return err(1)} fn bad()->result[int,text]{let x=source()? return ok(x)}')

    def test_standard_bundle_supports_question_when_go_parity_exists(self):
        if not shutil.which("go"):
            self.skipTest("go unavailable")
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"; app = Path(td) / "app"
            src.write_text('fn a()->option[int]{return some(1)} fn b()->option[int]{let x=a()? return some(x)} print(b())\n')
            build_standard_bundle(src, "native", app)
            proc = subprocess.run([str(app)], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), "some(1)")

    def test_scalar_aot_rejects_exact_rational_division(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"
            src.write_text("print(5 / 2)\n")
            with self.assertRaisesRegex(AOTError, "exact rational division"):
                emit_c(src)

    def test_scalar_aot_traps_int64_overflow_instead_of_wrapping(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "main.saga"; exe = root / "app"
            src.write_text("print(9223372036854775807 + 1)\n")
            build(src, "native", exe)
            proc = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 70)
            self.assertIn("integer overflow", proc.stderr)
            self.assertNotIn("-9223372036854775808", proc.stdout)

    def test_scalar_aot_tracks_lexical_block_scope(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        source = "if true { x = 1 }\nx = 2\nprint(x)\n"
        out: list[str] = []; run_source(source, output=out.append)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "main.saga"; exe = root / "app"
            src.write_text(source)
            build(src, "native", exe)
            native = subprocess.check_output([str(exe)], text=True).splitlines()
        self.assertEqual(native, out)

    def test_scalar_aot_print_preserves_multi_argument_layout_and_unicode(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        source = 'print("日本😀", 7, 8)\n'
        out: list[str] = []; run_source(source, output=out.append)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "main.saga"; exe = root / "app"
            src.write_text(source, encoding="utf-8")
            build(src, "native", exe)
            native = subprocess.check_output([str(exe)], text=True).splitlines()
        self.assertEqual(native, out)

    def test_scalar_aot_range_endpoints_are_evaluated_once_left_to_right(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        source = '''
fn start()->int { print(10) return 1 }
fn finish()->int { print(20) return 2 }
for n in start()..finish() { print(n) }
'''
        out: list[str] = []; run_source(source, output=out.append)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "main.saga"; exe = root / "app"
            src.write_text(source)
            build(src, "native", exe)
            native = subprocess.check_output([str(exe)], text=True).splitlines()
        self.assertEqual(native, out)
        self.assertEqual(native, ["10", "20", "1", "2"])

    def test_scalar_aot_rejects_ambiguous_effectful_operand_order(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"
            src.write_text('fn side(x:int)->int { print(x) return x }\nprint(side(1) + side(2))\n')
            with self.assertRaisesRegex(AOTError, "left-to-right evaluation"):
                emit_c(src)

    def test_task_await_preserves_saga_throw_identity(self):
        source = '''
use task
fn fail() -> int { throw "boom" }
try {
    let future = task.spawn(fail)
    task.await(future)
} catch error {
    print(error.kind, error.message)
}
'''
        out: list[str] = []; run_source(source, output=out.append)
        self.assertEqual(out, ["Thrown boom"])

    def test_task_all_preserves_saga_throw_identity(self):
        source = '''
use task
fn fail() -> int { throw "boom" }
try {
    let a = task.spawn(fail)
    let b = task.spawn(fail)
    task.all([a, b])
} catch error {
    print(error.kind, error.message)
}
'''
        out: list[str] = []; run_source(source, output=out.append)
        self.assertEqual(out, ["Thrown boom"])

    def test_symlink_entry_policy_cannot_be_bypassed_by_tools(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            actual = root / "actual.saga"; actual.write_text("print(1)\n")
            link = root / "main.saga"; link.symlink_to(actual)
            with self.assertRaises(OSError): _source_path(str(link))
            with self.assertRaises(ParseError): emit_c(link)
            with self.assertRaises(ParseError): audit(link)
            with self.assertRaises(ParseError): debug_file(link, output=lambda _x: None, debug_output=lambda _x: None)

    def test_project_manifest_rejects_symlinked_entry_and_test_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            actual = root / "actual.saga"; actual.write_text("print(1)\n")
            (root / "main.saga").symlink_to(actual)
            (root / "tests-real").mkdir(); (root / "tests").symlink_to(root / "tests-real", target_is_directory=True)
            manifest = root / "saga.toml"
            manifest.write_text('[project]\nname="demo"\nversion="0.1.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests-real"\n')
            with self.assertRaisesRegex(ValueError, "project.entry"):
                load_project(manifest)
            (root / "main.saga").unlink(); (root / "main.saga").write_text("print(1)\n")
            manifest.write_text('[project]\nname="demo"\nversion="0.1.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n')
            with self.assertRaisesRegex(ValueError, "project.test_dir"):
                load_project(manifest)

    def test_scalar_aot_abs_evaluates_argument_once(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        source = 'fn next()->int { print(7) return 3 }\nprint(abs(next()))\n'
        expected: list[str] = []; run_source(source, output=expected.append)
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"; exe = Path(td) / "app"; src.write_text(source)
            build(src, "native", exe)
            proc = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout.splitlines(), expected)

    def test_scalar_aot_checked_modulo_zero(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        source = 'fn zero()->int{return 0}\nprint(5 % zero())\n'
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"; exe = Path(td) / "app"; src.write_text(source)
            build(src, "native", exe)
            proc = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 71)
            self.assertIn("modulo by zero", proc.stderr)

    def test_scalar_aot_mangles_c_reserved_identifiers(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        source = 'long = 3\nswitch = 4\nprint(long, switch)\n'
        expected: list[str] = []; run_source(source, output=expected.append)
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"; exe = Path(td) / "app"; src.write_text(source)
            build(src, "native", exe)
            proc = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout.splitlines(), expected)

if __name__ == "__main__":
    unittest.main()
