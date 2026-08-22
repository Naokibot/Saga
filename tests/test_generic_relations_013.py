from __future__ import annotations
import unittest
from saga.api import compile_source
from saga.errors import TypeCheckError


class GenericRelationTests(unittest.TestCase):
    def test_generic_interface_binding(self):
        source = '''
interface Repository[T] { fn save(value: T) -> T }
class MemoryRepository[T](let seed: T) implements Repository[T] {
    override fn save(value: T) -> T = value
}
let repo: Repository[int] = MemoryRepository(0)
print(repo.save(42))
'''
        unit = compile_source(source)
        self.assertIsNotNone(unit)

    def test_generic_base_binding(self):
        source = '''
class Box[T](let value: T) {}
class IntBox() extends Box[int] {}
let box = IntBox(9)
print(box.value)
'''
        unit = compile_source(source)
        self.assertIsNotNone(unit)

    def test_generic_interface_is_invariant(self):
        source = '''
interface R[T] { fn save(v: T) -> T }
class M[T](let seed: T) implements R[T] { override fn save(v: T) -> T = v }
let r: R[text] = M(0)
'''
        with self.assertRaises(TypeCheckError):
            compile_source(source)

    def test_legacy_project_language_versions_remain_supported(self):
        from saga.project import load_project
        import tempfile
        from pathlib import Path
        for language in ("0.8", "0.9", "1.0"):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / "main.saga").write_text('print(1)\n', encoding='utf-8')
                (root / "saga.toml").write_text(
                    f'[project]\nname = "compat-test"\nversion = "1.0.0"\nlanguage = "{language}"\nentry = "main.saga"\ntest_dir = "tests"\n',
                    encoding='utf-8',
                )
                (root / "tests").mkdir()
                self.assertEqual(load_project(root / "saga.toml").language, language)


if __name__ == '__main__':
    unittest.main()
