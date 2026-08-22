from __future__ import annotations

import struct
import unittest
from decimal import Decimal

from saga import run_source
from saga.interpreter import Interpreter
from saga.native import Capabilities, NativeFailure
from saga.stdlib import MODULES
from saga.stdlib.machine_control import (
    AxisController, JerkLimitedProfile, ModbusRTUMaster, ModbusTCPMaster,
    SafetyLatch, modbus_crc16,
)


class _FakeUART:
    def __init__(self, response: bytes):
        self.response = bytearray(response)
        self.written = b""
        self.closed = False
    def write(self, payload: bytes) -> None:
        self.written += payload
    def read(self, count: int) -> bytes:
        out = bytes(self.response[:count])
        del self.response[:count]
        return out
    def close(self) -> None:
        self.closed = True


class _FakeSocket:
    def __init__(self, response: bytes):
        self.response = bytearray(response)
        self.sent = b""
        self.closed = False
    def sendall(self, payload: bytes) -> None:
        self.sent += payload
    def recv(self, count: int) -> bytes:
        out = bytes(self.response[:count])
        del self.response[:count]
        return out
    def close(self) -> None:
        self.closed = True


class MachineControl036Tests(unittest.TestCase):
    def test_modbus_crc_known_vector(self):
        # 01 03 00 00 00 0A -> CRC C5CD on the wire (value 0xCDC5).
        self.assertEqual(modbus_crc16(bytes.fromhex("01030000000a")), 0xCDC5)
        it = Interpreter()
        try:
            self.assertEqual(MODULES["machine"].get("modbus_crc16")(it, [bytes.fromhex("01030000000a")]), 0xCDC5)
        finally:
            it.close()

    def test_modbus_rtu_holding_registers_and_crc_validation(self):
        body = bytes.fromhex("010304002a1234")
        response = body + modbus_crc16(body).to_bytes(2, "little")
        master = ModbusRTUMaster.__new__(ModbusRTUMaster)
        master.unit_id = 1
        master.timeout_ms = 50
        master.closed = False
        master._lock = __import__("threading").Lock()
        master.uart = _FakeUART(response)
        self.assertEqual(master.read_holding_registers(0, 2), [42, 0x1234])
        self.assertEqual(master.uart.written[:6], bytes.fromhex("010300000002"))
        self.assertEqual(int.from_bytes(master.uart.written[-2:], "little"), modbus_crc16(master.uart.written[:-2]))

    def test_modbus_tcp_mbap_transaction_and_coils(self):
        pdu = bytes([0x01, 0x01, 0b00000101])
        response = struct.pack(">HHHB", 1, 0, len(pdu) + 1, 7) + pdu
        master = ModbusTCPMaster.__new__(ModbusTCPMaster)
        master.host, master.port, master.unit_id = "plc.local", 502, 7
        master.sock = _FakeSocket(response)
        master._transaction = 0
        master._lock = __import__("threading").Lock()
        master.closed = False
        self.assertEqual(master.read_coils(10, 3), [True, False, True])
        tx, proto, length, unit = struct.unpack(">HHHB", master.sock.sent[:7])
        self.assertEqual((tx, proto, unit), (1, 0, 7))
        self.assertEqual(length, len(master.sock.sent) - 6)

    def test_s_curve_reaches_target_without_overshoot(self):
        profile = JerkLimitedProfile(
            Decimal("0"), Decimal("0"), Decimal("0"), Decimal("1"),
            Decimal("2"), Decimal("4"), Decimal("20"),
        )
        positions = []
        for _ in range(2000):
            positions.append(profile.step(Decimal("0.005")))
            if profile.done():
                break
        self.assertTrue(profile.done())
        self.assertEqual(profile.position, Decimal("1"))
        self.assertTrue(all(Decimal("0") <= value <= Decimal("1") for value in positions))

    def test_axis_controller_trips_following_error_and_soft_limit(self):
        latch = SafetyLatch()
        axis = AxisController.create(
            Decimal("0"), Decimal("-10"), Decimal("10"), Decimal("2"), Decimal("4"),
            Decimal("1"), Decimal("0"), Decimal("0"), Decimal("0.01"), latch,
        )
        axis.set_target(Decimal("1"))
        with self.assertRaises(Exception):
            axis.step(Decimal("-1"), Decimal("0.1"))
        self.assertTrue(latch.tripped)
        self.assertEqual(axis.command, Decimal("0"))

        latch2 = SafetyLatch()
        axis2 = AxisController.create(
            Decimal("0"), Decimal("-1"), Decimal("1"), Decimal("1"), Decimal("2"),
            Decimal("1"), Decimal("0"), Decimal("0"), Decimal("1"), latch2,
        )
        with self.assertRaises(Exception):
            axis2.step(Decimal("2"), Decimal("0.01"))
        self.assertTrue(latch2.tripped)
        self.assertEqual(latch2.reason, "axis soft limit exceeded")

    def test_modbus_tcp_requires_device_and_network_capability(self):
        it = Interpreter(capabilities=Capabilities(allow_device=True))
        try:
            with self.assertRaises(NativeFailure) as ctx:
                MODULES["machine"].get("modbus_tcp_open")(it, ["127.0.0.1", 502, 50, 1])
            self.assertEqual(ctx.exception.diagnostic_id, "SAGA-R103")
        finally:
            it.close()

    def test_saga_surface_axis_and_s_curve(self):
        out = []
        run_source('''
use machine
let curve = machine.s_curve(0.0, 0.0, 0.0, 1.0, 2.0, 4.0, 20.0)
print(machine.s_curve_step(curve, 0.01) >= 0.0)
let safety = machine.safety_latch()
let axis = machine.axis(0.0, -10.0, 10.0, 2.0, 4.0, 1.0, 0.0, 0.0, 2.0, safety)
machine.axis_target(axis, 1.0)
print(machine.axis_step(axis, 0.0, 0.01) >= 0.0)
print(machine.safety_tripped(safety))
''', output=out.append)
        self.assertEqual(out, ["true", "true", "false"])


if __name__ == "__main__":
    unittest.main()
