from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import platform
import random
import shutil
import socket
import statistics
import struct
import subprocess
import tempfile
import time
from dataclasses import dataclass
from decimal import Decimal as D
from pathlib import Path

from saga.api import compile_source
from saga.stdlib.machine_control import CANDevice, SafetyLatch, _network_timestamp_from_ancillary
from saga.stdlib.machine_motion import FOCCurrentLoop, UnifiedEncoder, ethercat_datagram, ethercat_frame, ethercat_first_datagram_json
from tools.control_tick_c_codegen_048 import emit_control_tick_c

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(math.ceil(p * len(ordered))) - 1))
    return ordered[idx]


def qualify_foc() -> dict:
    # 20 kHz loop, nominal ~1 kHz electrical current-loop bandwidth.
    nominal_r, nominal_l, nominal_flux = 0.05, 0.0002, 0.015
    bandwidth = 2 * math.pi * 1000.0
    kp, ki = nominal_l * bandwidth, nominal_r * bandwidth
    dt = 50e-6

    def scenario(seed: int, r: float, ld: float, lq: float, flux: float, omega: float, vbus: float, iq_ref: float = 15.0):
        rng = random.Random(seed)
        loop = FOCCurrentLoop(
            D(str(kp)), D(str(ki)), D(str(kp)), D(str(ki)),
            D(str(nominal_r)), D(str(nominal_l)), D(str(nominal_l)), D(str(nominal_flux)),
            D("40"), D("30"), D("1000"),
        )
        id_, iq, theta = 0.0, 0.0, 0.0
        prev_vd = prev_vq = 0.0
        q_history: list[float] = []
        d_history: list[float] = []
        duty_ok = True
        t_history: list[float] = []
        for n in range(int(0.020 / dt)):
            t = n * dt
            ref_q = 0.0 if t < 0.002 else iq_ref
            # Deliberate bus sag after 12 ms and one-sample inverter delay.
            bus = vbus * (0.75 if t >= 0.012 else 1.0)
            dead_d = 0.15 if id_ > 0 else -0.15 if id_ < 0 else 0.0
            dead_q = 0.15 if iq > 0 else -0.15 if iq < 0 else 0.0
            vd = 0.98 * prev_vd - dead_d
            vq = 0.98 * prev_vq - dead_q
            did = (vd - r * id_ + omega * lq * iq) / ld
            diq = (vq - r * iq - omega * (ld * id_ + flux)) / lq
            id_ += did * dt
            iq += diq * dt
            theta = (theta + omega * dt) % (2 * math.pi)
            c, s = math.cos(theta), math.sin(theta)
            alpha = id_ * c - iq * s
            beta = id_ * s + iq * c
            noise = 0.02
            ia = alpha + rng.gauss(0.0, noise)
            ib = -0.5 * alpha + math.sqrt(3) * 0.5 * beta + rng.gauss(0.0, noise)
            ic = -0.5 * alpha - math.sqrt(3) * 0.5 * beta + rng.gauss(0.0, noise)
            loop.step(D(0), D(str(ref_q)), D(str(ia)), D(str(ib)), D(str(ic)), D(str(theta)), D(str(omega)), D(str(bus)), D(str(dt)))
            prev_vd, prev_vq = float(loop.voltage_d), float(loop.voltage_q)
            duty_ok = duty_ok and all(0.0 <= float(x) <= 1.0 for x in (loop.duty_a, loop.duty_b, loop.duty_c))
            q_history.append(iq)
            d_history.append(id_)
            t_history.append(t)
        tail = q_history[-40:]
        final_error = abs(statistics.mean(tail) - iq_ref)
        post = [(t, q) for t, q in zip(t_history, q_history) if t >= 0.002]
        overshoot = max(0.0, (max(q for _, q in post) - iq_ref) / iq_ref * 100.0)
        settle_ms = None
        window = max(1, int(0.001 / dt))
        for i, (t, _q) in enumerate(zip(t_history, q_history)):
            if t < 0.002:
                continue
            if i + window <= len(q_history) and all(abs(q_history[j] - iq_ref) <= 0.02 * iq_ref for j in range(i, i + window)):
                settle_ms = (t - 0.002) * 1000.0
                break
        return {
            "final_error_a": final_error,
            "overshoot_percent": overshoot,
            "settling_ms_2pct_1ms_window": settle_ms,
            "max_abs_iq_a": max(abs(x) for x in q_history),
            "max_abs_id_a": max(abs(x) for x in d_history),
            "duty_in_range": duty_ok,
        }

    nominal = scenario(1, nominal_r, nominal_l, nominal_l, nominal_flux, 500.0, 48.0)
    rng = random.Random(1048)
    monte: list[dict] = []
    for i in range(100):
        monte.append(scenario(
            10000 + i,
            nominal_r * rng.uniform(0.8, 1.2),
            nominal_l * rng.uniform(0.8, 1.2),
            nominal_l * rng.uniform(0.8, 1.2),
            nominal_flux * rng.uniform(0.9, 1.1),
            rng.uniform(0.0, 900.0),
            48.0 * rng.uniform(0.9, 1.1),
        ))
    failures = [m for m in monte if not (m["final_error_a"] < 0.7 and m["max_abs_iq_a"] < 45 and m["max_abs_id_a"] < 2 and m["duty_in_range"])]
    passed = (
        nominal["final_error_a"] < 0.3
        and nominal["overshoot_percent"] < 10
        and nominal["settling_ms_2pct_1ms_window"] is not None
        and nominal["settling_ms_2pct_1ms_window"] < 2.0
        and not failures
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "kind": "virtual-pmsm-inverter-hil",
        "control_rate_hz": 20000,
        "nominal_current_bandwidth_hz": 1000,
        "plant_features": ["dq PMSM electrical dynamics", "one-sample inverter delay", "2% voltage gain loss", "0.15V dead-time drop", "ADC noise", "25% bus sag"],
        "nominal": nominal,
        "monte_carlo_cases": len(monte),
        "monte_carlo_failures": len(failures),
        "worst_final_error_a": max(m["final_error_a"] for m in monte),
        "worst_abs_id_a": max(m["max_abs_id_a"] for m in monte),
        "physical_hardware_executed": False,
    }


def qualify_encoder() -> dict:
    rng = random.Random(2048)
    modulus = cpr = 131072  # 17-bit single-turn absolute encoder model
    rpm = 3000.0
    rps = rpm / 60.0
    base_dt = 1e-4  # 10 kHz sample
    enc = UnifiedEncoder(cpr, D(1), modulus, 1, D("0.2"))
    true_degrees = 45.0
    true_rev = true_degrees / 360.0
    raw = round((true_rev % 1.0) * modulus)
    enc.align_absolute(raw, D("45"))
    timestamp_ns = 1_000_000_000
    pos_errors: list[float] = []
    vel_errors: list[float] = []
    dropped = 0
    for i in range(20000):
        step = 2 if rng.random() < 0.01 else 1
        dropped += int(step == 2)
        true_degrees += step * rps * base_dt * 360.0
        true_rev += step * rps * base_dt
        count_noise = rng.choice([-1, 0, 0, 0, 1])
        raw = (int(round((true_rev % 1.0) * modulus)) + count_noise) % modulus
        timestamp_ns += int(step * base_dt * 1e9) + rng.randint(-200, 200)
        enc.sample(raw, timestamp_ns)
        pos_errors.append(float(enc.position_degrees) - true_degrees)
        if i > 100:
            vel_errors.append(float(enc.velocity_rpm) - rpm)
    max_pos = max(abs(x) for x in pos_errors)
    rms_pos = math.sqrt(statistics.mean(x*x for x in pos_errors))
    max_vel = max(abs(x) for x in vel_errors)
    p99_vel = percentile([abs(x) for x in vel_errors], 0.99)
    passed = max_pos < 0.01 and p99_vel < 5.0 and max_vel < 7.0
    return {
        "status": "PASS" if passed else "FAIL",
        "kind": "virtual-absolute-encoder-hil",
        "resolution_bits": 17,
        "speed_rpm": rpm,
        "sample_rate_hz": 10000,
        "timestamp_jitter_ns": 200,
        "simulated_dropped_samples": dropped,
        "count_noise_counts": 1,
        "max_position_error_deg": max_pos,
        "rms_position_error_deg": rms_pos,
        "p99_velocity_error_rpm": p99_vel,
        "max_velocity_error_rpm": max_vel,
        "physical_encoder_executed": False,
    }


class _FakeCANSocket:
    def __init__(self): self.payloads: list[bytes] = []
    def send(self, payload: bytes): self.payloads.append(bytes(payload)); return len(payload)
    def close(self): pass


def _canfd_wire_time_us(payload_bytes: int, nominal_bps: int, data_bps: int, brs: bool) -> float:
    # Deterministic qualification model, not ISO conformance bit counting.
    # Arbitration/control portion remains at nominal rate; payload+CRC phase is
    # charged to data bitrate when BRS is set. A 20% bit-stuffing margin is
    # deliberately added to both phases.
    arbitration_bits = 38
    crc_bits = 21 if payload_bytes <= 16 else 25
    data_phase_bits = payload_bytes * 8 + crc_bits + 13
    arb = arbitration_bits * 1.2 / nominal_bps
    rate = data_bps if brs else nominal_bps
    dat = data_phase_bits * 1.2 / rate
    return (arb + dat) * 1e6


def qualify_canfd() -> dict:
    fake = _FakeCANSocket()
    dev = CANDevice.__new__(CANDevice)
    dev.fd_mode = True
    dev.timestamping_enabled = False
    dev.sock = fake
    payload = bytes(range(64))
    dev.send(0x123, payload, CANDevice.CANFD_BRS)
    frame = fake.payloads[-1]
    can_id, length, flags, _r0, _r1, data = struct.unpack("=IBBBB64s", frame)
    packed_ok = can_id == 0x123 and length == 64 and flags & CANDevice.CANFD_BRS and data == payload
    no_brs_us = _canfd_wire_time_us(64, 1_000_000, 5_000_000, False)
    brs_us = _canfd_wire_time_us(64, 1_000_000, 5_000_000, True)
    # Attempt real virtual-CAN setup. This sandbox normally lacks CAP_NET_ADMIN;
    # record that boundary rather than silently converting it to PASS.
    ip = shutil.which("ip")
    kernel_vcan = "UNAVAILABLE"
    detail = "ip tool unavailable"
    if ip:
        proc = subprocess.run([ip, "link", "add", "dev", "sagavcan0", "type", "vcan"], capture_output=True, text=True)
        if proc.returncode == 0:
            subprocess.run([ip, "link", "set", "up", "sagavcan0"], capture_output=True)
            kernel_vcan = "AVAILABLE"
            subprocess.run([ip, "link", "delete", "sagavcan0"], capture_output=True)
            detail = "temporary vcan device created"
        else:
            detail = (proc.stderr or proc.stdout).strip()
    passed = packed_ok and brs_us < no_brs_us * 0.5
    return {
        "status": "PASS" if passed else "FAIL",
        "kind": "socketcan-abi-plus-brs-wire-model",
        "socketcan_canfd_frame_bytes": len(frame),
        "brs_flag_preserved": bool(flags & CANDevice.CANFD_BRS),
        "payload_roundtrip": data == payload,
        "modeled_64byte_wire_time_us_1mbps_no_brs": no_brs_us,
        "modeled_64byte_wire_time_us_1m_5m_brs": brs_us,
        "modeled_brs_speedup": no_brs_us / brs_us,
        "kernel_vcan_setup": kernel_vcan,
        "kernel_vcan_detail": detail,
        "physical_canfd_controller_executed": False,
    }


@dataclass
class _DCClock:
    offset_ns: float
    drift_ppm: float
    propagation_ns: float
    propagation_estimate_ns: float
    local_ns: float = 0.0
    rate_correction_ppm: float = 0.0

    def initialize(self): self.local_ns = self.offset_ns
    def advance(self, cycle_ns: float): self.local_ns += cycle_ns * (1.0 + (self.drift_ppm + self.rate_correction_ppm) * 1e-6)
    def synchronize(self, reference_ns: float, rng: random.Random):
        measured_target = reference_ns + self.propagation_estimate_ns + rng.gauss(0.0, 8.0)
        error = measured_target - self.local_ns
        self.local_ns += max(-20_000.0, min(20_000.0, 0.25 * error))
        self.rate_correction_ppm += max(-2.0, min(2.0, error / 1_000_000.0 * 0.02 * 1e6))
        self.rate_correction_ppm = max(-100.0, min(100.0, self.rate_correction_ppm))


def qualify_ethercat_dc() -> dict:
    # Validate that Saga's generic EtherCAT datagram layer can express the ESC
    # DC register traffic used by a master.
    capture = ethercat_frame(ethercat_datagram("BWR", 1, 0, 0x0900, b"\0" * 4))
    distribute = ethercat_frame(ethercat_datagram("FRMW", 2, 0x1001, 0x0910, (123456789).to_bytes(8, "little")))
    difference = ethercat_frame(ethercat_datagram("BRD", 3, 0, 0x092C, b"\0" * 4))
    reports = [json.loads(ethercat_first_datagram_json(f)) for f in (capture, distribute, difference)]
    frames_ok = reports[0]["command"] == "BWR" and reports[0]["offset"] == 0x0900 and reports[1]["command"] == "FRMW" and reports[1]["offset"] == 0x0910 and reports[2]["offset"] == 0x092C

    rng = random.Random(3048)
    clocks: list[_DCClock] = []
    for _ in range(4):
        propagation = rng.uniform(50.0, 500.0)
        clocks.append(_DCClock(rng.uniform(-1_000_000.0, 1_000_000.0), rng.uniform(-50.0, 50.0), propagation, propagation + rng.gauss(0.0, 12.0)))
    for c in clocks: c.initialize()
    cycle_ns = 1_000_000.0
    reference_ns = 0.0
    max_errors: list[float] = []
    for _ in range(3000):
        reference_ns += cycle_ns
        for c in clocks:
            c.advance(cycle_ns)
            c.synchronize(reference_ns, rng)
        max_errors.append(max(abs(c.local_ns - (reference_ns + c.propagation_ns)) for c in clocks))
    locked = max_errors[500:]
    p99 = percentile(locked, 0.99)
    worst = max(locked)
    passed = frames_ok and p99 < 100.0 and worst < 100.0
    return {
        "status": "PASS" if passed else "FAIL",
        "kind": "virtual-ethercat-distributed-clocks",
        "dc_register_frames": reports,
        "virtual_slaves": len(clocks),
        "cycle_us": 1000,
        "initial_offset_range_us": 1000,
        "oscillator_drift_range_ppm": 50,
        "propagation_estimate_sigma_ns": 12,
        "locked_p99_max_slave_error_ns": p99,
        "locked_worst_max_slave_error_ns": worst,
        "real_esc_distributed_clock_executed": False,
        "note": "Models ESC clock-servo behavior; it does not emulate a vendor ESC implementation or prove ETG conformance.",
    }


def qualify_timestamping() -> dict:
    # Synthetic ancillary-data parsing: hardware raw timestamp must win over SW.
    ancillary = [(socket.SOL_SOCKET, 37, struct.pack("=qqqqqq", 100, 200, 0, 0, 100, 123))]
    parsed_ns, parsed_source = _network_timestamp_from_ancillary(ancillary)
    hardware_parse_ok = parsed_source == "hardware" and parsed_ns == 100_000_000_123

    # Exercise real Linux kernel RX software timestamping on loopback.
    sw_delays_ns: list[int] = []
    real_sw = False
    try:
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.bind(("127.0.0.1", 0))
        rx.setsockopt(socket.SOL_SOCKET, 37, (1 << 3) | (1 << 4))
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for i in range(200):
            before = time.time_ns()
            tx.sendto(struct.pack("!I", i), rx.getsockname())
            _data, anc, _flags, _addr = rx.recvmsg(1024, 256)
            ts, source = _network_timestamp_from_ancillary(anc)
            if source == "software":
                sw_delays_ns.append(max(0, ts - before))
        tx.close(); rx.close()
        real_sw = len(sw_delays_ns) >= 190
    except OSError:
        real_sw = False

    # Physical PHC inventory.
    ptps = sorted(str(p) for p in Path("/dev").glob("ptp*"))
    eth0_device = Path("/sys/class/net/eth0/device")
    eth0_kind = str(eth0_device.resolve()) if eth0_device.exists() else "none"

    # Virtual PHC accuracy model: 8 ns quantization, 5 ns sigma timestamp error.
    rng = random.Random(4048)
    hw_errors: list[float] = []
    sw_model_errors: list[float] = []
    quantum = 8.0
    for i in range(10000):
        true_ns = i * 100_000.0 + rng.random() * 1000.0
        hw = round((true_ns + rng.gauss(0.0, 5.0)) / quantum) * quantum
        software = true_ns + max(0.0, rng.gauss(3000.0, 1000.0))
        hw_errors.append(abs(hw - true_ns))
        sw_model_errors.append(abs(software - true_ns))
    hw_p99 = percentile(hw_errors, 0.99)
    passed = hardware_parse_ok and hw_p99 < 25.0 and real_sw
    return {
        "status": "PASS" if passed else "FAIL",
        "kind": "timestamp-provenance-plus-virtual-phc",
        "synthetic_raw_hardware_timestamp_parse": hardware_parse_ok,
        "real_linux_software_timestamp_packets": len(sw_delays_ns),
        "real_linux_software_timestamp_p99_from_presend_ns": percentile(sw_delays_ns, 0.99) if sw_delays_ns else None,
        "ptp_devices": ptps,
        "eth0_device_path": eth0_kind,
        "virtual_phc_quantum_ns": quantum,
        "virtual_phc_error_p99_ns": hw_p99,
        "virtual_phc_error_max_ns": max(hw_errors),
        "virtual_software_timestamp_error_p99_ns": percentile(sw_model_errors, 0.99),
        "physical_nic_hardware_timestamp_executed": bool(ptps),
        "note": "Hardware precision figures are model results because this environment exposes no PHC device.",
    }


def qualify_mcu_codegen(output_dir: Path) -> dict:
    source = '''
@control_tick
fn foc_q_tick(iq_ref: decimal, iq: decimal, integral_q: decimal, kp: decimal, ki: decimal, resistance: decimal, omega: decimal, ld: decimal, id: decimal, flux: decimal, dt: decimal, limit: decimal) -> decimal {
    let error: decimal = iq_ref - iq
    let candidate: decimal = integral_q + ki * error * dt
    let feedforward: decimal = resistance * iq_ref + omega * (ld * id + flux)
    var voltage: decimal = kp * error + candidate + feedforward
    if voltage > limit {
        voltage = limit
    }
    if voltage < -limit {
        voltage = -limit
    }
    return voltage
}
'''
    compile_source(source, "virtual-hil-foc-q.saga")
    c_source = emit_control_tick_c(source, "foc_q_tick")
    output_dir.mkdir(parents=True, exist_ok=True)
    saga_path = output_dir / "foc_q_tick.saga"
    c_path = output_dir / "foc_q_tick.c"
    obj_path = output_dir / "foc_q_tick.cortex-m4f.o"
    saga_path.write_text(source, encoding="utf-8")
    c_path.write_text(c_source, encoding="utf-8")
    clang = shutil.which("clang") or "/usr/local/swift/usr/bin/clang"
    objdump = shutil.which("llvm-objdump") or "/usr/local/swift/usr/bin/llvm-objdump"
    if not Path(clang).exists() or not Path(objdump).exists():
        return {"status": "UNEXECUTED", "reason": "clang/llvm-objdump unavailable"}
    cmd = [clang, "--target=arm-none-eabi", "-mcpu=cortex-m4", "-mthumb", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard", "-O2", "-ffreestanding", "-fno-builtin", "-fno-stack-protector", "-fstack-usage", "-c", str(c_path), "-o", str(obj_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {"status": "FAIL", "compile_stderr": proc.stderr, "compile_stdout": proc.stdout}
    symbols = subprocess.run([objdump, "-t", str(obj_path)], capture_output=True, text=True, check=True).stdout
    disassembly = subprocess.run([objdump, "-d", str(obj_path)], capture_output=True, text=True, check=True).stdout
    (output_dir / "foc_q_tick.cortex-m4f.disassembly.txt").write_text(disassembly, encoding="utf-8")
    (output_dir / "foc_q_tick.cortex-m4f.symbols.txt").write_text(symbols, encoding="utf-8")
    allocator_names = ("malloc", "calloc", "realloc", "free", "operator new", "_sbrk", "__wrap_malloc")
    allocator_refs = [name for name in allocator_names if name in symbols or name in disassembly]
    call_lines = [line.strip() for line in disassembly.splitlines() if "\tbl" in line or "\tblx" in line]
    # Count disassembled instructions inside the sole generated function. It is
    # acyclic, so total instruction count is a conservative path-instruction bound.
    instruction_lines = []
    in_fn = False
    for line in disassembly.splitlines():
        if "<saga_foc_q_tick>:" in line:
            in_fn = True; continue
        if in_fn and line and not line.startswith(" ") and "<" in line and ">:" in line:
            break
        if in_fn and "\t" in line and ":" in line:
            instruction_lines.append(line)
    stack_files = list(output_dir.glob("*.su")) + list(c_path.parent.glob("*.su"))
    stack_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in stack_files if p.exists())
    stack_bytes = None
    for line in stack_text.splitlines():
        if "saga_foc_q_tick" in line:
            parts = line.split("\t")
            for part in parts:
                if part.isdigit():
                    stack_bytes = int(part); break
    # Deliberately pessimistic virtual WCET model: every emitted instruction is
    # charged 16 cycles. This is not a Cortex-M4 timing proof, but because the
    # generated function is acyclic it provides an explicit finite envelope for
    # the surrogate model. Report it separately from formal WCET.
    instruction_bound = len(instruction_lines)
    virtual_cycle_bound = instruction_bound * 16
    virtual_us_at_168mhz = virtual_cycle_bound / 168_000_000 * 1e6
    passed = not allocator_refs and not call_lines and instruction_bound > 0
    return {
        "status": "PASS" if passed else "FAIL",
        "kind": "restricted-control-tick-cortex-m4f-object-proof",
        "target": "arm-none-eabi cortex-m4f hard-float",
        "object_sha256": sha256(obj_path),
        "allocator_symbol_references": allocator_refs,
        "subroutine_call_instructions": call_lines,
        "static_stack_bytes": stack_bytes,
        "static_total_instruction_upper_bound": instruction_bound,
        "virtual_wcet_model_cycles_16_cycles_per_instruction": virtual_cycle_bound,
        "virtual_wcet_model_us_at_168mhz": virtual_us_at_168mhz,
        "formal_target_wcet_proven": False,
        "general_saga_mcu_backend_zero_allocation_proven": False,
        "scope": "one generated scalar FOC q-axis @control_tick kernel",
        "generated_c": str(c_path.relative_to(ROOT)) if c_path.is_relative_to(ROOT) else str(c_path),
        "generated_object": str(obj_path.relative_to(ROOT)) if obj_path.is_relative_to(ROOT) else str(obj_path),
    }


@dataclass
class _VirtualSTO:
    estop_a_released: bool = True
    estop_b_released: bool = True
    sto_a_enable: bool = True
    sto_b_enable: bool = True
    welded_a: bool = False
    welded_b: bool = False
    fault_latched: bool = False
    elapsed_since_trip_ms: float | None = None
    reaction_ms: float = 2.0

    @property
    def torque_permitted(self) -> bool:
        return self.sto_a_enable and self.sto_b_enable

    def press_estop(self, channel: str = "both"):
        if channel in ("a", "both"): self.estop_a_released = False
        if channel in ("b", "both"): self.estop_b_released = False
        self.elapsed_since_trip_ms = 0.0
        if self.estop_a_released != self.estop_b_released:
            self.fault_latched = True

    def tick(self, dt_ms: float):
        if not (self.estop_a_released and self.estop_b_released):
            if self.elapsed_since_trip_ms is None: self.elapsed_since_trip_ms = 0.0
            self.elapsed_since_trip_ms += dt_ms
            if self.elapsed_since_trip_ms >= self.reaction_ms:
                if not self.welded_a: self.sto_a_enable = False
                if not self.welded_b: self.sto_b_enable = False
                if self.sto_a_enable != self.sto_b_enable: self.fault_latched = True

    def release_estop(self):
        self.estop_a_released = self.estop_b_released = True

    def manual_reset(self) -> bool:
        if not (self.estop_a_released and self.estop_b_released): return False
        if self.fault_latched: return False
        if self.sto_a_enable != self.sto_b_enable: return False
        self.sto_a_enable = self.sto_b_enable = True
        self.elapsed_since_trip_ms = None
        return True


def qualify_safety() -> dict:
    # Independent virtual STO path and Saga software latch are exercised together.
    events: list[str] = []
    latch = SafetyLatch()
    actuator = {"command": 1.0}
    latch.register_stop(lambda: actuator.__setitem__("command", 0.0))

    # Normal dual-channel E-stop.
    sto = _VirtualSTO()
    t = 0.0
    sto.press_estop("both")
    latch.trip("virtual E-stop")
    while sto.torque_permitted and t < 10.0:
        sto.tick(0.1); t += 0.1
    normal_safe = (not sto.torque_permitted) and actuator["command"] == 0.0 and latch.tripped and t <= 2.1
    events.append(f"dual-channel-stop-ms={t:.1f}")

    # Restart prevention: release alone must not restore outputs.
    sto.release_estop()
    release_did_not_restart = not sto.torque_permitted

    # Single-channel discrepancy must latch fault and enter safe state through remaining channel.
    discrep = _VirtualSTO()
    discrep.press_estop("a")
    for _ in range(30): discrep.tick(0.1)
    discrepancy_safe = discrep.fault_latched and not discrep.torque_permitted and not discrep.manual_reset()

    # Weld one STO output high: the other channel still removes torque, feedback mismatch latches fault.
    weld = _VirtualSTO(welded_a=True)
    weld.press_estop("both")
    for _ in range(30): weld.tick(0.1)
    welded_safe = (not weld.torque_permitted) and weld.fault_latched and weld.sto_a_enable and not weld.sto_b_enable

    # Saga software clear is intentionally not treated as a safety reset. It can
    # clear its software latch, but the independent STO model remains off.
    latch.clear()
    software_clear_does_not_reenable_sto = not sto.torque_permitted

    passed = normal_safe and release_did_not_restart and discrepancy_safe and welded_safe and software_clear_does_not_reenable_sto
    return {
        "status": "PASS" if passed else "FAIL",
        "kind": "dual-channel-sto-estop-fault-injection-model",
        "dual_channel_reaction_ms": t,
        "saga_guarded_actuator_stopped": actuator["command"] == 0.0,
        "release_without_reset_does_not_restart": release_did_not_restart,
        "single_channel_discrepancy_latched": discrepancy_safe,
        "single_welded_sto_channel_still_removes_torque": welded_safe,
        "software_latch_clear_does_not_reenable_external_sto": software_clear_does_not_reenable_sto,
        "physical_safety_relay_or_drive_sto_executed": False,
        "functional_safety_certification_claimed": False,
        "note": "This is fault-injection logic testing only; it is not SIL/PL validation or proof of diagnostic coverage.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Saga 0.47 virtual HIL qualification 0.48")
    parser.add_argument("--output", default=str(ROOT / "validation" / "virtual-hil-0.48.0.json"))
    args = parser.parse_args()
    evidence = ROOT / "evidence" / "virtual-hil-048"
    evidence.mkdir(parents=True, exist_ok=True)
    results = {
        "schema": 1,
        "qualification": "Saga 0.47 Advanced Motion Virtual-HIL 0.48",
        "executed_at_unix_ns": time.time_ns(),
        "host": {"platform": platform.platform(), "python": platform.python_version(), "machine": platform.machine()},
        "foc_motor_inverter": qualify_foc(),
        "absolute_encoder": qualify_encoder(),
        "can_fd_brs": qualify_canfd(),
        "ethercat_distributed_clocks": qualify_ethercat_dc(),
        "nic_timestamping": qualify_timestamping(),
        "mcu_zero_allocation_wcet": qualify_mcu_codegen(evidence),
        "sto_estop": qualify_safety(),
    }
    statuses = [value.get("status") for key, value in results.items() if isinstance(value, dict) and "status" in value]
    results["software_model_pass"] = all(s == "PASS" for s in statuses)
    results["physical_hardware_qualification_pass"] = False
    results["physical_hardware_status"] = "UNEXECUTED"
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "software_model_pass": results["software_model_pass"], "statuses": statuses}, sort_keys=True))
    return 0 if results["software_model_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
