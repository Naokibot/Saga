from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from saga.diagnostics import CATALOG, get_spec


class SagaDiagnostics090Tests(unittest.TestCase):
    def _run(self, source: str, *args: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.saga"
            path.write_text(source, encoding="utf-8")
            root = Path(__file__).resolve().parents[1]
            return subprocess.run(
                [sys.executable, str(root / "saga.py"), "check", str(path), *args],
                text=True, capture_output=True,
            )

    def test_immutable_binding_has_detailed_diagnostic(self):
        result = self._run("let score = 1\nscore = 2\n", "--language", "ja")
        self.assertEqual(result.returncode, 4)
        self.assertIn("error[SAGA-T101]", result.stderr)
        self.assertIn("修正案:", result.stderr)
        self.assertIn("理由:", result.stderr)

    def test_english_diagnostics_do_not_expose_japanese_detail(self):
        result = self._run("let score = 1\nscore = 2\n", "--language", "en")
        self.assertEqual(result.returncode, 4)
        self.assertIn("Cannot assign to an immutable binding", result.stderr)
        self.assertIn("`score` is immutable", result.stderr)
        self.assertIn("help:", result.stderr)
        self.assertNotIn("なので変更できません", result.stderr)

    def test_typo_gets_fix_candidate(self):
        result = self._run("let score = 1\nprint(socre)\n", "--language", "en")
        self.assertIn("SAGA-T102", result.stderr)
        self.assertIn("Did you mean `score`?", result.stderr)

    def test_json_schema_preserves_compatibility_category_and_detailed_id(self):
        result = self._run("if 1 { print(1) }\n", "--diagnostic-format", "json", "--language", "en")
        document = json.loads(result.stderr)
        self.assertEqual(document["schema"], 2)
        self.assertEqual(document["diagnostic"]["code"], "SAGA-T001")
        self.assertEqual(document["diagnostic"]["id"], "SAGA-T104")
        self.assertEqual(document["locale"], "en")
        self.assertIn("range", document["diagnostic"])

    def test_sarif_output_has_rule_and_range(self):
        result = self._run("if 1 { print(1) }\n", "--diagnostic-format", "sarif", "--language", "en")
        document = json.loads(result.stderr)
        self.assertEqual(document["version"], "2.1.0")
        item = document["runs"][0]["results"][0]
        self.assertEqual(item["ruleId"], "SAGA-T104")
        self.assertEqual(item["locations"][0]["physicalLocation"]["region"]["startLine"], 1)

    def test_catalog_has_bilingual_explanations(self):
        self.assertGreaterEqual(len(CATALOG), 19)
        for code, spec in CATALOG.items():
            self.assertEqual(code, spec.id)
            self.assertTrue(spec.title("ja"))
            self.assertTrue(spec.title("en"))
            self.assertTrue(spec.explanation("ja"))
            self.assertTrue(spec.explanation("en"))


    def test_malformed_utf8_has_lexical_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.saga"
            path.write_bytes(b"print(1)\n\xff\n")
            root = Path(__file__).resolve().parents[1]
            result = subprocess.run(
                [sys.executable, str(root / "saga.py"), "check", str(path), "--language", "en"],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("SAGA-L104", result.stderr)
            self.assertIn("Invalid UTF-8 source", result.stderr)

    def test_non_nfc_identifier_has_specific_diagnostic(self):
        result = self._run("let e\u0301 = 1\n", "--language", "en")
        self.assertEqual(result.returncode, 2)
        self.assertIn("SAGA-L105", result.stderr)
        self.assertIn("NFC", result.stderr)

    def test_bidi_control_has_specific_diagnostic(self):
        result = self._run("let ok = 1\n\u202e\n", "--language", "en")
        self.assertEqual(result.returncode, 2)
        self.assertIn("SAGA-L106", result.stderr)
        self.assertIn("Bidirectional", result.stderr)

    def test_unsupported_locale_falls_back_to_english(self):
        result = self._run("let score = 1\nscore = 2\n", "--language", "fr-FR")
        self.assertEqual(result.returncode, 4)
        self.assertIn("Cannot assign to an immutable binding", result.stderr)

    def test_explain_command(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "saga.py"), "explain", "SAGA-T101", "--language", "en"],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Cannot assign to an immutable binding", result.stdout)
        self.assertIn("Suggested fix:", result.stdout)


if __name__ == "__main__":
    unittest.main()

class SagaInternationalProject090Tests(unittest.TestCase):
    def test_unicode_project_name_is_portable_and_safe(self):
        from saga.project import load_project
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.saga").write_text("print(1)\n", encoding="utf-8")
            (root / "saga.toml").write_text(
                '[project]\nname="学習ツール-日本"\nversion="1.0.0"\nlanguage="0.9"\nentry="main.saga"\n',
                encoding="utf-8",
            )
            project = load_project(root / "saga.toml")
            self.assertEqual(project.name, "学習ツール-日本")

    def test_project_name_has_no_saga_fixed_length_ceiling(self):
        from saga.project import load_project
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.saga").write_text("print(1)\n", encoding="utf-8")
            name = "学" * 200
            (root / "saga.toml").write_text(
                f'[project]\nname="{name}"\nversion="1.0.0"\nlanguage="0.9"\nentry="main.saga"\n',
                encoding="utf-8",
            )
            project = load_project(root / "saga.toml")
            self.assertEqual(project.name, name)

    def test_project_name_still_rejects_path_escape(self):
        from saga.project import load_project
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.saga").write_text("print(1)\n", encoding="utf-8")
            (root / "saga.toml").write_text(
                '[project]\nname="../危険"\nversion="1.0.0"\nlanguage="0.9"\nentry="main.saga"\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_project(root / "saga.toml")
