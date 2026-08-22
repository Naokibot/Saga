from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

from saga import run_source
from saga.stdlib.machine_precision import (
    AlphaBetaObserver,
    BiquadFilter,
    DeadlineBudget,
    TwoDOFPID,
    clarke,
    inverse_park,
    motor_feedforward,
    park,
    svpwm,
)


class PrecisionMachine046Tests(unittest.TestCase):
    def test_pid2_uses_setpoint_weight_and_derivative_on_measurement(self):
        pid = TwoDOFPID(D("2"), D("1"), D(".5"), D("1"), D(".02"), D("4"), D("-2"), D("2"))
        first = pid.step(D("1"), D("0"), D("0"), D(".01"))
        self.assertEqual(first, D("2"))
        # A setpoint-only change must not create a derivative kick because D is
        # computed from the measurement path.
        second = pid.step(D("2"), D("0"), D("0"), D(".01"))
        self.assertEqual(second, D("2"))
        self.assertEqual(pid.derivative_state, D("0"))

    def test_pid2_back_calculation_keeps_integral_bounded(self):
        pid = TwoDOFPID(D("10"), D("5"), D("0"), D("1"), D("0"), D("10"), D("-1"), D("1"))
        for _ in range(100):
            self.assertEqual(pid.step(D("10"), D("0"), D("0"), D(".01")), D("1"))
        self.assertGreaterEqual(pid.integral, D("-1"))
        self.assertLessEqual(pid.integral, D("1"))

    def test_alpha_beta_observer(self):
        observer = AlphaBetaObserver(D(".5"), D(".1"), D("0"), D("0"))
        position, velocity = observer.step(D("2"), D(".1"))
        self.assertEqual(position, D("1.0"))
        self.assertEqual(velocity, D("2"))
        observer.reset(D("3"), D("4"))
        self.assertEqual((observer.position, observer.velocity), (D("3"), D("4")))

    def test_notch_reset_is_deterministic(self):
        notch = BiquadFilter.notch(D("1000"), D("120"), D("5"))
        first = [notch.step(D("1")) for _ in range(8)]
        notch.reset()
        second = [notch.step(D("1")) for _ in range(8)]
        self.assertEqual(first, second)
        self.assertTrue(all(value.is_finite() for value in first))

    def test_foc_transforms_and_svpwm(self):
        alpha, beta, zero = clarke(D("1"), D("-.5"), D("-.5"))
        self.assertAlmostEqual(float(alpha), 1.0, places=12)
        self.assertAlmostEqual(float(beta), 0.0, places=12)
        self.assertEqual(zero, D("0.0"))
        d, q = park(alpha, beta, D("0"))
        self.assertAlmostEqual(float(d), 1.0, places=12)
        self.assertAlmostEqual(float(q), 0.0, places=12)
        a2, b2 = inverse_park(d, q, D("0"))
        self.assertAlmostEqual(float(a2), 1.0, places=12)
        self.assertAlmostEqual(float(b2), 0.0, places=12)
        duty = svpwm(D("1"), D("0"), D("4"))
        self.assertEqual(duty, (D("0.6875"), D("0.3125"), D("0.3125")))

    def test_motor_feedforward_direction_is_explicit(self):
        self.assertEqual(motor_feedforward(D(".2"), D("1.5"), D(".1"), D("2"), D("3")), D("3.5"))
        self.assertEqual(motor_feedforward(D(".2"), D("1.5"), D(".1"), D("0"), D("-2")), D("-.4"))

    def test_deadline_budget_observes_but_does_not_change_control_policy(self):
        budget = DeadlineBudget(1_000_000, 1_000_000)
        budget.begin()
        over = budget.end()
        report = json.loads(budget.stats_json())
        self.assertFalse(over)
        self.assertEqual(report["samples"], 1)
        self.assertEqual(report["timing_class"], "hosted-soft-realtime")
        budget.reset()
        self.assertEqual(json.loads(budget.stats_json())["samples"], 0)

    def test_saga_surface_composes_precision_control_without_device_permission(self):
        out: list[str] = []
        run_source('''
use machine
let controller = machine.pid2(1.0, 0.0, 0.0, 1.0, 0.0, 0.0, -10.0, 10.0)
print(machine.pid2_step(controller, 2.0, 0.5, 0.0, 0.01))
print(machine.motor_feedforward(0.2, 1.5, 0.1, 2.0, 3.0))
let observer = machine.alpha_beta(0.5, 0.1, 0.0, 0.0)
let estimate = machine.alpha_beta_step(observer, 2.0, 0.1)
print(estimate[0])
print(estimate[1])
let dq = machine.park(1.0, 0.0, 0.0)
print(dq[0])
let duty = machine.svpwm(1.0, 0.0, 4.0)
print(duty[0])
''', output=out.append)
        self.assertEqual(out, ["1.5", "3.5", "1", "2", "1", "0.6875"])

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_python_and_go_share_precision_machine_surface(self):
        source = '''
use machine
let controller = machine.pid2(1.0, 0.0, 0.0, 1.0, 0.0, 0.0, -10.0, 10.0)
print(machine.pid2_step(controller, 2.0, 0.5, 0.0, 0.01))
print(machine.motor_feedforward(0.2, 1.5, 0.1, 2.0, 3.0))
let observer = machine.alpha_beta(0.5, 0.1, 0.0, 0.0)
let estimate = machine.alpha_beta_step(observer, 2.0, 0.1)
print(estimate[0])
print(estimate[1])
let dq = machine.park(1.0, 0.0, 0.0)
print(dq[0])
let duty = machine.svpwm(1.0, 0.0, 4.0)
print(duty[0])
'''
        py_output: list[str] = []
        run_source(source, output=py_output.append)
        with tempfile.TemporaryDirectory() as td:
            program = Path(td) / "precision.saga"
            program.write_text(source, encoding="utf-8")
            go_dir = Path(__file__).resolve().parents[1] / "implementations" / "go" / "cmd" / "saga-go"
            proc = subprocess.run(["go", "run", ".", "run", str(program)], cwd=go_dir, text=True, capture_output=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(proc.stdout.strip().splitlines(), py_output)


if __name__ == "__main__":
    unittest.main()
