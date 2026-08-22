#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal, getcontext
import json
from pathlib import Path
import sys
import struct
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.stdlib.machine_control import (
    AxisController,
    MachineControlError,
    SafetyLatch,
    ModbusRTUMaster,
    modbus_crc16,
)

RELEASE = "0.38.0"


class DigitalTwinUART:
    """In-memory Modbus RTU slave used by the endurance qualification.

    It deliberately implements the byte-level UART contract consumed by
    ModbusRTUMaster instead of bypassing the master parser.
    """
    def __init__(self) -> None:
        self.registers = [0] * 256
        self.response = bytearray()
        self.closed = False
        self.corrupt_next_crc = False
        self.drop_next_response = False
        self.transactions = 0

    def write(self, request: bytes) -> int:
        if self.closed:
            raise MachineControlError("digital-twin UART is closed")
        self.transactions += 1
        if len(request) < 8:
            raise MachineControlError("digital-twin received short RTU request")
        if modbus_crc16(request[:-2]) != int.from_bytes(request[-2:], "little"):
            raise MachineControlError("digital-twin received bad request CRC")
        unit, function = request[0], request[1]
        if function == 0x03:
            address, count = struct.unpack(">HH", request[2:6])
            payload = b"".join(self.registers[address + i].to_bytes(2, "big") for i in range(count))
            body = bytes([unit, function, len(payload)]) + payload
        elif function == 0x06:
            address, value = struct.unpack(">HH", request[2:6])
            self.registers[address] = value
            body = request[:-2]
        else:
            body = bytes([unit, function | 0x80, 0x01])
        crc = modbus_crc16(body)
        response = body + crc.to_bytes(2, "little")
        if self.corrupt_next_crc:
            response = response[:-1] + bytes([response[-1] ^ 0x80])
            self.corrupt_next_crc = False
        if self.drop_next_response:
            response = b""
            self.drop_next_response = False
        self.response = bytearray(response)
        return len(request)

    def read(self, count: int) -> bytes:
        if not self.response:
            return b""
        chunk = bytes(self.response[:count])
        del self.response[:count]
        return chunk

    def close(self) -> None:
        self.closed = True


def make_modbus_twin() -> tuple[ModbusRTUMaster, DigitalTwinUART]:
    uart = DigitalTwinUART()
    master = object.__new__(ModbusRTUMaster)
    master.unit_id = 1
    master.uart = uart
    master.timeout_ms = 1
    master.closed = False
    master._lock = threading.Lock()
    return master, uart


def recover_axis(axis: AxisController, safety: SafetyLatch, position: Decimal) -> None:
    # Recovery is intentionally explicit; a safety trip never self-clears.
    safety.clear()
    axis.pid.reset()
    axis.profile.position = position
    axis.profile.velocity = Decimal(0)
    axis.profile.target = position
    axis.command = Decimal(0)


def run(hours: int = 168, period_ms: int = 100) -> dict:
    if hours < 1 or period_ms < 10:
        raise ValueError("hours must be >=1 and period_ms >=10")
    getcontext().prec = 28
    dt = Decimal(period_ms) / Decimal(1000)
    steps = hours * 3600 * 1000 // period_ms
    safety = SafetyLatch()
    axis = AxisController.create(
        Decimal(0), Decimal(-100), Decimal(100),
        Decimal(8), Decimal(16),
        Decimal("0.30"), Decimal("0.015"), Decimal("0.01"),
        Decimal(60), safety,
    )
    axis.set_target(Decimal(25))
    position = Decimal(0)
    velocity = Decimal(0)
    damping = Decimal("0.55")
    torque_gain = Decimal("3.0")
    max_following = Decimal(0)
    max_abs_position = Decimal(0)
    max_abs_command = Decimal(0)
    unexpected_trips: list[dict] = []
    expected_trips: list[dict] = []
    fault_checks: dict[str, bool] = {}
    master, uart = make_modbus_twin()
    modbus_success = 0
    modbus_expected_failures = 0
    target_period_steps = max(1, 600_000 // period_ms)  # 10 simulated minutes
    bus_period_steps = max(1, 60_000 // period_ms)       # one poll per simulated minute
    recover_at = -1

    # Inject deterministic faults after 1/4, 1/2 and 3/4 of the run so the same
    # qualification is meaningful even when a shorter duration is requested.
    following_step = steps // 4
    soft_limit_step = steps // 2
    estop_step = (steps * 3) // 4
    crc_step = max(10, steps // 8)
    drop_step = max(20, steps // 8 + bus_period_steps)

    started = time.perf_counter()
    for i in range(steps):
        if i % target_period_steps == 0 and not safety.tripped:
            phase = (i // target_period_steps) % 4
            target = (Decimal(25), Decimal(-30), Decimal(40), Decimal(-15))[phase]
            try:
                axis.set_target(target)
            except MachineControlError as exc:
                unexpected_trips.append({"step": i, "stage": "retarget", "error": str(exc)})

        if i == recover_at:
            recover_axis(axis, safety, position)
            axis.set_target(Decimal(0))
            recover_at = -1

        measurement = position
        expected_fault = None
        if i == following_step:
            measurement = Decimal(-90) if axis.profile.position >= 0 else Decimal(90)
            expected_fault = "following-error"
        elif i == soft_limit_step:
            measurement = Decimal(150)
            expected_fault = "soft-limit"
        elif i == estop_step:
            safety.trip("digital-twin emergency stop")
            expected_trips.append({"step": i, "kind": "emergency-stop", "reason": safety.reason})
            fault_checks["emergency_stop_zero_output"] = axis.command == 0
            recover_at = i + 50

        if not safety.tripped:
            try:
                command = axis.step(measurement, dt)
            except MachineControlError as exc:
                if expected_fault is None:
                    unexpected_trips.append({"step": i, "stage": "axis", "error": str(exc)})
                else:
                    expected_trips.append({"step": i, "kind": expected_fault, "reason": safety.reason})
                    fault_checks[expected_fault + "_latched"] = safety.tripped and axis.command == 0
                    recover_at = i + 50
                command = Decimal(0)
        else:
            command = Decimal(0)

        # Stable second-order servo-drive digital twin. This is not a physical
        # motor model certification; it is a deterministic plant for exercising
        # Saga's controller and safety state over millions of cycles.
        acceleration = command * torque_gain - velocity * damping
        velocity += acceleration * dt
        position += velocity * dt
        if position > Decimal(99):
            position = Decimal(99); velocity = Decimal(0)
        elif position < Decimal(-99):
            position = Decimal(-99); velocity = Decimal(0)

        if not safety.tripped:
            planned_error = abs(axis.profile.position - position)
            max_following = max(max_following, planned_error)
        max_abs_position = max(max_abs_position, abs(position))
        max_abs_command = max(max_abs_command, abs(command))

        if i % bus_period_steps == 0:
            # Store position in a signed-offset engineering register and read it
            # through the real ModbusRTUMaster transaction/parser path.
            scaled = int((position + Decimal(100)) * Decimal(100))
            uart.registers[0] = max(0, min(65535, scaled))
            try:
                values = master.read_holding_registers(0, 1)
                if values[0] != uart.registers[0]:
                    unexpected_trips.append({"step": i, "stage": "modbus", "error": "register mismatch"})
                else:
                    modbus_success += 1
            except MachineControlError as exc:
                unexpected_trips.append({"step": i, "stage": "modbus", "error": str(exc)})

        if i == crc_step:
            uart.corrupt_next_crc = True
            try:
                master.read_holding_registers(0, 1)
                fault_checks["modbus_crc_rejected"] = False
            except MachineControlError as exc:
                fault_checks["modbus_crc_rejected"] = "CRC" in str(exc)
                modbus_expected_failures += 1
        if i == drop_step:
            uart.drop_next_response = True
            try:
                master.read_holding_registers(0, 1)
                fault_checks["modbus_timeout_rejected"] = False
            except MachineControlError as exc:
                fault_checks["modbus_timeout_rejected"] = "timeout" in str(exc).lower() or "short response" in str(exc).lower()
                modbus_expected_failures += 1

    elapsed = time.perf_counter() - started
    master.close()
    expected_fault_kinds = {e["kind"] for e in expected_trips}
    required = {
        "following-error", "soft-limit", "emergency-stop",
    }
    safety_ok = required.issubset(expected_fault_kinds) and all(fault_checks.get(k, False) for k in (
        "following-error_latched", "soft-limit_latched", "emergency_stop_zero_output",
        "modbus_crc_rejected", "modbus_timeout_rejected",
    ))
    return {
        "schema": "saga.industrial-endurance-simulation.v1",
        "release": RELEASE,
        "mode": "accelerated deterministic digital twin; no physical PLC/drive/motor/CAN/fieldbus hardware attached",
        "simulated_hours": hours,
        "control_period_ms": period_ms,
        "control_cycles": steps,
        "wall_seconds": elapsed,
        "acceleration_factor": (hours * 3600 / elapsed) if elapsed else None,
        "plant": "bounded second-order servo-drive twin",
        "max_following_error_normal": str(max_following),
        "max_abs_position": str(max_abs_position),
        "max_abs_command": str(max_abs_command),
        "expected_safety_trips": expected_trips,
        "unexpected_failures": unexpected_trips,
        "fault_checks": fault_checks,
        "modbus_rtu_transactions": uart.transactions,
        "modbus_successful_periodic_reads": modbus_success,
        "modbus_expected_faults": modbus_expected_failures,
        "explicit_recovery_required": True,
        "pass": safety_ok and not unexpected_trips and max_abs_command <= Decimal(1) and max_abs_position <= Decimal(100),
        "limitations": [
            "No physical industrial equipment is connected; timing, EMI, grounding, bus arbitration, device firmware and mechanical wear are not represented.",
            "The accelerated plant does not establish hard-real-time latency, SIL/PL safety certification, STO behavior or servo tuning suitability.",
            "A physical hardware-in-the-loop and long-running rig test remains required before industrial deployment claims.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--period-ms", type=int, default=100)
    ap.add_argument("--output", default=str(ROOT / "validation" / "industrial-endurance-sim-0.38.0.json"))
    args = ap.parse_args()
    report = run(args.hours, args.period_ms)
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
