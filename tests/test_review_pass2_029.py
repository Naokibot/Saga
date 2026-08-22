from __future__ import annotations

import unittest

from saga.api import SagaSession, compile_source, run_source
from saga.errors import ParseError, TypeCheckError
from saga.interpreter import SagaThrown
from saga.migration import migrate_source


class ReviewPass2Natural029Tests(unittest.TestCase):
    def run_program(self, source: str) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append)
        return output

    def test_migration_never_rewrites_strings_or_comments(self):
        source = '''
print("filter(pred, values)")
// transform(fn, values)
# sort(values)
actual = filter(pred, values) // filter(pred, values)
'''
        result = migrate_source(source)
        self.assertIn('print("filter(pred, values)")', result.source)
        self.assertIn('// transform(fn, values)', result.source)
        self.assertIn('# sort(values)', result.source)
        self.assertIn('actual = values.filter(pred) // filter(pred, values)', result.source)
        self.assertEqual(len(result.changes), 1)

    def test_pipeline_supports_natural_collection_stage_names(self):
        source = '''
values = [3, 1, 2, 2]
result = values
    |> map { it * 2 }
    |> distinct
    |> sorted
    |> take(2)
print(result)
'''
        self.assertEqual(self.run_program(source), ['[2, 4]'])

    def test_pipeline_preserves_legacy_reduce_and_find_argument_order(self):
        source = '''
fn add(acc: int, n: int) -> int { return acc + n }
fn greaterThanOne(n: int) -> bool { return n > 1 }
values = [1, 2, 3]
print(values |> reduce(add, 0))
print(values |> find(greaterThanOne, 99))
'''
        self.assertEqual(self.run_program(source), ['6', '2'])

    def test_pipeline_natural_fold_and_none_use_extension_semantics(self):
        source = '''
values = [1, 2, 3]
print(values |> fold(0) { acc, n -> acc + n })
print(values |> reduce(0) { acc, n -> acc + n })
print(values |> find { it > 1 })
print(values |> none { it > 3 })
'''
        self.assertEqual(self.run_program(source), ['6', '6', 'some(2)', 'true'])

    def test_duplicate_closure_parameters_are_rejected(self):
        with self.assertRaises(ParseError):
            compile_source('let f: fn[int,int,int] = { value, value -> value }')

    def test_control_header_pipeline_closure_requires_parentheses(self):
        source = 'values = [1, 2]\nif (values |> any { it > 0 }) { print("yes") }'
        self.assertEqual(self.run_program(source), ['yes'])
        with self.assertRaises((ParseError, TypeCheckError)):
            compile_source('values = [1, 2]\nif values |> any { it > 0 } { print("yes") }')

    def test_return_analysis_understands_nested_blocks_and_finally(self):
        source = '''
fn fromNestedBlock() -> int { { return 2 } }
fn fromTryFinally() -> int {
    try { return 3 } finally { print("cleanup") }
}
fn fromFinally() -> int {
    try { print("body") } finally { return 4 }
}
print(fromNestedBlock())
print(fromTryFinally())
print(fromFinally())
'''
        self.assertEqual(self.run_program(source), ['2', 'cleanup', '3', 'body', '4'])

    def test_repl_does_not_redeclare_existing_class_members(self):
        output: list[str] = []
        with SagaSession(output=output.append) as session:
            session.execute('class Item(let value: int) { fn doubled() -> int { return self.value * 2 } }')
            session.execute('let item = Item(4)\nprint(item.doubled())')
            session.execute('print("next")')
        self.assertEqual(output, ['8', 'next'])

    def test_repl_inheritance_resolution_is_idempotent(self):
        output: list[str] = []
        with SagaSession(output=output.append) as session:
            session.execute('class Base(let x: int) { fn get() -> int { return self.x } }')
            session.execute('class Child(let y: int) extends Base { fn sum() -> int { return self.x + self.y } }')
            session.execute('let child = Child(2, 3)\nprint(child.sum())')
            session.execute('print("again")')
        self.assertEqual(output, ['5', 'again'])

    def test_failed_repl_submission_rolls_back_language_state(self):
        output: list[str] = []
        with SagaSession(output=output.append) as session:
            with self.assertRaises(SagaThrown):
                session.execute('x = 1\nfn temporary() -> int { return 7 }\nthrow "boom"')
            with self.assertRaises(TypeCheckError):
                session.execute('print(x)')
            with self.assertRaises(TypeCheckError):
                session.execute('print(temporary())')
            session.execute('x = 2\nprint(x)')
        self.assertEqual(output, ['2'])


if __name__ == '__main__':
    unittest.main()
