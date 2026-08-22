from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from saga.api import SagaSession, compile_source, run_source
from saga.errors import LexError, TypeCheckError
from saga.native import NativeFailure
from saga.formatter import format_source
from saga.interpreter import Interpreter
from saga.linter import lint_program
from saga.project import load_project
from saga.stdlib import MODULES
from saga.typesys import INT


class SagaStandardLanguageTests(unittest.TestCase):
    def run_program(self, source: str) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append)
        return output

    def test_class_and_interface_subtyping(self):
        source = '''
        interface Named { fn name() -> text }
        class Person(let value: text) implements Named {
            override fn name() -> text = self.value
        }
        class Student(let student_name: text) extends Person {
            override fn name() -> text = "Student " + self.student_name
        }
        fn label(item: Named) -> text = item.name()
        let person: Person = Student("base", "Aki")
        let named: Named = person
        print(label(named))
        '''
        self.assertEqual(self.run_program(source), ["Student Aki"])

    def test_override_is_explicit(self):
        missing = '''
        class Base() { fn value() -> int = 1 }
        class Child() extends Base { fn value() -> int = 2 }
        '''
        with self.assertRaises(TypeCheckError):
            compile_source(missing)
        with self.assertRaises(TypeCheckError):
            compile_source('class A() { override fn value() -> int = 1 }')

    def test_option_values(self):
        source = '''
        let found: option[int] = some(42)
        let missing: option[int] = none()
        print(is_some(found), unwrap(found))
        print(is_none(missing), unwrap_or(missing, 7))
        '''
        self.assertEqual(self.run_program(source), ["true 42", "true 7"])

    def test_result_values_with_explicit_type_annotation(self):
        source = """
        let value: result[int,text] = ok(7)
        print(is_ok(value), unwrap_ok(value))
        """
        self.assertEqual(self.run_program(source), ["true 7"])

    def test_json_is_exact_and_null_is_option(self):
        source = r'''
        use json
        let data = json.decode("{\"number\":0.1,\"missing\":null}")
        let number = map_get(data, "number", 0.0)
        let missing = map_get(data, "missing", none())
        print(number == 0.1, is_none(missing))
        print(json.encode(map_of("number", 0.1, "missing", none())))
        '''
        self.assertEqual(
            self.run_program(source),
            ['true true', '{"number":0.1,"missing":null}'],
        )

    def test_json_rejects_duplicate_keys(self):
        source = r'''use json
        json.decode("{\"x\":1,\"x\":2}")'''
        from saga.errors import RuntimeLanguageError
        with self.assertRaises(RuntimeLanguageError):
            self.run_program(source)

    def test_malformed_numeric_separators_are_rejected(self):
        for source in ("let x = 1__2", "let x = 12_", "let x = 1_.2", "let x = 1._2"):
            with self.subTest(source=source), self.assertRaises(LexError):
                compile_source(source)

    def test_unhashable_collection_keys_are_rejected(self):
        with self.assertRaises(TypeCheckError):
            compile_source("let value = map_of([1], 2)")
        with self.assertRaises(TypeCheckError):
            compile_source("let value = set_of([1])")

    def test_unique_supports_nested_lists(self):
        self.assertEqual(self.run_program("print(unique([[1], [1], [2]]))"), ["[[1], [2]]"])

    def test_annotation_arguments_are_compile_time_literals(self):
        with self.assertRaises(TypeCheckError):
            compile_source("@example(1 + 2)\nfn value() -> int = 3")

    def test_native_contract_rejects_wrong_host_value(self):
        interpreter = Interpreter()
        try:
            with self.assertRaises(NativeFailure):
                interpreter.validate_native_value(INT, "not-an-int", "result")
        finally:
            interpreter.close()

    def test_repl_session_keeps_state_and_rolls_back_failed_check(self):
        output: list[str] = []
        with SagaSession(output=output.append) as session:
            session.execute("let x = 40")
            with self.assertRaises(TypeCheckError):
                session.execute('x = "bad"')
            session.execute("print(x + 2)")
        self.assertEqual(output, ["42"])

    def test_formatter_is_idempotent_and_preserves_strings(self):
        source = 'fn greet(name: text)->text { return "a  b" }\nprint(greet("x"))\n'
        once = format_source(source)
        twice = format_source(once)
        self.assertEqual(once, twice)
        self.assertIn('"a  b"', once)
        compile_source(once)

    def test_standard_linter_reports_dynamic_any(self):
        program = compile_source("fn echo(value: any) -> any = value")
        diagnostics = lint_program(program, standard=True)
        self.assertTrue(any(item.severity == "error" for item in diagnostics))

    def test_private_fields_are_not_serialized(self):
        source = '''
        use json
        class Account(private let secret: text, let name: text) {}
        print(json.encode(Account("token", "Aki")))
        '''
        self.assertEqual(self.run_program(source), ['{"name":"Aki"}'])

    def test_higher_order_function_contracts(self):
        with self.assertRaises(TypeCheckError):
            compile_source('fn bad(x: int) -> int = x\nfilter(bad, [1, 2])')
        with self.assertRaises(TypeCheckError):
            compile_source('fn wrong(x: text) -> bool = true\nany(wrong, [1, 2])')
        with self.assertRaises(TypeCheckError):
            compile_source('fn combine(a: text, b: int) -> text = a\nreduce(combine, [1, 2], 0)')

    def test_map_and_set_lookup_types_are_checked(self):
        with self.assertRaises(TypeCheckError):
            compile_source('map_contains(map_of("x", 1), 2)')
        with self.assertRaises(TypeCheckError):
            compile_source('set_contains(set_of(1), "1")')


    def test_project_manifest_is_semver_and_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.saga").write_text("print(42)", encoding="utf-8")
            manifest = root / "saga.toml"
            manifest.write_text('[project]\nname="demo"\nversion="1.2.3"\nentry="main.saga"\ntest_dir="tests"\n', encoding="utf-8")
            project = load_project(manifest)
            self.assertEqual(project.version, "1.2.3")
            manifest.write_text('[project]\nname="demo"\nversion="latest"\nentry="main.saga"\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_project(manifest)
            manifest.write_text('[project]\nname="demo"\nversion="1.2.3"\nentry="main.saga"\ntest_dir="../outside"\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_project(manifest)



if __name__ == "__main__":
    unittest.main()
