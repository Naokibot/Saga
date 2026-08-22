from __future__ import annotations

import unittest

from saga.api import compile_source, run_source
from saga.errors import RuntimeLanguageError, TypeCheckError


class SagaLanguageTests(unittest.TestCase):
    def run_program(self, source: str, precision: int = 50) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append, precision=precision)
        return output

    def test_exact_decimal_arithmetic(self):
        self.assertEqual(self.run_program("print(0.1 + 0.2, 0.1 + 0.2 == 0.3)"), ["0.3 true"])

    def test_exact_rational_division(self):
        self.assertEqual(self.run_program("print(1 / 3 + 1 / 6)"), ["1/2"])

    def test_large_integer(self):
        source = "print(999999999999999999999999 ** 3)"
        self.assertEqual(
            self.run_program(source),
            ["999999999999999999999997000000000000000000000002999999999999999999999999"],
        )

    def test_power_precedence_matches_mathematics(self):
        self.assertEqual(self.run_program("print(-2 ** 2, (-2) ** 2, 2 ** 3 ** 2, 2 ** -2)"), ["-4 4 512 1/4"])


    def test_expression_function_inference(self):
        source = "fn add(a: int, b: int) = a + b\nprint(add(20, 22))"
        self.assertEqual(self.run_program(source), ["42"])

    def test_recursive_function_with_explicit_type(self):
        source = """
        fn factorial(n: int) -> int {
            if n <= 1 { return 1 }
            return n * factorial(n - 1)
        }
        print(factorial(10))
        """
        self.assertEqual(self.run_program(source), ["3628800"])

    def test_missing_return_path_rejected(self):
        source = "fn value(ok: bool) -> int { if ok { return 1 } }"
        with self.assertRaises(TypeCheckError):
            compile_source(source)

    def test_immutable_by_default(self):
        with self.assertRaises(TypeCheckError):
            compile_source("let x = 1\nx = 2")

    def test_mutable_variable(self):
        self.assertEqual(self.run_program("var x = 1\nx = x + 1\nprint(x)"), ["2"])

    def test_for_range_ascending(self):
        source = "var total = 0\nfor n in 1..5 { total = total + n }\nprint(total)"
        self.assertEqual(self.run_program(source), ["15"])

    def test_for_range_descending(self):
        self.assertEqual(self.run_program("for n in 3..1 { print(n) }"), ["3", "2", "1"])

    def test_break_and_continue(self):
        source = """
        for n in 1..6 {
            if n == 2 { continue }
            if n == 5 { break }
            print(n)
        }
        """
        self.assertEqual(self.run_program(source), ["1", "3", "4"])

    def test_empty_typed_list(self):
        self.assertEqual(self.run_program("let xs: list[int] = []\nprint(len(xs))"), ["0"])

    def test_mixed_numeric_list_promotes(self):
        self.assertEqual(self.run_program("let xs = [1, 2.5]\nprint(xs)"), ["[1, 2.5]"])

    def test_safe_index_error(self):
        with self.assertRaises(RuntimeLanguageError):
            self.run_program("let xs = [1, 2]\nprint(xs[2])")

    def test_safe_get_fallback(self):
        self.assertEqual(self.run_program("print(get([10, 20], 5, -1))"), ["-1"])

    def test_append_is_immutable(self):
        source = "let a = [1, 2]\nlet b = append(a, 3)\nprint(a, b)"
        self.assertEqual(self.run_program(source), ["[1, 2] [1, 2, 3]"])

    def test_sum_and_mean(self):
        self.assertEqual(self.run_program("print(sum([1, 2, 3]), mean([1, 2, 3]))"), ["6 2"])
        self.assertEqual(self.run_program("print(mean([1, 2]))"), ["3/2"])

    def test_precision_function(self):
        output = self.run_program("precision(80)\nprint(decimal(1 / 7))")
        self.assertEqual(len(output[0].split(".")[1]), 80)

    def test_sqrt_high_precision(self):
        output = self.run_program("precision(60)\nprint(sqrt(2))")
        self.assertTrue(output[0].startswith("1.41421356237309504880168872420969807856967187537694"))

    def test_round_floor_ceil(self):
        source = "print(round(1 / 3, 5), floor(-1.2), ceil(-1.2))"
        self.assertEqual(self.run_program(source), ["0.33333 -2 -1"])

    def test_assertion(self):
        with self.assertRaises(RuntimeLanguageError):
            self.run_program('assert(2 + 2 == 5, "math failed")')

    def test_boolean_words(self):
        self.assertEqual(self.run_program("print(true and not false, false or true)"), ["true true"])

    def test_single_quoted_string_and_hash_comment(self):
        self.assertEqual(self.run_program("# comment\nprint('Saga')"), ["Saga"])

    def test_no_implicit_text_conversion(self):
        with self.assertRaises(TypeCheckError):
            compile_source('print("x=" + 1)')
        self.assertEqual(self.run_program('print("x=", 1)'), ["x= 1"])

    def test_division_by_zero(self):
        with self.assertRaises(RuntimeLanguageError):
            self.run_program("print(10 / 0)")

    def test_range_requires_int(self):
        with self.assertRaises(TypeCheckError):
            compile_source("for n in 1.5..3 { print(n) }")

    def test_list_type_mismatch(self):
        with self.assertRaises(TypeCheckError):
            compile_source('let xs = [1, "two"]')

    def test_unit_function_may_omit_return_type(self):
        source = 'fn greet(name: text) { print("Hello", name) }\ngreet("Aki")'
        self.assertEqual(self.run_program(source), ["Hello Aki"])

    def test_inferred_function_can_use_previous_global(self):
        source = "let base = 10\nfn add_base(x: int) = x + base\nprint(add_base(5))"
        self.assertEqual(self.run_program(source), ["15"])

    def test_forward_inferred_function_dependency(self):
        source = "fn twice(x: int) = double(x)\nfn double(x: int) = x * 2\nprint(twice(4))"
        self.assertEqual(self.run_program(source), ["8"])


if __name__ == "__main__":
    unittest.main()
