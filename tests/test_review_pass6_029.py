from __future__ import annotations

import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from saga.api import compile_source
from saga.aot import build
from saga.interpreter import Interpreter
from saga.values import OptionValue, ResultValue


class ReviewPass6Natural029Tests(unittest.TestCase):
    def test_result_equality_preserves_object_identity_semantics(self):
        source = '''
class Box(let value: int) {}
let a = Box(1)
let b = Box(1)
print(a == b)
print(some(a) == some(b))
print(ok(a) == ok(b))
'''
        program = compile_source(source)
        output: list[str] = []
        runtime = Interpreter(output=output.append)
        try:
            runtime.interpret(program)
        finally:
            runtime.close()
        self.assertEqual(output, ["false", "false", "false"])

    def test_task_snapshot_preserves_option_and_result_wrapper_cycles(self):
        source = Interpreter()
        target = Interpreter()
        try:
            option_map: dict[str, object] = {}
            option = OptionValue.some(option_map)
            option_map["self"] = option
            copied_option = source._snapshot_value_to(target, option, {})
            self.assertIs(copied_option.value["self"], copied_option)

            result_map: dict[str, object] = {}
            result = ResultValue.success(result_map)
            result_map["self"] = result
            copied_result = source._snapshot_value_to(target, result, {})
            self.assertIs(copied_result.value["self"], copied_result)
        finally:
            source.close()
            target.close()

    def test_repl_snapshot_preserves_option_and_result_wrapper_cycles(self):
        runtime = Interpreter()
        try:
            option_map: dict[str, object] = {}
            option = OptionValue.some(option_map)
            option_map["self"] = option
            copied_option = runtime._snapshot_session_value(option, {}, {})
            self.assertIs(copied_option.value["self"], copied_option)

            result_map: dict[str, object] = {}
            result = ResultValue.failure(result_map)
            result_map["self"] = result
            copied_result = runtime._snapshot_session_value(result, {}, {})
            self.assertIs(copied_result.value["self"], copied_result)
        finally:
            runtime.close()

    @unittest.skipUnless(shutil.which("clang"), "clang is required for scalar AOT parity")
    def test_scalar_aot_preserves_print_argument_evaluation_order_and_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "order.saga"
            source.write_text("""
fn first() -> int { print(\"first\") return 1 }
fn second() -> int { print(\"second\") return 2 }
print(first(), second())
fn done() -> unit { print(\"done\") return }
let u = done()
print(u)
print(done())
""", encoding="utf-8")
            expected = subprocess.run(
                [shutil.which("python3") or "python3", "-m", "saga", "run", str(source)],
                cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=True,
            ).stdout
            binary = root / "order"
            build(source, "native", binary)
            actual = subprocess.run([str(binary)], text=True, capture_output=True, check=True).stdout
            self.assertEqual(actual, expected)

    @unittest.skipUnless(shutil.which("clang"), "clang is required for scalar AOT parity")
    def test_scalar_aot_prints_bool_with_saga_text_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bools.saga"
            source.write_text('''
print(true)
let flag: bool = false
print(flag)
fn yes() -> bool { return true }
print(yes())
print(1 < 2)
''', encoding="utf-8")
            expected = subprocess.run(
                [shutil.which("python3") or "python3", "-m", "saga", "run", str(source)],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=True,
            ).stdout
            binary = root / "bools"
            build(source, "native", binary)
            actual = subprocess.run([str(binary)], text=True, capture_output=True, check=True).stdout
            self.assertEqual(actual, expected)

    def test_scalar_aot_fails_closed_for_unit_parameter_instead_of_emitting_invalid_c(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "unit_param.saga"
            source.write_text("""
fn take(x: unit) -> int { return 1 }
fn done() -> unit { return }
print(take(done()))
""", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "unit-valued function parameters"):
                build(source, "native", root / "unit_param")


if __name__ == "__main__":
    unittest.main()
