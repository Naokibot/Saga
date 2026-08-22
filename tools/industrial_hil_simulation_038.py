#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal, getcontext
import json
import os
from pathlib import Path
import pty
import select
import socket
import struct
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.stdlib.machine_control import AxisController, SafetyLatch, MachineControlError, ModbusRTUMaster, modbus_crc16

RELEASE = "0.38.0"


class PTYModbusPLC:
    """OS-level pseudo-terminal Modbus RTU slave.

    The Saga Modbus master opens the PTY slave through the normal Linux UARTDevice,
    so termios/select/read/write are exercised. Only the remote PLC is simulated.
    """
    def __init__(self) -> None:
        self.master_fd, self.slave_guard_fd = pty.openpty()
        self.slave_path = os.ttyname(self.slave_guard_fd)
        self.registers = [0] * 256
        self.coils = [False] * 256
        self.running = True
        self.transactions = 0
        self.bad_crc_responses = 0
        self.dropped_responses = 0
        self.corrupt_next = False
        self.drop_next = False
        self.thread = threading.Thread(target=self._run, name="saga-hil-modbus-plc", daemon=True)
        self.thread.start()

    def _reply(self, req: bytes) -> bytes:
        if len(req) < 8 or modbus_crc16(req[:-2]) != int.from_bytes(req[-2:], "little"):
            return b""
        self.transactions += 1
        unit, fn = req[0], req[1]
        if fn in (0x03, 0x04):
            addr, count = struct.unpack(">HH", req[2:6])
            payload = b"".join(self.registers[addr+i].to_bytes(2, "big") for i in range(count))
            body = bytes([unit, fn, len(payload)]) + payload
        elif fn == 0x06:
            addr, value = struct.unpack(">HH", req[2:6]); self.registers[addr] = value
            body = req[:-2]
        elif fn == 0x05:
            addr, value = struct.unpack(">HH", req[2:6]); self.coils[addr] = value == 0xFF00
            body = req[:-2]
        else:
            body = bytes([unit, fn | 0x80, 0x01])
        out = body + modbus_crc16(body).to_bytes(2, "little")
        if self.corrupt_next:
            self.corrupt_next = False; self.bad_crc_responses += 1
            out = out[:-1] + bytes([out[-1] ^ 0x40])
        if self.drop_next:
            self.drop_next = False; self.dropped_responses += 1
            return b""
        return out

    def _run(self) -> None:
        buf = bytearray()
        while self.running:
            ready, _, _ = select.select([self.master_fd], [], [], 0.02)
            if not ready:
                continue
            try:
                chunk = os.read(self.master_fd, 512)
            except OSError:
                break
            if not chunk:
                continue
            buf.extend(chunk)
            # Qualification only emits fixed 8-byte requests for single read/write.
            while len(buf) >= 8:
                req = bytes(buf[:8]); del buf[:8]
                reply = self._reply(req)
                if reply:
                    try: os.write(self.master_fd, reply)
                    except OSError: return

    def close(self) -> None:
        self.running = False
        try: os.close(self.master_fd)
        except OSError: pass
        try: os.close(self.slave_guard_fd)
        except OSError: pass
        self.thread.join(timeout=1)


class VirtualCANBus:
    """Socket-backed CAN transport simulator used when vcan cannot be created."""
    def __init__(self) -> None:
        self.host, self.drive = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.host.setblocking(False); self.drive.setblocking(False)
        self.frames_tx = 0; self.frames_rx = 0; self.dropped = 0
        self.drop_next_host = False

    @staticmethod
    def pack(can_id: int, payload: bytes) -> bytes:
        if not 0 <= can_id <= 0x1FFFFFFF or len(payload) > 64:
            raise ValueError("invalid virtual CAN frame")
        return struct.pack(">IB", can_id, len(payload)) + payload

    @staticmethod
    def unpack(frame: bytes) -> tuple[int, bytes]:
        if len(frame) < 5: raise ValueError("short virtual CAN frame")
        can_id, n = struct.unpack(">IB", frame[:5])
        if n > 64 or len(frame) != 5+n: raise ValueError("malformed virtual CAN frame")
        return can_id, frame[5:]

    def host_send(self, can_id: int, payload: bytes) -> None:
        self.frames_tx += 1
        if self.drop_next_host:
            self.drop_next_host = False; self.dropped += 1; return
        self.host.send(self.pack(can_id, payload))

    def drive_recv(self) -> tuple[int, bytes] | None:
        try: return self.unpack(self.drive.recv(80))
        except BlockingIOError: return None

    def drive_send(self, can_id: int, payload: bytes) -> None:
        self.drive.send(self.pack(can_id, payload)); self.frames_rx += 1

    def host_recv(self) -> tuple[int, bytes] | None:
        try: return self.unpack(self.host.recv(80))
        except BlockingIOError: return None

    def close(self) -> None:
        self.host.close(); self.drive.close()


def run(hours: int = 24, period_ms: int = 100) -> dict:
    if hours < 1 or period_ms < 10: raise ValueError("hours>=1 and period_ms>=10 required")
    getcontext().prec = 28
    dt = Decimal(period_ms) / Decimal(1000)
    steps = hours * 3600 * 1000 // period_ms
    safety = SafetyLatch()
    axis = AxisController.create(Decimal(0), Decimal(-100), Decimal(100), Decimal(8), Decimal(16), Decimal("0.25"), Decimal("0.01"), Decimal("0.005"), Decimal(50), safety)
    axis.set_target(Decimal(25))
    plc = PTYModbusPLC()
    master = ModbusRTUMaster(plc.slave_path, 115200, 20, 1)
    can = VirtualCANBus()
    position = Decimal(0); velocity = Decimal(0); command = Decimal(0)
    encoder_counts = 0
    unexpected: list[str] = []
    fault_checks: dict[str, bool] = {}
    modbus_ok = 0; encoder_feedback = 0
    bus_period = max(1, 60_000 // period_ms)
    target_period = max(1, 300_000 // period_ms)
    estop_step = steps // 3
    can_drop_step = steps // 2
    crc_step = (steps * 2) // 3
    timeout_step = min(steps - 2, crc_step + bus_period)
    reset_at = -1
    started = time.perf_counter()

    for i in range(steps):
        if i % target_period == 0 and not safety.tripped:
            axis.set_target((Decimal(25), Decimal(-25), Decimal(40), Decimal(-10))[(i // target_period) % 4])
        if i == reset_at:
            safety.clear(); axis.pid.reset(); axis.profile.position = position; axis.profile.velocity = Decimal(0); axis.profile.target = position; axis.command = Decimal(0); axis.set_target(Decimal(0)); reset_at = -1
        if i == estop_step:
            safety.trip("HIL simulated dual-channel E-stop")
            fault_checks["estop_zero_output"] = axis.command == 0
            reset_at = i + 20
        if not safety.tripped:
            try: command = axis.step(position, dt)
            except MachineControlError as exc:
                unexpected.append(f"axis:{i}:{exc}"); command = Decimal(0)
        else:
            command = Decimal(0)

        # Command is transported over the virtual CAN socket, then applied by the drive twin.
        raw_cmd = int(max(-10000, min(10000, int(command * Decimal(10000)))))
        if i == can_drop_step: can.drop_next_host = True
        can.host_send(0x201, struct.pack(">h", raw_cmd))
        frame = can.drive_recv()
        drive_cmd = Decimal(0)
        if frame:
            _, payload = frame; drive_cmd = Decimal(struct.unpack(">h", payload)[0]) / Decimal(10000)
        elif i == can_drop_step:
            fault_checks["can_command_drop_forces_zero"] = True
        else:
            unexpected.append(f"can-command-missing:{i}")

        # Motor + load twin and encoder generation.
        acceleration = drive_cmd * Decimal("3.2") - velocity * Decimal("0.7")
        velocity += acceleration * dt; position += velocity * dt
        position = max(Decimal(-99), min(Decimal(99), position))
        encoder_counts = int(position * Decimal(4096) / Decimal(360))
        can.drive_send(0x181, struct.pack(">i", encoder_counts))
        fb = can.host_recv()
        if fb:
            _, payload = fb; count = struct.unpack(">i", payload)[0]
            measured = Decimal(count) * Decimal(360) / Decimal(4096)
            if abs(measured - position) > Decimal("0.1"): unexpected.append(f"encoder-mismatch:{i}")
            else: encoder_feedback += 1

        if i % bus_period == 0:
            plc.registers[0] = max(0, min(65535, int((position + Decimal(100)) * 100)))
            try:
                got = master.read_holding_registers(0, 1)
                if got[0] != plc.registers[0]: unexpected.append(f"modbus-register-mismatch:{i}")
                else: modbus_ok += 1
            except Exception as exc: unexpected.append(f"modbus:{i}:{exc}")
        if i == crc_step:
            plc.corrupt_next = True
            try: master.read_holding_registers(0, 1); fault_checks["modbus_crc_rejected"] = False
            except MachineControlError as exc: fault_checks["modbus_crc_rejected"] = "CRC" in str(exc)
        if i == timeout_step:
            plc.drop_next = True
            try: master.read_holding_registers(0, 1); fault_checks["modbus_timeout_rejected"] = False
            except MachineControlError as exc: fault_checks["modbus_timeout_rejected"] = "timeout" in str(exc).lower() or "short" in str(exc).lower()

    elapsed = time.perf_counter() - started
    master.close(); plc.close(); can.close()
    checks = ["estop_zero_output", "can_command_drop_forces_zero", "modbus_crc_rejected", "modbus_timeout_rejected"]
    passed = not unexpected and all(fault_checks.get(k, False) for k in checks) and encoder_feedback == steps
    return {
        "schema": "saga.industrial-hil-simulation.v1",
        "release": RELEASE,
        "mode": "OS-level HIL simulation: Linux PTY/termios Modbus RTU + UNIX datagram virtual CAN + servo/motor/encoder plant; no physical industrial equipment",
        "simulated_hours": hours,
        "period_ms": period_ms,
        "control_cycles": steps,
        "wall_seconds": elapsed,
        "acceleration_factor": hours*3600/elapsed if elapsed else None,
        "modbus_rtu_transactions": plc.transactions,
        "modbus_periodic_reads_ok": modbus_ok,
        "can_command_frames": can.frames_tx,
        "can_feedback_frames": can.frames_rx,
        "can_dropped_frames": can.dropped,
        "encoder_feedback_frames": encoder_feedback,
        "fault_checks": fault_checks,
        "unexpected_failures": unexpected[:50],
        "pass": passed,
        "physical_hardware_execution": "UNEXECUTED",
        "limitations": [
            "The PLC, servo drive, motor, encoder and CAN transceivers are simulated; no physical I/O, EMI, grounding, connector wear, drive firmware or STO circuitry is exercised.",
            "The PTY path does exercise Saga UARTDevice termios/select/read/write and the real ModbusRTUMaster parser/CRC path.",
            "The virtual CAN path exercises framing, loss handling and control/feedback separation but is not Linux SocketCAN because CAP_NET_ADMIN is unavailable for creating vcan0.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--period-ms", type=int, default=100)
    ap.add_argument("--output", default=str(ROOT / "validation" / "industrial-hil-sim-0.38.0.json"))
    args = ap.parse_args()
    report = run(args.hours, args.period_ms)
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
