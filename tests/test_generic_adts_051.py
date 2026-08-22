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


class GenericADTs051Tests(unittest.TestCase):
    def run_program(self, source: str) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append)
        return output

    def test_payload_constructor_infers_type_and_match_specializes_binding(self):
        source = """
        enum Maybe[T] { None, Some(T) }
        let value = Maybe.Some(42)
        match value {
            case Maybe.Some(item) { let checked: int = item; print(checked) }
            case Maybe.None { print(0) }
        }
        """
        self.assertEqual(self.run_program(source), ["42"])

    def test_nullary_generic_variant_uses_contextual_type(self):
        source = """
        enum Maybe[T] { None, Some(T) }
        let value: Maybe[int] = Maybe.None
        match value {
            case Maybe.Some(item) { print(item) }
            case Maybe.None { print("empty") }
        }
        """
        self.assertEqual(self.run_program(source), ["empty"])

    def test_nullary_generic_variant_without_context_is_rejected(self):
        source = """
        enum Maybe[T] { None, Some(T) }
        let value = Maybe.None
        """
        with self.assertRaises(TypeCheckError) as caught:
            compile_source(source)
        self.assertIn("SAGA-T113", str(caught.exception))

    def test_context_completes_partially_inferred_enum_parameters(self):
        source = """
        enum Either[L, R] { Left(L), Right(R) }
        let value: Either[int, text] = Either.Left(7)
        match value {
            case Either.Left(item) { let checked: int = item; print(checked) }
            case Either.Right(message) { let checked: text = message; print(checked) }
        }
        """
        self.assertEqual(self.run_program(source), ["7"])

    def test_generic_enum_arity_is_checked(self):
        source = """
        enum Maybe[T] { None, Some(T) }
        let value: Maybe[int, text] = Maybe.Some(1)
        """
        with self.assertRaises(TypeCheckError):
            compile_source(source)

    def test_module_interface_preserves_generic_enum_abi(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            module = root / "maybe.saga"
            module.write_text(
                "module maybe\npublic enum Maybe[T] { None, Some(T) }\n",
                encoding="utf-8",
            )
            interface = build_module_interface(module, root=root)
            export = next(item for item in interface["exports"] if item["name"] == "Maybe")
            self.assertEqual(export["type_params"], ["T"])
            self.assertEqual(export["variants"][1]["payload"], ["T"])

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_python_and_go_share_generic_adt_runtime_and_module_abi(self):
        source = """
        enum Maybe[T] { None, Some(T) }
        enum Either[L, R] { Left(L), Right(R) }
        let value = Maybe.Some(42)
        match value {
            case Maybe.Some(item) { print(item) }
            case Maybe.None { print(0) }
        }
        let side: Either[int, text] = Either.Left(7)
        match side {
            case Either.Left(item) { print(item) }
            case Either.Right(message) { print(message) }
        }
        """
        py_output = self.run_program(source)
        self.assertEqual(py_output, ["42", "7"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            program = root / "main.saga"
            program.write_text(source, encoding="utf-8")
            go_dir = Path(__file__).resolve().parents[1] / "implementations" / "go" / "cmd" / "saga-go"
            go_run = subprocess.run(
                ["go", "run", ".", "run", str(program)],
                cwd=go_dir, text=True, capture_output=True, timeout=90,
            )
            self.assertEqual(go_run.returncode, 0, go_run.stdout + go_run.stderr)
            self.assertEqual(go_run.stdout.strip().splitlines(), py_output)

            module = root / "maybe.saga"
            module.write_text(
                "module maybe\npublic enum Maybe[T] { None, Some(T) }\n",
                encoding="utf-8",
            )
            py_iface = build_module_interface(module, output=root / "python.smi.json")
            go_compile = subprocess.run(
                ["go", "run", ".", "module", "compile", str(module), str(root / "go.smi.json")],
                cwd=go_dir, text=True, capture_output=True, timeout=90,
            )
            self.assertEqual(go_compile.returncode, 0, go_compile.stdout + go_compile.stderr)
            go_iface = json.loads((root / "go.smi.json").read_text(encoding="utf-8"))
            self.assertEqual(py_iface["exports"], go_iface["exports"])
            self.assertEqual(py_iface["abi_sha256"], go_iface["abi_sha256"])


if __name__ == "__main__":
    unittest.main()
