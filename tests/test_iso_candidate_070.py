from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from saga import Capabilities, compile_source, run_source
from saga.api import compile_file, run_file
from saga.errors import RuntimeLanguageError
from saga.package import build_lock, pack_project, verify_lock


class SagaISOCandidate070Tests(unittest.TestCase):
    def test_object_identity_is_cycle_safe(self):
        source = '''
        class Node(var next: any) {}
        let a = Node(0)
        let b = Node(0)
        a.next = a
        b.next = b
        print(a == a, a == b)
        '''
        output: list[str] = []
        run_source(source, output=output.append)
        self.assertEqual(output, ["true false"])

    def test_deep_syntax_is_not_rejected_by_old_fixed_ceiling(self):
        source = "let value = " + "(" * 3000 + "1" + ")" * 3000
        compile_source(source)

    def test_decimal_overflow_is_catchable(self):
        output: list[str] = []
        run_source('try { print(decimal(10) ** 1000000) } catch e { print(e.kind) }', output=output.append)
        self.assertEqual(output, ["RuntimeLanguageError"])

    def test_parallel_map_enforces_send_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = f'''
            use db
            use task
            let connection = db.open("{root / 'x.db'}")
            fn inspect(value: any) -> int = 1
            print(task.parallel_map(inspect, [connection], 1))
            '''
            with self.assertRaises(RuntimeLanguageError) as raised:
                run_source(source, capabilities=Capabilities(db_roots=(root.resolve(),)))
            self.assertIn("共有可能なSaga値ではありません", str(raised.exception))

    def test_task_result_is_send_checked_and_class_is_remapped(self):
        output: list[str] = []
        source = '''
        use task
        class Box(let value: int) { fn get() -> int = self.value }
        fn make_box() -> Box = Box(42)
        let future = task.spawn(make_box)
        let box = task.await(future)
        print(box.get())
        '''
        run_source(source, output=output.append)
        self.assertEqual(output, ["42"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = f'''
            use db
            use task
            fn make_connection() -> any {{ return db.open("{root / 'task.db'}") }}
            let future = task.spawn(make_connection)
            print(task.await(future))
            '''
            with self.assertRaises(RuntimeLanguageError) as raised:
                run_source(source, capabilities=Capabilities(db_roots=(root,)))
            self.assertIn("task result", str(raised.exception))

    def test_source_units_are_checked_and_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "saga.toml").write_text('[project]\nname="units"\nversion="1.0.0"\nlanguage="0.8"\nentry="main.saga"\n', encoding="utf-8")
            (root / "math.saga").write_text('fn twice(value: int) -> int = value * 2\n', encoding="utf-8")
            (root / "main.saga").write_text('use "math.saga"\nprint(twice(21))\n', encoding="utf-8")
            loaded = compile_file(str(root / "main.saga"))
            self.assertEqual([p.name for p in loaded.files], ["math.saga", "main.saga"])
            output: list[str] = []
            run_file(str(root / "main.saga"), output=output.append)
            self.assertEqual(output, ["42"])

    def test_source_unit_cycle_and_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "saga.toml").write_text('[project]\nname="cycle"\nversion="1.0.0"\nlanguage="0.8"\nentry="a.saga"\n', encoding="utf-8")
            (root / "a.saga").write_text('use "b.saga"\n', encoding="utf-8")
            (root / "b.saga").write_text('use "a.saga"\n', encoding="utf-8")
            with self.assertRaises(Exception) as raised:
                compile_file(str(root / "a.saga"))
            self.assertIn("循環依存", str(raised.exception))
            outside = root.parent / "outside.saga"
            outside.write_text('print(1)\n', encoding="utf-8")
            (root / "a.saga").write_text('use "../outside.saga"\n', encoding="utf-8")
            with self.assertRaises(Exception) as escaped:
                compile_file(str(root / "a.saga"))
            self.assertIn("プロジェクト外", str(escaped.exception))

    def test_json_cycle_is_controlled_error(self):
        source = '''
        use json
        class Node(var next: any) {}
        let node = Node(0)
        node.next = node
        print(json.encode(node))
        '''
        with self.assertRaises(RuntimeLanguageError) as raised:
            run_source(source)
        self.assertIn("循環参照", str(raised.exception))

    def test_lock_and_package_are_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "saga.toml").write_text('[project]\nname="locked"\nversion="1.2.3"\nlanguage="0.8"\nentry="main.saga"\n', encoding="utf-8")
            (root / "main.saga").write_text('print(42)\n', encoding="utf-8")
            lock = build_lock(root)
            self.assertTrue(lock.path.is_file())
            self.assertEqual(verify_lock(root), (True, []))
            first = pack_project(root, root / "first.sagapkg")
            second = pack_project(root, root / "second.sagapkg")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            (root / "main.saga").write_text('print(43)\n', encoding="utf-8")
            valid, errors = verify_lock(root)
            self.assertFalse(valid)
            self.assertTrue(any("一致しません" in item for item in errors))

    def test_bom_and_crlf_are_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "main.saga"
            path.write_bytes(b"\xef\xbb\xbflet value = 42\r\nprint(value)\r\n")
            output: list[str] = []
            run_file(str(path), output=output.append)
            self.assertEqual(output, ["42"])

    def test_project_name_cannot_escape_package_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.saga").write_text("print(1)\n", encoding="utf-8")
            (root / "saga.toml").write_text('[project]\nname="../../escape"\nversion="1.0.0"\nlanguage="0.8"\nentry="main.saga"\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                compile_file(str(root / "main.saga"))

    def test_zero_major_semver_project_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.saga").write_text("print(1)\n", encoding="utf-8")
            (root / "saga.toml").write_text('[project]\nname="alpha"\nversion="0.1.0"\nlanguage="0.8"\nentry="main.saga"\n', encoding="utf-8")
            self.assertEqual(compile_file(str(root / "main.saga")).entry.name, "main.saga")

    def test_cli_uses_stable_exit_codes_and_json_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.saga"
            path.write_text('if 1 { print(1) }\n', encoding="utf-8")
            root = Path(__file__).resolve().parents[1]
            result = subprocess.run(
                [sys.executable, str(root / "saga.py"), "check", str(path), "--diagnostic-format", "json"],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 4)
            document = json.loads(result.stderr)
            self.assertEqual(document["diagnostic"]["code"], "SAGA-T001")

    def test_native_resource_types_and_standard_templates(self):
        from saga.typesys import NATIVE, parse_type
        from saga.project_templates import TEMPLATES
        self.assertEqual(parse_type("http_request"), NATIVE("http_request"))
        self.assertEqual(parse_type("http_response"), NATIVE("http_response"))
        self.assertNotIn("request: any", TEMPLATES["web"].files["main.saga"])
        self.assertNotIn("request: any", TEMPLATES["microservice"].files["main.saga"])
        self.assertIn("fn clicked() -> unit", TEMPLATES["desktop"].files["main.saga"])


if __name__ == "__main__":
    unittest.main()
