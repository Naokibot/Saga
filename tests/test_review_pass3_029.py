from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from saga.api import SagaSession, compile_file, compile_source, run_source
from saga.errors import ParseLimitError, RuntimeLanguageError, TypeCheckError
from saga.interpreter import SagaThrown


class ReviewPass3Natural029Tests(unittest.TestCase):
    def run_program(self, source: str) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append)
        return output

    def test_function_assignment_checks_return_contract(self):
        source = '''
fn give(value: int) -> int { return value }
let wrong: fn[int,text] = give
'''
        with self.assertRaises(TypeCheckError):
            compile_source(source)

    def test_function_assignment_uses_safe_parameter_variance(self):
        safe = '''
fn acceptsDecimal(value: decimal) -> int { return 1 }
let f: fn[int,int] = acceptsDecimal
print(f(2))
'''
        self.assertEqual(self.run_program(safe), ['1'])
        unsafe = '''
fn acceptsInt(value: int) -> int { return value }
let f: fn[decimal,int] = acceptsInt
'''
        with self.assertRaises(TypeCheckError):
            compile_source(unsafe)

    def test_generic_arguments_are_invariant(self):
        with self.assertRaises(TypeCheckError):
            compile_source('let a: list[int] = [1]\nlet b: list[decimal] = a')
        with self.assertRaises(TypeCheckError):
            compile_source('let a: option[int] = some(1)\nlet b: option[decimal] = a')

    def test_contextual_option_and_result_construction_preserves_invariance(self):
        source = '''
let maybe: option[decimal] = some(1)
let success: result[decimal,text] = ok(2)
let failure: result[int,text] = err("no")
print(unwrap(maybe), unwrap_ok(success), unwrap_err(failure))
'''
        self.assertEqual(self.run_program(source), ['1 2 no'])

    def test_generic_type_variables_remain_visible_in_local_declarations(self):
        source = '''
fn outer[T](value: T) -> T {
    let copy: T = value
    fn inner(next: T) -> T { return next }
    return inner(copy)
}
print(outer(4))
'''
        self.assertEqual(self.run_program(source), ['4'])

    def test_unknown_nominal_types_are_rejected(self):
        with self.assertRaises(TypeCheckError):
            compile_source('fn broken(value: MissingType) -> MissingType { return value }')
        with self.assertRaises(TypeCheckError):
            compile_source('fn dynamic() -> any { return 1 }\nlet value: MissingType = dynamic()')

    def test_local_function_hoisting_is_consistent_in_for_and_catch(self):
        source = '''
for n in 1..1 {
    print(local())
    fn local() -> int { return n }
}
try { throw "x" } catch error {
    print(recover())
    fn recover() -> int { return 7 }
}
'''
        self.assertEqual(self.run_program(source), ['1', '7'])

    def test_dynamic_any_is_checked_at_typed_variable_boundaries(self):
        initial = '''
fn dynamic() -> any { return "oops" }
let value: int = dynamic()
'''
        with self.assertRaises(RuntimeLanguageError) as raised:
            run_source(initial)
        self.assertIn('SAGA-T103', str(raised.exception))

        assignment = '''
fn dynamic() -> any { return "oops" }
var value: int = 1
value = dynamic()
'''
        with self.assertRaises(RuntimeLanguageError) as raised:
            run_source(assignment)
        self.assertIn('SAGA-T103', str(raised.exception))

    def test_dynamic_any_is_checked_at_field_boundary(self):
        source = '''
class Box(var value: int) {}
fn dynamic() -> any { return "oops" }
var box = Box(1)
box.value = dynamic()
'''
        with self.assertRaises(RuntimeLanguageError) as raised:
            run_source(source)
        self.assertIn('SAGA-T103', str(raised.exception))

    def test_failed_repl_submission_rolls_back_object_mutation(self):
        output: list[str] = []
        with SagaSession(output=output.append) as session:
            session.execute('class Box(var value: int) {}\nvar box = Box(1)')
            with self.assertRaises(SagaThrown):
                session.execute('box.value = 9\nthrow "boom"')
            session.execute('print(box.value)')
        self.assertEqual(output, ['1'])

    def test_failed_repl_submission_rolls_back_captured_closure_state(self):
        output: list[str] = []
        with SagaSession(output=output.append) as session:
            session.execute('fn make() -> fn[int] { var n = 0 return { n = n + 1 n } }\nvar counter = make()')
            with self.assertRaises(SagaThrown):
                session.execute('counter()\nthrow "boom"')
            session.execute('print(counter())')
        self.assertEqual(output, ['1'])

    def test_task_spawn_rejects_local_function_before_scheduling(self):
        source = '''
use task
fn outer() -> int {
    fn local(value: int) -> int { return value + 1 }
    let future = task.spawn(local, 4)
    return task.await(future)
}
print(outer())
'''
        with self.assertRaises(RuntimeLanguageError) as raised:
            run_source(source)
        self.assertIn('トップレベル関数', str(raised.exception))
        self.assertNotIn("非同期処理が失敗しました", str(raised.exception))

    def test_deep_source_unit_chain_reports_saga_resource_diagnostic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            count = 1100
            for index in range(count):
                path = root / f'unit{index}.saga'
                if index + 1 < count:
                    path.write_text(f'use "unit{index + 1}.saga"\n', encoding='utf-8')
                else:
                    path.write_text('print("ok")\n', encoding='utf-8')
            with self.assertRaises(ParseLimitError):
                compile_file(str(root / 'unit0.saga'))

    def test_dynamic_any_function_contract_checks_signature(self):
        bad = r'''
fn give(value: int) -> int { return value }
fn dynamic() -> any { return give }
let callback: fn[int,text] = dynamic()
'''
        with self.assertRaises(RuntimeLanguageError) as raised:
            run_source(bad)
        self.assertIn('SAGA-T103', str(raised.exception))

        generic = r'''
fn identity[T](value: T) -> T { return value }
fn dynamic() -> any { return identity }
let callback: fn[int,int] = dynamic()
print(callback(3))
'''
        self.assertEqual(self.run_program(generic), ['3'])

    def test_dynamic_any_inside_generic_function_uses_concrete_runtime_contract(self):
        source = r'''
fn dynamic() -> any { return "oops" }
fn pick[T](fallback: T) -> T {
    let value: T = dynamic()
    return value
}
print(pick(1) + 1)
'''
        with self.assertRaises(RuntimeLanguageError) as raised:
            run_source(source)
        self.assertIn('SAGA-T103', str(raised.exception))
        self.assertNotIn('TypeError', str(raised.exception))

    def test_native_any_container_contract_is_wildcard_without_weakening_user_generics(self):
        source = r'''
use task
fn square(value: int) -> int { return value * value }
let values = [1, 2, 3]
let futureValues = task.cpu_map(square, values, 0)
'''
        compile_source(source)
        with self.assertRaises(TypeCheckError):
            compile_source('let ints: list[int] = [1]\nlet decimals: list[decimal] = ints')


if __name__ == '__main__':
    unittest.main()
