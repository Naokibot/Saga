from __future__ import annotations

import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from saga.interpreter import Interpreter
from saga.native import Capabilities, NativeFailure
from saga.stdlib import MODULES
from saga.stdlib.machine_control import CANDevice, ControlCycle, DCMotor, EncoderTracker, MotionProfile, PIDController, SafetyLatch, Servo, Watchdog, servo_duty, slew


class MachineControl028Tests(unittest.TestCase):
    def test_pid_and_slew_are_stable(self):
        pid = PIDController.create(Decimal('1'), Decimal('0.1'), Decimal('0'), Decimal('-1'), Decimal('1'))
        self.assertEqual(pid.step(Decimal('10'), Decimal('8'), Decimal('0.1')), Decimal('1'))
        self.assertEqual(slew(Decimal('0'), Decimal('10'), Decimal('2'), Decimal('0.5')), Decimal('1.0'))
        pid.set_integral_limits(Decimal('-0.5'), Decimal('0.5'))
        for _ in range(20):
            pid.step(Decimal('100'), Decimal('0'), Decimal('0.01'))
        self.assertLessEqual(pid.integral, Decimal('0.5'))

    def test_motion_profile_reaches_target_without_overshoot(self):
        profile = MotionProfile(Decimal('0'), Decimal('0'), Decimal('1'), Decimal('2'), Decimal('4'))
        positions = []
        for _ in range(200):
            positions.append(profile.step(Decimal('0.01')))
            if profile.done():
                break
        self.assertTrue(profile.done())
        self.assertEqual(profile.position, Decimal('1'))
        self.assertTrue(all(Decimal('0') <= p <= Decimal('1') for p in positions))

    def test_watchdog_safety_and_cycle(self):
        wd = Watchdog(15)
        self.assertFalse(wd.expired())
        time.sleep(0.02)
        self.assertTrue(wd.expired())
        wd.feed()
        self.assertGreater(wd.remaining_ms(), 0)

        latch = SafetyLatch()
        latch.trip('guard open')
        self.assertTrue(latch.tripped)
        self.assertEqual(latch.reason, 'guard open')
        latch.clear()
        self.assertFalse(latch.tripped)

        cycle = ControlCycle(1000)
        cycle.wait()
        self.assertGreaterEqual(cycle.last_jitter_us, 0)

    def test_servo_mapping(self):
        duty = servo_duty(
            Decimal('0'), Decimal('-90'), Decimal('90'),
            Decimal('1000'), Decimal('2000'), Decimal('20000'),
        )
        self.assertEqual(duty, Decimal('0.075'))


    def test_encoder_and_motor_safety(self):
        encoder = EncoderTracker(1000, Decimal("2"))
        encoder.update(0, 1_000_000_000)
        encoder.update(1000, 2_000_000_000)
        self.assertEqual(encoder.position_degrees, Decimal("180"))
        self.assertEqual(encoder.velocity_rpm, Decimal("30"))

        class FakePWM:
            def __init__(self): self.duty = Decimal(0)
            def set_duty(self, value): self.duty = value
        forward, reverse = FakePWM(), FakePWM()
        safety = SafetyLatch()
        motor = DCMotor(forward, reverse, Decimal("0.05"), safety)
        motor.write(Decimal("0.6"))
        self.assertEqual(forward.duty, Decimal("0.6"))
        self.assertEqual(reverse.duty, Decimal(0))
        safety.trip("guard open")
        with self.assertRaises(Exception): motor.write(Decimal("0.5"))
        self.assertEqual(forward.duty, Decimal(0))
        self.assertEqual(reverse.duty, Decimal(0))


    def test_monotonic_clock_increases(self):
        interpreter = Interpreter()
        try:
            first = MODULES['machine'].get('monotonic_ns')(interpreter, [])
            time.sleep(0.002)
            second = MODULES['machine'].get('monotonic_ns')(interpreter, [])
            self.assertGreater(second, first)
        finally:
            interpreter.close()

    def test_can_extended_id_sets_eff_flag(self):
        class FakeSocket:
            def __init__(self): self.frame = b''
            def send(self, frame): self.frame = frame; return len(frame)

        dev = CANDevice.__new__(CANDevice)
        dev.fd_mode = False
        dev.sock = FakeSocket()
        dev.send(0x123, b'\x01')
        standard_id = int.from_bytes(dev.sock.frame[:4], 'little')
        self.assertEqual(standard_id, 0x123)
        dev.send(0x12345, b'\x02')
        extended_id = int.from_bytes(dev.sock.frame[:4], 'little')
        self.assertEqual(extended_id, 0x12345 | CANDevice.CAN_EFF_FLAG)


    def test_i2c_combined_transfer_rejects_oversized_segments(self):
        dev = object.__new__(__import__('saga.stdlib.machine_control', fromlist=['I2CDevice']).I2CDevice)
        dev.fd = -1
        dev.path = '/dev/i2c-test'
        dev.address = 0x40
        with self.assertRaises(Exception):
            dev.write_read(b'x' * 65536, 1)
        with self.assertRaises(Exception):
            dev.write_read(b'x', 65536)

    def test_can_fd_socket_accepts_classic_frame(self):
        class FakeSocket:
            def settimeout(self, _timeout): pass
            def recv(self, _count):
                import struct
                return struct.pack('=IB3x8s', 0x321, 2, b'ok'.ljust(8, b'\0'))
        dev = CANDevice.__new__(CANDevice)
        dev.fd_mode = True
        dev.sock = FakeSocket()
        self.assertEqual(dev.recv(10), (0x321, b'ok'))

    def test_safety_trip_stops_guarded_servo_immediately(self):
        class FakePWM:
            period_ns = 20_000_000
            def __init__(self): self.duty = Decimal(0)
            def set_duty(self, value): self.duty = value

        pwm = FakePWM()
        latch = SafetyLatch()
        servo = Servo(pwm, Decimal('1000'), Decimal('2000'), Decimal('-90'), Decimal('90'))
        servo.guard(latch)
        servo.write_degrees(Decimal('0'))
        self.assertEqual(pwm.duty, Decimal('0.075'))
        latch.trip('guard open')
        self.assertEqual(pwm.duty, Decimal(0))


    def test_low_pass_watchdog_and_interlock_helpers(self):
        self.assertEqual(
            MODULES['machine'].get('low_pass')(Interpreter(), [Decimal('0'), Decimal('10'), Decimal('0.25')]),
            Decimal('2.50'),
        )
        latch = SafetyLatch()
        wd = Watchdog(1)
        time.sleep(0.003)
        interpreter = Interpreter()
        try:
            self.assertTrue(MODULES['machine'].get('watchdog_check')(interpreter, [wd, latch, 'watchdog']))
            self.assertTrue(latch.tripped)
            latch.clear()
            self.assertFalse(MODULES['machine'].get('safety_check')(interpreter, [latch, False, 'limit']))
            self.assertTrue(latch.tripped)
        finally:
            interpreter.close()

    def test_encoder_wraparound_is_unwrapped(self):
        encoder = EncoderTracker(4096, Decimal('1'))
        encoder.set_wrap_modulus(65536)
        encoder.update(65530, 1_000_000_000)
        encoder.update(4, 2_000_000_000)
        self.assertEqual(encoder.unwrapped_count, 65540)
        self.assertEqual(encoder.velocity_rpm, Decimal(10) * Decimal(60_000_000_000) / (Decimal(4096) * Decimal(1_000_000_000)))


    def test_safety_clear_is_rejected_while_trip_is_stopping_actuators(self):
        import threading
        latch = SafetyLatch()
        entered = threading.Event()
        release = threading.Event()
        def slow_stop():
            entered.set()
            release.wait(1)
        latch.register_stop(slow_stop)
        errors = []
        thread = threading.Thread(target=lambda: self._capture_trip(latch, errors))
        thread.start()
        self.assertTrue(entered.wait(1))
        with self.assertRaises(Exception):
            latch.clear()
        release.set()
        thread.join(1)
        self.assertFalse(errors)
        self.assertTrue(latch.tripped)

    @staticmethod
    def _capture_trip(latch, errors):
        try:
            latch.trip('concurrent stop')
        except Exception as exc:
            errors.append(exc)

    def test_hardware_calls_require_device_capability(self):
        interpreter = Interpreter(capabilities=Capabilities())
        try:
            with self.assertRaises(NativeFailure) as ctx:
                MODULES['machine'].get('i2c_open')(interpreter, ['/dev/i2c-1', 0x40])
            self.assertEqual(ctx.exception.diagnostic_id, 'SAGA-R103')
        finally:
            interpreter.close()

    def test_iio_read_is_restricted_to_iio_sysfs(self):
        interpreter = Interpreter(capabilities=Capabilities(allow_device=True))
        try:
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / 'raw'
                p.write_text('123')
                with self.assertRaises(NativeFailure):
                    MODULES['machine'].get('iio_read')(interpreter, [str(p), Decimal('1')])
        finally:
            interpreter.close()

    def test_python_saga_surface_executes_portable_control(self):
        from saga import run_source
        output = []
        run_source('''
use machine
let pid = machine.pid(1.0, 0.1, 0.0, -1.0, 1.0)
print(machine.pid_step(pid, 10.0, 8.0, 0.1))
print(machine.slew(0.0, 10.0, 2.0, 0.5))
let p = machine.profile(0.0, 0.0, 1.0, 2.0, 4.0)
print(machine.profile_step(p, 0.1))
''', output=output.append)
        self.assertEqual(output, ['1', '1', '0.02'])


if __name__ == '__main__':
    unittest.main()
