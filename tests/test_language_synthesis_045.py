from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from saga.api import compile_source, run_file, run_source
from saga.errors import TypeCheckError
from saga.module_interface import build_module_interface


class LanguageSynthesis045Tests(unittest.TestCase):
    def run_program(self, source: str) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append)
        return output

    def test_async_function_returns_typed_future_and_await_unwraps(self):
        source = """
        async fn double(value: int) -> int {
            return value * 2
        }
        let pending: future[int] = double(21)
        print(await pending)
        """
        self.assertEqual(self.run_program(source), ["42"])

    def test_new_words_remain_contextual_for_legacy_identifiers(self):
        source = """
        fn await() -> int = 20
        fn move() -> int = 22
        let async = await() + move()
        var defer = async
        defer = defer + 1
        let using = defer + 1
        let taskgroup = using + 1
        print(async)
        print(defer)
        print(using)
        print(taskgroup)
        fn echo(await: int) -> int = await
        print(echo(46))
        """
        self.assertEqual(self.run_program(source), ["42", "43", "44", "45", "46"])

    def test_async_future_cannot_be_used_as_plain_result(self):
        source = """
        async fn double(value: int) -> int { return value * 2 }
        let value: int = double(21)
        """
        with self.assertRaises(TypeCheckError):
            compile_source(source)

    def test_taskgroup_joins_unawaited_async_work_before_leaving_scope(self):
        source = """
        async fn worker() -> unit {
            print("worker")
        }
        taskgroup {
            worker()
        }
        print("done")
        """
        self.assertEqual(self.run_program(source), ["worker", "done"])

    def test_defer_is_lifo_and_runs_before_return_completes(self):
        source = """
        fn first() -> unit { print("first") }
        fn second() -> unit { print("second") }
        fn value() -> int {
            defer first()
            defer second()
            return 7
        }
        print(value())
        """
        self.assertEqual(self.run_program(source), ["second", "first", "7"])

    def test_defer_also_works_in_first_class_closure(self):
        source = """
        fn cleanup() -> unit { print("cleanup") }
        let block: fn[int] = {
            defer cleanup()
            42
        }
        print(block())
        """
        self.assertEqual(self.run_program(source), ["cleanup", "42"])

    def test_using_closes_task_pool_scope(self):
        source = """
        use task
        fn identity(value: int) -> int = value
        using pool = task.pool(1) {
            let pending = task.submit(pool, identity, 9)
            print(task.await(pending))
        }
        print("closed")
        """
        self.assertEqual(self.run_program(source), ["9", "closed"])

    def test_move_is_single_use_for_resource_binding(self):
        source = """
        use task
        let pool = task.pool(1)
        task.shutdown(move pool)
        task.shutdown(pool)
        """
        with self.assertRaises(TypeCheckError):
            compile_source(source)

    def test_mutable_resource_can_be_reinitialized_after_move(self):
        source = """
        use task
        var pool = task.pool(1)
        task.shutdown(move pool)
        pool = task.pool(1)
        task.shutdown(move pool)
        print("ok")
        """
        self.assertEqual(self.run_program(source), ["ok"])

    def test_public_async_function_is_preserved_by_common_module_interface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            module = root / "jobs.saga"
            main = root / "main.saga"
            module.write_text(
                "module jobs\npublic async fn answer() -> int { return 42 }\n",
                encoding="utf-8",
            )
            interface = build_module_interface(module, root=root)
            export = next(item for item in interface["exports"] if item["name"] == "answer")
            self.assertEqual(export["return"], "future[int]")
            main.write_text(
                'use "jobs.saga" as jobs\nprint(await jobs.answer())\n',
                encoding="utf-8",
            )
            output: list[str] = []
            run_file(main, output=output.append)
            self.assertEqual(output, ["42"])

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_python_and_go_share_task_pool_using_and_move(self):
        source = """
        use task
        fn identity(value: int) -> int = value
        using pool = task.pool(1) {
            let pending = task.submit(pool, identity, 9)
            print(task.await(pending))
        }
        var second = task.pool(1)
        task.shutdown(move second)
        second = task.pool(1)
        task.shutdown(move second)
        print("ok")
        """
        py_output = self.run_program(source)
        self.assertEqual(py_output, ["9", "ok"])
        with tempfile.TemporaryDirectory() as td:
            program = Path(td) / "pool.saga"
            program.write_text(source, encoding="utf-8")
            go_dir = Path(__file__).resolve().parents[1] / "implementations" / "go" / "cmd" / "saga-go"
            go_run = subprocess.run(
                ["go", "run", ".", "run", str(program)],
                cwd=go_dir, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(go_run.returncode, 0, go_run.stdout + go_run.stderr)
            self.assertEqual(go_run.stdout.strip().splitlines(), py_output)

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_python_and_go_share_async_semantics_and_module_abi(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            program = root / "main.saga"
            program.write_text(
                'async fn double(x: int) -> int { return x * 2 }\n'
                'fn cleanup() -> unit { print("cleanup") }\n'
                'fn main() -> int { defer cleanup(); return await double(21) }\n'
                'print(main())\n',
                encoding="utf-8",
            )
            py_output: list[str] = []
            run_file(program, output=py_output.append)
            self.assertEqual(py_output, ["cleanup", "42"])

            go_dir = Path(__file__).resolve().parents[1] / "implementations" / "go" / "cmd" / "saga-go"
            go_run = subprocess.run(
                ["go", "run", ".", "run", str(program)],
                cwd=go_dir, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(go_run.returncode, 0, go_run.stdout + go_run.stderr)
            self.assertEqual(go_run.stdout.strip().splitlines(), py_output)

            module = root / "jobs.saga"
            module.write_text(
                'module jobs\npublic async fn answer() -> int { return 42 }\n',
                encoding="utf-8",
            )
            py_iface = build_module_interface(module, output=root / "python.smi.json")
            go_compile = subprocess.run(
                ["go", "run", ".", "module", "compile", str(module), str(root / "go.smi.json")],
                cwd=go_dir, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(go_compile.returncode, 0, go_compile.stdout + go_compile.stderr)
            go_iface = json.loads((root / "go.smi.json").read_text(encoding="utf-8"))
            self.assertEqual(py_iface["exports"], go_iface["exports"])
            self.assertEqual(py_iface["abi_sha256"], go_iface["abi_sha256"])



if __name__ == "__main__":
    unittest.main()
