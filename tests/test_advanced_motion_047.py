from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

from saga import run_source
from saga.stdlib.machine_motion import (
    DisturbanceObserver,
    FOCCurrentLoop,
    MPC2,
    MultiAxisSynchronizer,
    RLS2,
    UnifiedEncoder,
    allocation_free_profile_json,
    ethercat_first_datagram_json,
    ethercat_lrw,
    friction_compensation,
    canfd_frame_json,
)


class AdvancedMotion047Tests(unittest.TestCase):
    def test_foc_current_loop_zero_error_has_centered_duty(self):
        loop = FOCCurrentLoop(
            D("2"), D("20"), D("2"), D("20"), D("0.1"), D("0.001"), D("0.001"),
            D("0.02"), D("20"), D("24"), D("10"),
        )
        loop.step(D("0"), D("0"), D("0"), D("0"), D("0"), D("0"), D("0"), D("48"), D("0.0001"))
        self.assertEqual((loop.measured_d, loop.measured_q), (D(0), D(0)))
        self.assertEqual((loop.duty_a, loop.duty_b, loop.duty_c), (D("0.5"), D("0.5"), D("0.5")))

    def test_foc_voltage_is_limited_by_bus_and_profile(self):
        loop = FOCCurrentLoop(
            D("20"), D("100"), D("20"), D("100"), D("0.2"), D("0.001"), D("0.001"),
            D("0.04"), D("100"), D("100"), D("20"),
        )
        loop.step(D("50"), D("50"), D("0"), D("0"), D("0"), D("0"), D("0"), D("12"), D("0.001"))
        magnitude = math.hypot(float(loop.voltage_d), float(loop.voltage_q))
        self.assertLessEqual(magnitude, 12 / math.sqrt(3) + 1e-12)
        self.assertTrue(all(D(0) <= q <= D(1) for q in (loop.duty_a, loop.duty_b, loop.duty_c)))

    def test_incremental_and_absolute_encoder_unwrap(self):
        enc = UnifiedEncoder(4096, D(1), 4096, 1, D(1))
        enc.sample(4090, 1_000_000_000)
        enc.sample(2, 1_010_000_000)
        self.assertEqual(enc.unwrapped_count, 4098)
        self.assertGreater(enc.velocity_deg_s, 0)
        enc.align_absolute(1024, D("90"))
        enc.sample(1024, 2_000_000_000)
        self.assertEqual(enc.position_degrees, D("90"))

    def test_online_rls_identifies_two_parameter_model(self):
        est = RLS2.create(D("0.995"), D("1000"))
        # y = 2*x0 - 0.5*x1
        for i in range(1, 80):
            x0 = D(i) / D(10)
            x1 = D((i * 7) % 13) / D(10)
            est.update(x0, x1, D(2) * x0 - D("0.5") * x1)
        self.assertAlmostEqual(float(est.theta0), 2.0, places=3)
        self.assertAlmostEqual(float(est.theta1), -0.5, places=3)

    def test_mpc2_drives_double_integrator_toward_reference_with_bounds(self):
        # x=[position, velocity], dt=0.1, input=acceleration.
        mpc = MPC2(D(1), D("0.1"), D(0), D(1), D("0.005"), D("0.1"), D(20), D(1), D("0.2"), 12, D(-2), D(2))
        x0, x1 = D(0), D(0)
        first = mpc.step(x0, x1, D(1), D(0))
        self.assertGreater(first, 0)
        self.assertLessEqual(abs(first), D(2))
        for _ in range(50):
            u = mpc.step(x0, x1, D(1), D(0))
            x0, x1 = x0 + D("0.1")*x1 + D("0.005")*u, x1 + D("0.1")*u
        self.assertGreater(x0, D("0.5"))

    def test_disturbance_observer_converges(self):
        dob = DisturbanceObserver(D(1), D("0.2"), D(20))
        v = D(0)
        dt = D("0.001")
        disturbance = D("0.7")
        for _ in range(2000):
            u = D("0.4")
            acceleration = u - D("0.2")*v + disturbance
            v += acceleration * dt
            estimate = dob.step(u, v, dt)
        self.assertAlmostEqual(float(estimate), 0.7, places=2)

    def test_stribeck_friction_compensation_is_odd_and_bounded_near_zero(self):
        pos = friction_compensation(D("0.4"), D("0.1"), D("0.8"), D("0.2"), D("0.05"), D("0.01"))
        neg = friction_compensation(D("0.4"), D("0.1"), D("0.8"), D("0.2"), D("-0.05"), D("0.01"))
        self.assertAlmostEqual(float(pos), -float(neg), places=12)
        self.assertEqual(friction_compensation(D("0.4"), D("0.1"), D("0.8"), D("0.2"), D(0), D("0.01")), D(0))

    def test_multi_axis_sync_electronic_gearing_and_skew_detection(self):
        sync = MultiAxisSynchronizer(2, D("0.5"), D(2), D("0.2"))
        sync.configure(0, D(1), D(0))
        sync.configure(1, D(2), D("0.1"))
        sync.begin(D(1))
        self.assertEqual(sync.correction(0, D("0.9")), D("0.05"))
        self.assertEqual(sync.correction(1, D("2.1")), D(0))
        self.assertTrue(sync.healthy)
        sync.correction(1, D("1.0"))
        self.assertFalse(sync.healthy)

    def test_ethercat_lrw_codec_and_parser(self):
        frame = ethercat_lrw(7, 0x12345678, bytes.fromhex("11223344"))
        report = json.loads(ethercat_first_datagram_json(frame))
        self.assertEqual(report["command"], "LRW")
        self.assertEqual(report["index"], 7)
        self.assertEqual(report["address"], 0x5678)
        self.assertEqual(report["offset"], 0x1234)
        self.assertEqual(report["data_hex"], "11223344")
        self.assertEqual(report["working_counter"], 0)

    def test_allocation_free_profile_is_explicit_about_reference_runtime_boundary(self):
        report = json.loads(allocation_free_profile_json())
        self.assertEqual(report["profile"], "mcu-control-0.47")
        self.assertEqual(report["saga_visible_heap_allocation_in_tick"], "forbidden")
        self.assertFalse(report["host_reference_runtime_hard_realtime"])

    def test_saga_surface_composes_advanced_motion_without_device_authority(self):
        out: list[str] = []
        run_source('''
use machine
let foc = machine.foc_current(2.0, 20.0, 2.0, 20.0, 0.1, 0.001, 0.001, 0.02, 20.0, 24.0, 10.0)
machine.foc_step(foc, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 48.0, 0.0001)
print(machine.foc_duty(foc, 0))
let enc = machine.encoder_integrated(4096, 1.0, 4096, 1, 1.0)
machine.encoder_sample(enc, 4090, 1000000000)
machine.encoder_sample(enc, 2, 1010000000)
print(machine.encoder_position_deg(enc))
let ident = machine.rls2(0.99, 100.0)
machine.rls2_update(ident, 1.0, 2.0, 3.0)
print(machine.rls2_error(ident))
let sync = machine.axis_sync(2, 0.5, 2.0, 0.2)
machine.axis_sync_config(sync, 1, 2.0, 0.1)
machine.axis_sync_begin(sync, 1.0)
print(machine.axis_sync_correction(sync, 1, 2.1))
let ec = machine.ethercat_lrw(1, 305419896, machine.bytes_from_hex("1122"))
print(machine.ethercat_first_datagram_json(ec))
''', output=out.append)
        self.assertEqual(out[0], "0.5")
        self.assertTrue(float(out[1]) > 360.0)
        self.assertEqual(out[2], "3")
        self.assertEqual(out[3], "0")
        self.assertIn('"command":"LRW"', out[4])

    def test_canfd_metadata_preserves_brs_esi_and_timestamp_source(self):
        report = json.loads(canfd_frame_json(True, 0x123, bytes.fromhex("aabb"), 0x03, 123456789, "hardware"))
        self.assertEqual(report, {
            "received": True, "id": 0x123, "data_hex": "aabb",
            "brs": True, "esi": True, "timestamp_ns": 123456789,
            "timestamp_source": "hardware",
        })

    def test_ethercat_raw_open_is_device_capability_gated(self):
        with self.assertRaises(Exception) as ctx:
            run_source("""
use machine
let mac = machine.bytes_from_hex("ffffffffffff")
let ec = machine.ethercat_open("lo", mac, false)
""")
        self.assertIn("device", str(ctx.exception).lower())

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_python_and_go_share_advanced_motion_surface(self):
        source = '''
use machine
let enc = machine.encoder_integrated(4096, 1.0, 4096, 1, 1.0)
machine.encoder_sample(enc, 4090, 1000000000)
machine.encoder_sample(enc, 2, 1010000000)
print(machine.encoder_position_deg(enc))
let sync = machine.axis_sync(2, 0.5, 2.0, 0.2)
machine.axis_sync_config(sync, 1, 2.0, 0.1)
machine.axis_sync_begin(sync, 1.0)
print(machine.axis_sync_correction(sync, 1, 2.1))
let ec = machine.ethercat_lrw(1, 305419896, machine.bytes_from_hex("1122"))
print(machine.ethercat_first_datagram_json(ec))
print(machine.allocation_free_profile_json())
'''
        py_output: list[str] = []
        run_source(source, output=py_output.append)
        with tempfile.TemporaryDirectory() as td:
            program = Path(td) / "advanced-motion.saga"
            program.write_text(source, encoding="utf-8")
            go_dir = Path(__file__).resolve().parents[1] / "implementations" / "go" / "cmd" / "saga-go"
            proc = subprocess.run(["go", "run", ".", "run", str(program)], cwd=go_dir, text=True, capture_output=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(proc.stdout.strip().splitlines(), py_output)


if __name__ == "__main__":
    unittest.main()

# Allocation-free source-profile tests are kept in the release module so the
# motion qualification covers both control math and the MCU/RTOS source rules.
class AllocationFreeControl047Tests(unittest.TestCase):
    def test_control_tick_accepts_bounded_scalar_control(self):
        from saga.api import compile_source
        compile_source('''
use machine
@control_tick
fn tick(state: decimal, target: decimal) -> decimal {
    var correction = target - state
    for i in 0..3 {
        correction = correction * 0.5
    }
    return correction
}
''')

    def test_control_tick_rejects_dynamic_list(self):
        from saga.api import compile_source
        with self.assertRaises(Exception) as ctx:
            compile_source('''
@control_tick
fn tick(x: int) -> int {
    let values = [x, x + 1]
    return x
}
''')
        self.assertIn('SAGA-C471', str(ctx.exception))

    def test_control_tick_rejects_blocking_canfd_receive(self):
        from saga.api import compile_source
        with self.assertRaises(Exception) as ctx:
            compile_source('''
use machine
@control_tick
fn tick() -> int {
    let packet = machine.canfd_recv(0, 1)
    return 0
}
''')
        self.assertIn('SAGA-C479', str(ctx.exception))

    @unittest.skipUnless(shutil.which("go"), "Go toolchain required")
    def test_python_and_go_enforce_control_tick_profile(self):
        from saga.api import compile_source
        source = '''
use machine
@control_tick
fn tick() -> int {
    let packet = machine.canfd_recv(0, 1)
    return 0
}
'''
        with self.assertRaises(Exception) as ctx:
            compile_source(source)
        self.assertIn("SAGA-C479", str(ctx.exception))
        with tempfile.TemporaryDirectory() as td:
            program = Path(td) / "bad-control-tick.saga"
            program.write_text(source, encoding="utf-8")
            go_dir = Path(__file__).resolve().parents[1] / "implementations" / "go" / "cmd" / "saga-go"
            proc = subprocess.run(["go", "run", ".", "check", str(program)], cwd=go_dir, text=True, capture_output=True, timeout=60)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SAGA-C479", proc.stdout + proc.stderr)
