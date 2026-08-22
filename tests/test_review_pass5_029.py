from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from saga.aot import AOTError, build, emit_c
from saga.api import run_source
from saga.cli import main as cli_main
from saga.package import PackageError, build_lock, pack_project
from saga.project import load_project


class ReviewPass5Natural029Tests(unittest.TestCase):
    def test_task_snapshot_preserves_alias_between_repeated_arguments(self):
        source = '''
use task
class Box(var value: int) {}
fn same(a: Box, b: Box) -> bool { return a == b }
let box = Box(1)
let future = task.spawn(same, box, box)
print(task.await(future))
'''
        out: list[str] = []
        run_source(source, output=out.append)
        self.assertEqual(out, ["true"])

    def test_task_snapshot_preserves_alias_between_globals(self):
        source = '''
use task
class Box(var value: int) {}
let first = Box(1)
let second = first
fn globals_same() -> bool { return first == second }
print(task.await(task.spawn(globals_same)))
'''
        out: list[str] = []
        run_source(source, output=out.append)
        self.assertEqual(out, ["true"])

    def test_task_snapshot_preserves_alias_between_global_and_argument(self):
        source = '''
use task
class Box(var value: int) {}
let saved = Box(1)
fn same_as_saved(value: Box) -> bool { return saved == value }
print(task.await(task.spawn(same_as_saved, saved)))
'''
        out: list[str] = []
        run_source(source, output=out.append)
        self.assertEqual(out, ["true"])


    def test_task_all_joins_later_futures_before_raising(self):
        source = '''
use task
use time
fn fail() -> int { throw "boom" }
fn slow() -> int { time.sleep(0.03) print("slow") return 1 }
try {
    let a = task.spawn(fail)
    let b = task.spawn(slow)
    task.all([a, b])
} catch error {
    print("caught")
}
'''
        out: list[str] = []
        run_source(source, output=out.append)
        self.assertEqual(out, ["slow", "caught"])

    def test_fmt_directory_rejects_saga_symlink_without_touching_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"; project.mkdir()
            outside = root / "outside.saga"; outside.write_text("  print(1)  \n\n\n")
            link = project / "linked.saga"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            before = outside.read_bytes()
            self.assertNotEqual(cli_main(["fmt", str(project)]), 0)
            self.assertEqual(outside.read_bytes(), before)

    def test_migrate_write_directory_rejects_saga_symlink_without_touching_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"; project.mkdir()
            outside = root / "outside.saga"; outside.write_text("let xs = filter(is_ok, values)\n")
            link = project / "linked.saga"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            before = outside.read_bytes()
            self.assertNotEqual(cli_main(["migrate", "--write", str(project)]), 0)
            self.assertEqual(outside.read_bytes(), before)

    def test_load_project_rejects_symlinked_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); real = root / "real.toml"
            real.write_text('[project]\nname="demo"\nversion="0.1.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n')
            link = root / "saga.toml"
            try:
                link.symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            with self.assertRaisesRegex(ValueError, "シンボリックリンク"):
                load_project(link)

    def test_package_commands_cannot_bypass_manifest_symlink_policy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; project.mkdir()
            (project / "main.saga").write_text("print(1)\n")
            manifest = project / "saga.toml"
            manifest.write_text('[project]\nname="demo"\nversion="0.1.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n')
            link = root / "linked.toml"
            try:
                link.symlink_to(manifest)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            with self.assertRaisesRegex(PackageError, "シンボリックリンク"):
                build_lock(link)

    def test_pack_rejects_symlink_output_without_overwriting_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; project.mkdir()
            (project / "main.saga").write_text("print(1)\n")
            (project / "saga.toml").write_text('[project]\nname="demo"\nversion="0.1.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n')
            build_lock(project)
            outside = root / "outside.bin"; outside.write_bytes(b"KEEP")
            output = root / "demo.sagapkg"
            try:
                output.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            with self.assertRaisesRegex(PackageError, "symbolic|シンボリック"):
                pack_project(project, output)
            self.assertEqual(outside.read_bytes(), b"KEEP")


    def test_source_loader_rejects_symlinked_project_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); real = root / "real"; real.mkdir()
            (real / "main.saga").write_text("print(1)\n")
            (real / "saga.toml").write_text('[project]\nname="demo"\nversion="0.1.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n')
            link = root / "linked"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            from saga.api import compile_file
            from saga.errors import ParseError
            with self.assertRaisesRegex(ParseError, "シンボリックリンク"):
                compile_file(link / "main.saga")
            with self.assertRaisesRegex(ValueError, "シンボリックリンク"):
                load_project(link / "saga.toml")
            self.assertNotEqual(cli_main(["check", str(link / "main.saga")]), 0)

    def test_pack_default_dist_rejects_symlink_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; project.mkdir()
            (project / "main.saga").write_text("print(1)\n")
            (project / "saga.toml").write_text('[project]\nname="demo"\nversion="0.1.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n')
            build_lock(project)
            outside = root / "outside"; outside.mkdir()
            try:
                (project / "dist").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            with self.assertRaisesRegex(PackageError, "シンボリックリンク"):
                pack_project(project)
            self.assertEqual(list(outside.iterdir()), [])

    def test_scalar_aot_rejects_symlink_output_without_overwriting_target(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "main.saga"; src.write_text("print(1)\n")
            outside = root / "outside.bin"; outside.write_bytes(b"KEEP")
            output = root / "app"
            try:
                output.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            with self.assertRaisesRegex(AOTError, "symbolic link"):
                build(src, "native", output)
            self.assertEqual(outside.read_bytes(), b"KEEP")

    def test_scalar_aot_rejects_top_level_binding_capture_instead_of_changing_meaning(self):
        source = '''
var x: int = 1
fn change() -> int { x = 2 return x }
print(change(), x)
'''
        expected: list[str] = []
        run_source(source, output=expected.append)
        self.assertEqual(expected, ["2 2"])
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"; src.write_text(source)
            with self.assertRaisesRegex(AOTError, "top-level binding capture"):
                emit_c(src)

    def test_scalar_aot_forward_function_reference_matches_interpreter(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        source = '''
fn first() -> int { return second() }
fn second() -> int { return 42 }
print(first())
'''
        expected: list[str] = []; run_source(source, output=expected.append)
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"; exe = Path(td) / "app"; src.write_text(source)
            build(src, "native", exe)
            proc = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.splitlines(), expected)


    def test_scalar_aot_range_continue_at_endpoint_terminates(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        source = 'for n in 1..2 { if n == 2 { continue } print(n) }\n'
        expected: list[str] = []; run_source(source, output=expected.append)
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"; exe = Path(td) / "app"; src.write_text(source)
            build(src, "native", exe)
            proc = subprocess.run([str(exe)], capture_output=True, text=True, timeout=2)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.splitlines(), expected)

    def test_scalar_aot_utf8_followed_by_hex_digit_is_byte_exact(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        for text in ("éA", "éF", "🙂a"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as td:
                source = f'print("{text}")\n'
                expected: list[str] = []; run_source(source, output=expected.append)
                src = Path(td) / "main.saga"; exe = Path(td) / "app"
                src.write_text(source, encoding="utf-8")
                build(src, "native", exe)
                proc = subprocess.run([str(exe)], capture_output=True)
                self.assertEqual(proc.returncode, 0, proc.stderr.decode(errors="replace"))
                self.assertEqual(proc.stdout, (expected[0] + "\n").encode("utf-8"))

    def test_scalar_aot_embedded_nul_text_print_is_byte_exact(self):
        if not shutil.which("clang"):
            self.skipTest("clang unavailable")
        source = 'print("x\x00y")\n'
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "main.saga"; exe = Path(td) / "app"
            src.write_text(source)
            build(src, "native", exe)
            proc = subprocess.run([str(exe)], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode(errors="replace"))
            self.assertEqual(proc.stdout, b"x\x00y\n")


if __name__ == "__main__":
    unittest.main()
