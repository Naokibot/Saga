from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import platform
from pathlib import Path
import shutil
import socket
import tempfile
import unittest

from saga.interpreter import Interpreter
from saga.native import Capabilities, NativeFailure
from saga.stdlib import MODULES
from saga.stdlib.modules import _freeze_external
from saga.values import OptionValue


class SagaReview0101Tests(unittest.TestCase):
    def native(self, interpreter: Interpreter, module: str, name: str, *args):
        return MODULES[module].get(name)(interpreter, list(args))

    def test_datetime_arithmetic_overflow_is_language_failure(self):
        interpreter = Interpreter(capabilities=Capabilities(allow_all=True))
        try:
            with self.assertRaises(NativeFailure):
                self.native(interpreter, "time", "add_days", datetime.max.replace(tzinfo=timezone.utc), 1)
        finally:
            interpreter.close()

    def test_negative_receive_size_is_rejected_before_host_socket(self):
        interpreter = Interpreter(capabilities=Capabilities(allow_all=True))
        left, right = socket.socketpair()
        try:
            with self.assertRaises(NativeFailure):
                self.native(interpreter, "net", "receive", left, -1)
        finally:
            left.close(); right.close(); interpreter.close()

    def test_external_object_cannot_leak_into_saga_value_space(self):
        with self.assertRaises(NativeFailure):
            _freeze_external(object())
        self.assertEqual(_freeze_external([1, 0.5, None]), (1, Decimal("0.5"), OptionValue.none()))

    def test_docdb_put_has_json_snapshot_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            interpreter = Interpreter(capabilities=Capabilities(db_roots=(root,)))
            try:
                store = self.native(interpreter, "docdb", "open", str(root / "db.json"))
                original = {"items": [1, 2]}
                # Native boundary uses tuple for Saga list; mutate the host dict
                # after put to prove the store did not retain the live object.
                original = {"value": 1}
                self.native(interpreter, "docdb", "put", store, "k", original)
                original["value"] = 99
                saved = self.native(interpreter, "docdb", "get", store, "k", {})
                self.assertEqual(saved["value"], 1)
            finally:
                interpreter.close()

    def test_plugin_preserves_datetime_duration_and_option_semantics(self):
        if platform.system().lower() != "linux" or not shutil.which("unshare"):
            self.skipTest("strict plugin sandbox needs Linux namespaces")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plugin.py"
            path.write_text(
                "def year(x): return x.year\n"
                "def seconds(x): return x.days * 86400 + x.seconds\n"
                "def add_option(x): return some(unwrap_or(x, 0) + 1)\n"
                "saga_exports={'year':year,'seconds':seconds,'add_option':add_option}\n",
                encoding="utf-8",
            )
            interpreter = Interpreter(capabilities=Capabilities(plugin_roots=(Path(td),)))
            try:
                plugin = self.native(interpreter, "plugin", "load", str(path))
                dt = datetime(2026, 8, 7, 10, 0, tzinfo=timezone(timedelta(hours=9)))
                self.assertEqual(self.native(interpreter, "plugin", "call", plugin, "year", dt), 2026)
                self.assertEqual(self.native(interpreter, "plugin", "call", plugin, "seconds", timedelta(days=2)), 172800)
                result = self.native(interpreter, "plugin", "call", plugin, "add_option", OptionValue.some(41))
                self.assertIsInstance(result, OptionValue)
                self.assertTrue(result.present)
                self.assertEqual(result.value, 42)
            finally:
                interpreter.close()

    def test_native_resource_contract_rejects_any_wrong_host_value(self):
        from saga.api import compile_source
        from saga.errors import RuntimeLanguageError
        source = """
use db
fn close_any(value: any) { db.close(value) }
close_any(42)
"""
        program = compile_source(source)
        interpreter = Interpreter("native-any.saga")
        try:
            with self.assertRaises(RuntimeLanguageError) as raised:
                interpreter.interpret(program)
            self.assertIn("ネイティブ資源型", str(raised.exception))
            self.assertNotIn("has no attribute", str(raised.exception))
        finally:
            interpreter.close()

    def test_image_resize_is_owned_resource_and_validates_dimensions(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / "x.png"; Image.new("RGB", (3, 2)).save(source)
            interpreter = Interpreter(capabilities=Capabilities(read_roots=(root,), write_roots=(root,)))
            try:
                image = self.native(interpreter, "image", "open", str(source))
                count = len(interpreter._resources)
                resized = self.native(interpreter, "image", "resize", image, 2, 1)
                self.assertEqual(len(interpreter._resources), count + 1)
                self.assertEqual(resized.size, (2, 1))
                with self.assertRaises(NativeFailure):
                    self.native(interpreter, "image", "resize", image, 0, 1)
            finally:
                interpreter.close()


if __name__ == "__main__":
    unittest.main()
