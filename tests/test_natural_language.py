from __future__ import annotations

import unittest

from saga.api import compile_source, run_source
from saga.errors import TypeCheckError


class NaturalSagaTests(unittest.TestCase):
    def run_program(self, source: str) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append)
        return output

    def test_first_assignment_introduces_local_name(self):
        self.assertEqual(self.run_program('name = "Saga"\nprint(name)'), ['Saga'])

    def test_explicit_let_remains_immutable(self):
        with self.assertRaises(TypeCheckError):
            compile_source('let name = "Saga"\nname = "Other"')

    def test_natural_binding_is_also_immutable(self):
        with self.assertRaises(TypeCheckError):
            compile_source('name = "Saga"\nname = "Other"')

    def test_implicit_it_collection_pipeline(self):
        source = '''
        numbers = [3, 1, 2, 2]
        result = numbers
            .filter { it > 1 }
            .map { it * 10 }
            .distinct()
            .sorted()
        print(result)
        '''
        self.assertEqual(self.run_program(source), ['[20, 30]'])

    def test_explicit_two_parameter_closure(self):
        source = 'numbers = [1, 2, 3]\ntotal = numbers.fold(0) { acc, n -> acc + n }\nprint(total)'
        self.assertEqual(self.run_program(source), ['6'])

    def test_trailing_block_repeat(self):
        self.assertEqual(self.run_program('repeat(3) { print("Hello") }'), ['Hello', 'Hello', 'Hello'])

    def test_first_class_zero_argument_closure(self):
        source = 'greet = { print("Hello") }\ngreet()'
        self.assertEqual(self.run_program(source), ['Hello'])

    def test_first_class_explicit_parameter_closure(self):
        source = 'let double: fn[int, int] = { value -> value * 2 }\nprint(double(4))'
        self.assertEqual(self.run_program(source), ['8'])

    def test_return_exits_closure_not_enclosing_function(self):
        source = '''
        values = [1, 2, 3]
        mapped = values.map {
            if it > 1 { return it * 10 }
            return it
        }
        print(mapped)
        '''
        self.assertEqual(self.run_program(source), ['[1, 20, 30]'])

    def test_closure_return_type_is_independent_of_enclosing_function(self):
        source = '''
        fn outer() -> int {
            values = [1]
            mapped = values.map { return text(it) }
            return len(mapped)
        }
        print(outer())
        '''
        self.assertEqual(self.run_program(source), ['1'])

    def test_closure_cannot_break_or_continue_enclosing_loop(self):
        for keyword in ('break', 'continue'):
            with self.subTest(keyword=keyword):
                with self.assertRaises(TypeCheckError):
                    compile_source(f'for n in [1] {{ let f: fn[unit] = {{ {keyword} }} f() }}')

    def test_nested_function_cannot_break_enclosing_loop(self):
        with self.assertRaises(TypeCheckError):
            compile_source('for n in [1] { fn stop() { break } stop() }')

    def test_closure_return_paths_must_agree(self):
        with self.assertRaises(TypeCheckError):
            compile_source('values = [1]\nvalues.map { if it > 0 { return 1 } print("no value") }')

    def test_library_defined_dsl_uses_bare_arguments_and_trailing_block(self):
        source = '''
        fn panel(title: text, body: fn[unit]) {
            print(title)
            body()
        }
        panel "Todo" { print("inside") }
        '''
        self.assertEqual(self.run_program(source), ['Todo', 'inside'])

    def test_pipe_is_sugar_over_existing_collection_functions(self):
        source = '''
        numbers = [1, 2, 3]
        result = numbers |> filter { it > 1 } |> transform { it * 2 }
        print(result)
        '''
        self.assertEqual(self.run_program(source), ['[4, 6]'])

    def test_control_flow_brace_not_misread_as_closure(self):
        source = 'active = true\nif active { print("yes") }\nfor n in [1, 2] { print(n) }'
        self.assertEqual(self.run_program(source), ['yes', '1', '2'])

    def test_control_flow_call_brace_not_misread_as_closure(self):
        source = '''
        fn ready() -> bool { return true }
        if ready() { print("if") }
        var count = 0
        while count < 1 { print("while") count = count + 1 }
        fn values() -> list[int] { return [1, 2] }
        for n in values() { print(n) }
        '''
        self.assertEqual(self.run_program(source), ['if', 'while', '1', '2'])

    def test_parentheses_disambiguate_trailing_closure_in_control_header(self):
        source = 'values = [1, 2]\nif (values.any { it > 1 }) { print("yes") }'
        self.assertEqual(self.run_program(source), ['yes'])

    def test_contextual_closure_type_error_teaches_at_compile_time(self):
        with self.assertRaises(TypeCheckError):
            compile_source('[1, 2, 3].filter { it + 1 }')

    def test_group_by_and_sorted_by(self):
        source = '''
        values = [1, 2, 3, 4]
        descending = values.sortedBy { -it }
        groups = values.groupBy { it % 2 }
        print(descending)
        print(groups)
        '''
        out = self.run_program(source)
        self.assertEqual(out[0], '[4, 3, 2, 1]')
        self.assertIn('1: [1, 3]', out[1])
        self.assertIn('0: [2, 4]', out[1])

    def test_flat_map_and_window(self):
        source = '''
        values = [1, 2, 3]
        doubled = values.flatMap { [it, it] }
        windows = values.window(2)
        print(doubled)
        print(windows)
        '''
        self.assertEqual(self.run_program(source), ['[1, 1, 2, 2, 3, 3]', '[[1, 2], [2, 3]]'])


if __name__ == '__main__':
    unittest.main()
