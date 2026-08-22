from __future__ import annotations

import unittest

from saga.api import compile_source
from saga.migration import migrate_source


class Migration029Tests(unittest.TestCase):
    def test_safe_collection_rewrites_compile(self):
        source = '''
        fn keep(x: int) -> bool = x > 1
        fn twice(x: int) -> int = x * 2
        values = [1, 2, 3]
        a = filter(keep, values)
        b = transform(twice, values)
        c = sort(values)
        d = unique(values)
        '''
        result = migrate_source(source)
        self.assertEqual(len(result.changes), 4)
        compile_source(result.source)
        self.assertIn('values.filter(keep)', result.source)
        self.assertIn('values.map(twice)', result.source)

    def test_complex_expression_is_left_untouched(self):
        source = 'values = transform(make_mapper(2), load_values())\n'
        result = migrate_source(source)
        self.assertFalse(result.changes)
        self.assertEqual(result.source, source)


class NaturalLint029Tests(unittest.TestCase):
    def test_legacy_collection_form_gets_migration_hint(self):
        from saga.linter import lint_program
        program = compile_source('fn keep(x: int) -> bool = true\nvalues = [1,2]\nprint(filter(keep, values))')
        diagnostics = lint_program(program)
        self.assertTrue(any(item.code == 'S106' and 'saga migrate' in item.message for item in diagnostics))


if __name__ == '__main__':
    unittest.main()
