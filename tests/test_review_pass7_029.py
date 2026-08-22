from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from pathlib import Path
import tempfile
import unittest

from saga.api import compile_file, compile_source
from saga.aot import build_standard_bundle
from saga.interpreter import Interpreter
from saga.errors import SourceError
from saga.project import find_project, load_project, saga_files


@contextlib.contextmanager
def working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class ReviewPass7Natural029Tests(unittest.TestCase):
    def run_program(self, source: str) -> list[str]:
        program = compile_source(source)
        output: list[str] = []
        runtime = Interpreter(output=output.append)
        try:
            runtime.interpret(program)
        finally:
            runtime.close()
        return output

    def test_member_assignment_resolves_target_before_rhs(self):
        source = '''
class Box(var value: int) {}
let box = Box(0)
fn target() -> Box {
    print("target")
    return box
}
fn rhs() -> int {
    print("rhs")
    return 7
}
target().value = rhs()
print(box.value)
'''
        self.assertEqual(self.run_program(source), ["target", "rhs", "7"])

    def test_remainder_by_zero_has_stable_runtime_diagnostic(self):
        with self.assertRaises(SourceError) as caught:
            self.run_program("print(1 % 0)")
        self.assertEqual(caught.exception.code, "SAGA-R001")
        self.assertEqual(caught.exception.diagnostic_id, "SAGA-R102")

    def test_natural_binding_has_same_module_shadowing_rule_as_let(self):
        self.assertEqual(self.run_program("task = 1\nprint(task)"), ["1"])
        self.assertEqual(self.run_program("let task = 1\nprint(task)"), ["1"])

    def test_find_project_from_relative_subdirectory_walks_to_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            nested = root / "src" / "deep"
            nested.mkdir(parents=True)
            (root / "main.saga").write_text("print(1)", encoding="utf-8")
            (root / "saga.toml").write_text(
                '[project]\nname="walk"\nversion="1.0.0"\nentry="main.saga"\ntest_dir="tests"\n',
                encoding="utf-8",
            )
            (root / "tests").mkdir()
            with working_directory(nested):
                project = find_project(".")
            self.assertIsNotNone(project)
            assert project is not None
            self.assertEqual(project.root, root.resolve())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_source_entry_rejects_parent_component_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real = base / "real"
            real.mkdir()
            (real / "main.saga").write_text("print(1)", encoding="utf-8")
            alias = base / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with working_directory(base):
                with self.assertRaisesRegex(Exception, "シンボリックリンク"):
                    compile_file("alias/main.saga")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_saga_files_rejects_parent_component_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real = base / "real"
            sub = real / "src"
            sub.mkdir(parents=True)
            (sub / "main.saga").write_text("print(1)", encoding="utf-8")
            alias = base / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with working_directory(base):
                with self.assertRaisesRegex(ValueError, "シンボリックリンク"):
                    saga_files("alias/src")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_load_project_rejects_ancestor_component_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real_parent = base / "real-parent"
            root = real_parent / "project"
            root.mkdir(parents=True)
            (root / "main.saga").write_text("print(1)", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "saga.toml").write_text(
                '[project]\nname="aliaswalk"\nversion="1.0.0"\nentry="main.saga"\ntest_dir="tests"\n',
                encoding="utf-8",
            )
            alias = base / "alias"
            alias.symlink_to(real_parent, target_is_directory=True)
            with working_directory(base):
                with self.assertRaisesRegex(ValueError, "シンボリックリンク"):
                    load_project("alias/project/saga.toml")

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_standard_native_bundle_runs_natural_029_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "main.saga"
            output = root / ("main.exe" if os.name == "nt" else "main")
            source.write_text(
                "values = [3, 1, 2, 2]\n"
                "print(values |> map { it * 2 } |> distinct |> sorted |> take(2))\n"
                "greet = { print(\"Hello\") }\n"
                "greet()\n",
                encoding="utf-8",
            )
            build_standard_bundle(source, "native", output)
            result = subprocess.run([str(output)], text=True, capture_output=True, timeout=30, check=True)
            self.assertEqual(result.stdout.strip().splitlines(), ["[2, 4]", "Hello"])

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_standard_native_bundle_runs_bare_argument_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "main.saga"
            output = root / ("main.exe" if os.name == "nt" else "main")
            source.write_text(
                'fn panel(title:text,body:fn[unit]) { print(title) body() }\n'
                'print "Hello"\n'
                'panel "Todo" { print("inside") }\n',
                encoding="utf-8",
            )
            build_standard_bundle(source, "native", output)
            result = subprocess.run([str(output)], text=True, capture_output=True, timeout=30, check=True)
            self.assertEqual(result.stdout.strip().splitlines(), ["Hello", "Todo", "inside"])


if __name__ == "__main__":
    unittest.main()
