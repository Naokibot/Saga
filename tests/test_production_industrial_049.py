from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from saga import run_source
from saga.api import compile_source
from saga.package import build_lock
from saga.production import production_check
from saga.stdlib.machine_precision import ControlGuard
from saga.workspace import load_workspace


class ProductionIndustrial049Tests(unittest.TestCase):
    def test_control_tick_accepts_explicit_rate_budget_contract(self):
        compile_source('''
@control_tick(20000, 35)
fn current_tick(error: decimal) -> decimal {
    return error * 0.5
}
''')

    def test_control_tick_rejects_budget_larger_than_period(self):
        with self.assertRaises(Exception) as ctx:
            compile_source('''
@control_tick(20000, 60)
fn current_tick(error: decimal) -> decimal { return error }
''')
        self.assertIn("SAGA-C483", str(ctx.exception))

    def test_control_guard_observes_stale_jitter_and_budget_without_hidden_policy(self):
        guard = ControlGuard(20_000, 35, 100, 5)
        self.assertTrue(guard.begin(999_950_000, 1_000_000_000))
        self.assertTrue(guard.end(1_000_020_000))
        self.assertTrue(guard.begin(1_000_000_000, 1_000_050_000))
        self.assertFalse(guard.end(1_000_090_000))  # 40 us > 35 us
        report = json.loads(guard.stats_json())
        self.assertEqual(report["samples"], 2)
        self.assertEqual(report["budget_misses"], 1)
        self.assertEqual(report["stale_inputs"], 0)
        self.assertEqual(report["jitter_violations"], 0)
        self.assertFalse(guard.ok())

    def test_saga_surface_control_guard_is_deterministic(self):
        out: list[str] = []
        run_source('''
use machine
let guard = machine.control_guard(20000, 35, 100, 5)
print(machine.control_guard_begin(guard, 999950000, 1000000000))
print(machine.control_guard_end(guard, 1000020000))
print(machine.control_guard_begin(guard, 1000000000, 1000050000))
print(machine.control_guard_end(guard, 1000090000))
print(machine.control_guard_ok(guard))
print(machine.control_guard_stats_json(guard))
''', output=out.append)
        self.assertEqual(out[:5], ["true", "true", "true", "false", "false"])
        self.assertEqual(json.loads(out[5])["budget_misses"], 1)

    def test_workspace_rejects_duplicate_project_names(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ("a", "b"):
                d = root / name; d.mkdir()
                (d / "saga.toml").write_text('[project]\nname="same"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\n', encoding="utf-8")
                (d / "main.saga").write_text('print(1)\n', encoding="utf-8")
            (root / "saga-workspace.toml").write_text('[workspace]\nmembers=["a","b"]\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_workspace(root)

    def test_production_gate_checks_workspace_lock_lint_and_reproducible_package(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, value in (("core", 1), ("service", 2)):
                d = root / name; d.mkdir()
                (d / "saga.toml").write_text(
                    f'[project]\nname="{name}"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\n',
                    encoding="utf-8",
                )
                (d / "main.saga").write_text(f'print({value})\n', encoding="utf-8")
                build_lock(d)
            (root / "saga-workspace.toml").write_text('[workspace]\nmembers=["core","service"]\n', encoding="utf-8")
            report = production_check(root)
            self.assertTrue(report["ready"], json.dumps(report, indent=2))
            self.assertEqual(len(report["projects"]), 2)
            for project in report["projects"]:
                self.assertTrue(project["ready"])
                self.assertEqual([g["status"] for g in project["gates"]], ["PASS", "PASS", "PASS"])

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_python_and_go_share_control_guard_and_control_tick_contract(self):
        good = '''
use machine
@control_tick(20000, 35)
fn tick(error: decimal) -> decimal { return error * 0.5 }
let guard = machine.control_guard(20000, 35, 100, 5)
print(machine.control_guard_begin(guard, 999950000, 1000000000))
print(machine.control_guard_end(guard, 1000020000))
print(machine.control_guard_stats_json(guard))
'''
        py: list[str] = []
        run_source(good, output=py.append)
        go_dir = Path(__file__).resolve().parents[1] / "implementations" / "go" / "cmd" / "saga-go"
        with tempfile.TemporaryDirectory() as td:
            program = Path(td) / "good.saga"; program.write_text(good, encoding="utf-8")
            proc = subprocess.run(["go", "run", ".", "run", str(program)], cwd=go_dir, text=True, capture_output=True, timeout=90)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            gout = proc.stdout.strip().splitlines()
            self.assertEqual(gout[:2], py[:2])
            self.assertEqual(json.loads(gout[2])["budget_misses"], 0)

            bad = Path(td) / "bad.saga"
            bad.write_text('@control_tick(20000, 60)\nfn tick(x: int) -> int { return x }\n', encoding="utf-8")
            proc = subprocess.run(["go", "run", ".", "check", str(bad)], cwd=go_dir, text=True, capture_output=True, timeout=90)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SAGA-C483", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
