from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from saga.api import compile_source
from saga.package import build_lock
from saga.production import _source_digest, production_check
from saga.project import find_project


class ControlGA050Tests(unittest.TestCase):
    def test_control_tick_rejects_hidden_unverified_helper(self):
        with self.assertRaises(Exception) as ctx:
            compile_source('''
@control_tick(1000, 500)
fn tick(x: int) -> int { return helper(x) }
fn helper(x: int) -> int { return x + 1 }
''')
        self.assertIn("SAGA-C490", str(ctx.exception))

    def test_control_safe_helper_is_transitively_checked(self):
        compile_source('''
@control_tick(1000, 500)
fn tick(x: int) -> int { return helper(x) }
@control_safe
fn helper(x: int) -> int { return x + 1 }
''')
        with self.assertRaises(Exception) as ctx:
            compile_source('''
use machine
@control_tick(1000, 500)
fn tick(x: int) -> int { return helper(x) }
@control_safe
fn helper(x: int) -> int { let now = machine.monotonic_ns(); return x }
''')
        self.assertTrue("SAGA-C479" in str(ctx.exception) or "SAGA-C492" in str(ctx.exception))

    def test_control_call_graph_rejects_recursion(self):
        with self.assertRaises(Exception) as ctx:
            compile_source('''
@control_tick(1000, 500)
fn tick(x: int) -> int { return helper(x) }
@control_safe
fn helper(x: int) -> int { return tick(x) }
''')
        self.assertIn("SAGA-C485", str(ctx.exception))

    def test_control_rejects_shared_mutation_and_excessive_static_loop(self):
        with self.assertRaises(Exception) as ctx:
            compile_source('''
var global = 0
@control_tick(1000, 500)
fn tick(x: int) -> int { global = x; return global }
''')
        self.assertIn("SAGA-C487", str(ctx.exception))
        with self.assertRaises(Exception) as ctx:
            compile_source('''
@control_tick(1000, 500)
fn tick(x: int) -> int {
    var y = x
    for i in 0..5000 { y = y + 1 }
    return y
}
''')
        self.assertIn("SAGA-C486", str(ctx.exception))

    def _project(self, root: Path, *, mismatched=False) -> None:
        (root / "saga.toml").write_text('[project]\nname="motor"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\n', encoding="utf-8")
        (root / "main.saga").write_text('@control_tick(1000,500)\nfn tick(x:int)->int { return helper(x) }\n@control_safe\nfn helper(x:int)->int { return x+1 }\n', encoding="utf-8")
        build_lock(root)
        project = find_project(root); assert project is not None
        digest = "0" * 64 if mismatched else _source_digest(project)
        ev = root / "evidence"; ev.mkdir()
        for name, kind in (("hazard.json", "hazard-analysis"), ("wcet.json", "wcet"), ("hil.json", "hil")):
            (ev / name).write_text(json.dumps({"schema":1,"kind":kind,"pass":True,"project_source_sha256":digest,"saga_release":"0.50.0"}), encoding="utf-8")
        (root / "machine-safety.toml").write_text('''[safety]
profile="machine-production-ga-1"
external_emergency_stop=true
sto_or_interlock=true
hardware_watchdog=true
target="rtos"
hazard_analysis="evidence/hazard.json"
wcet_evidence="evidence/wcet.json"
hil_evidence="evidence/hil.json"
''', encoding="utf-8")

    def test_machine_production_gate_is_fail_closed_and_source_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "saga.toml").write_text('[project]\nname="motor"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\n', encoding="utf-8")
            (root / "main.saga").write_text('@control_tick(1000,500)\nfn tick(x:int)->int{return x}\n', encoding="utf-8")
            build_lock(root)
            self.assertFalse(production_check(root, machine=True)["ready"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self._project(root)
            report = production_check(root, machine=True)
            self.assertTrue(report["ready"], json.dumps(report, indent=2))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self._project(root, mismatched=True)
            self.assertFalse(production_check(root, machine=True)["ready"])


    def test_rejected_http_redirect_closes_response_resource(self):
        from saga.native import NativeFailure
        from saga.stdlib.modules import _CapabilityRedirectHandler

        class DenyCapabilities:
            def require_net(self, host, port):
                raise NativeFailure(f"denied {host}:{port}")

        class Response:
            closed = False
            def close(self):
                self.closed = True

        response = Response()
        handler = _CapabilityRedirectHandler(DenyCapabilities())
        with self.assertRaises(NativeFailure):
            handler.redirect_request(None, response, 302, "Found", {}, "https://example.com/next")
        self.assertTrue(response.closed)

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_python_go_control_call_graph_parity(self):
        good = '@control_tick(1000,500)\nfn tick(x:int)->int{return helper(x)}\n@control_safe\nfn helper(x:int)->int{return x+1}\n'
        bad = '@control_tick(1000,500)\nfn tick(x:int)->int{return helper(x)}\nfn helper(x:int)->int{return x+1}\n'
        compile_source(good)
        go_dir = Path(__file__).resolve().parents[1] / "implementations" / "go"
        with tempfile.TemporaryDirectory() as td:
            gp = Path(td) / "good.saga"; gp.write_text(good, encoding="utf-8")
            bp = Path(td) / "bad.saga"; bp.write_text(bad, encoding="utf-8")
            proc = subprocess.run(["go", "run", "./cmd/saga-go", "check", str(gp)], cwd=go_dir, text=True, capture_output=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            proc = subprocess.run(["go", "run", "./cmd/saga-go", "check", str(bp)], cwd=go_dir, text=True, capture_output=True, timeout=60)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SAGA-C490", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
