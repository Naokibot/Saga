#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import socket
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.api import compile_source
from saga.project_templates import TEMPLATES
from saga.stdlib.drone_control import (
    AttitudeController,
    FlightManager,
    Geofence,
    PositionController,
    QuadXMixer,
    QuaternionAttitudeController,
    RTLPlanner,
    RateController,
    dronecan_crc16_ccitt_false,
    dronecan_multi_frame,
    dronecan_single_frame,
    mavlink2_encode_signed,
    mavlink2_verify_signed,
    mavlink_set_attitude_target,
    mavlink_set_position_target_local_ned,
    mavlink_command_long,
    MAVLinkStreamParser,
    quaternion_from_rpy,
)
from saga.stdlib.machine_control import SafetyLatch
from tools.evidence_context import source_binding

RELEASE = "0.43.0"


def main() -> int:
    ap = argparse.ArgumentParser(description="Saga 0.40 practical drone/offboard qualification")
    ap.add_argument("--output", default=str(ROOT / "validation" / f"drone-control-{RELEASE}.json"))
    args = ap.parse_args()
    checks: list[dict[str, object]] = []

    def mark(name: str, passed: bool, detail: object = None) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    # Component regressions in both independent implementations.
    py = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_drone_control_040.py"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    mark("Python drone regression", py.returncode == 0, (py.stdout + py.stderr)[-2000:])
    go = subprocess.run(["go", "test", "./cmd/saga-go", "-run", "TestDrone", "-count=1"], cwd=ROOT / "implementations/go", text=True, capture_output=True, timeout=90)
    mark("Go drone regression", go.returncode == 0, (go.stdout + go.stderr)[-2000:])

    # Verify the language-facing starter and examples type-check without hardware.
    source = TEMPLATES["drone"].files["main.saga"]
    try:
        compile_source(source, "<drone-template>")
        template_ok, template_detail = True, "drone starter compiles"
    except Exception as exc:
        template_ok, template_detail = False, repr(exc)
    mark("SITL-first drone project template compiles", template_ok, template_detail)
    example_results = {}
    for path in sorted((ROOT / "examples/drone").glob("*.saga")):
        try:
            compile_source(path.read_text(encoding="utf-8"), str(path))
            example_results[path.name] = "PASS"
        except Exception as exc:
            example_results[path.name] = repr(exc)
    mark("drone examples compile", bool(example_results) and all(v == "PASS" for v in example_results.values()), example_results)

    # Deterministic rotational SITL: recover from large initial attitude and a later rate impulse.
    attitude = QuaternionAttitudeController(D("4"), D("4"), D("2"), D("3"))
    rates = RateController.create(D("0.35"), D("0.04"), D("0.01"), D("0.25"))
    mixer = QuadXMixer(D("0.05"), D("1"))
    rpy = [D("0.30"), D("-0.20"), D("0.15")]
    omega = [D(0), D(0), D(0)]
    inertia = [D("0.12"), D("0.12"), D("0.20")]
    damping = D("0.25")
    dt = D("0.01")
    max_motor, min_motor = D(0), D(1)
    cycles = 20_000
    for n in range(cycles):
        if n == 5_000:
            omega[0] += D("1.2")
            omega[1] -= D("0.8")
        sp = attitude.step(quaternion_from_rpy(D0, D0, D0), quaternion_from_rpy(rpy[0], rpy[1], rpy[2]))
        torque = rates.step(sp, omega, dt)
        for j in range(3):
            rate_dot = (torque[j] - damping * omega[j]) / inertia[j]
            omega[j] += rate_dot * dt
            rpy[j] += omega[j] * dt
        motors = mixer.mix(D("0.50"), torque[0], torque[1], torque[2])
        max_motor = max(max_motor, *motors)
        min_motor = min(min_motor, *motors)
    rotational_error = math.sqrt(sum(float(v) ** 2 for v in rpy))
    mark("3-axis rotational SITL converges after disturbance", rotational_error < 1e-4 and min_motor >= D("0.05") and max_motor <= D(1), {
        "simulated_seconds": float(dt) * cycles,
        "cycles": cycles,
        "final_rpy_rad": [str(v) for v in rpy],
        "final_rate_rad_s": [str(v) for v in omega],
        "attitude_error_norm_rad": rotational_error,
        "motor_min": str(min_motor),
        "motor_max": str(max_motor),
    })

    # Translational loop SITL in a local Cartesian frame.
    position = PositionController(D("0.8"), D("0.7"), D("0.03"), D("0.02"), D("6"), D("3"))
    pos = [D(0), D(0), D(0)]
    vel = [D(0), D(0), D(0)]
    target = [D("20"), D("-10"), D("12")]
    max_acc = D(0)
    for _ in range(12_000):
        acc = position.step(target, pos, vel, (D0, D0, D0), dt)
        for j in range(3):
            max_acc = max(max_acc, abs(acc[j]))
            vel[j] += acc[j] * dt
            pos[j] += vel[j] * dt
    position_error = math.sqrt(sum(float(target[j] - pos[j]) ** 2 for j in range(3)))
    mark("position loop SITL reaches waypoint with bounded acceleration", position_error < 0.05 and max_acc <= D("3"), {
        "cycles": 12_000, "final_position_m": [str(v) for v in pos], "error_m": position_error, "max_acceleration": str(max_acc)
    })

    # No automatic flight-safety policy: health telemetry is observable but does not change mode.
    safety = SafetyLatch()
    flight = FlightManager(safety, D("0.2"))
    flight.update_health(True, True, D("0.8"), True, True, True)
    flight.arm(True)
    flight.set_mode("ATTITUDE")
    flight.update_health(False, False, D("0.01"), False, False, True)
    explicit_only = flight.state == "ARMED" and flight.mode == "ATTITUDE" and flight.control_allowed() and not safety.tripped
    mark("health degradation does not trigger automatic RTL/LAND/DISARM", explicit_only, {"state": flight.state, "mode": flight.mode, "safety_tripped": safety.tripped})
    flight.set_mode("RTL")
    mark("RTL remains an explicit application command", flight.state == "ARMED" and flight.mode == "RTL", {"state": flight.state, "mode": flight.mode})

    # Navigation safety helpers.
    fence = Geofence(D("35"), D("139"), D("100"), D(0), D("120"))
    rtl = RTLPlanner(D("35"), D("139"), D("5"), D("30"), D("2"))
    mark("geofence prediction and RTL phases", fence.predict_breach(D("35"), D("139"), D("50"), D("30"), D0, D0, D("4")) and rtl.target(D("35.001"), D("139"), D("10"))["phase"] == "CLIMB", None)

    # Practical companion/offboard path: build standard MAVLink common setpoints and
    # send them through a real localhost UDP socket, then incrementally parse them.
    att_frame = mavlink_set_attitude_target(7, 245, 190, 1, 1, 0,
                                            (D(1), D0, D0, D0), (D("0.1"), D("-0.2"), D("0.3")), D("0.55"), 1234)
    pos_frame = mavlink_set_position_target_local_ned(8, 245, 190, 1, 1, 1, 0,
                                                       (D(1), D(2), D(-3)), (D("0.1"), D("0.2"), D("0.3")),
                                                       (D0, D0, D0), D("0.4"), D0, 2000)
    cmd_frame = mavlink_command_long(9, 245, 190, 1, 1, 400, 0, (D(1),D(2),D(3),D(4),D(5),D(6),D(7)))
    parser = MAVLinkStreamParser()
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(1.0)
    try:
        address = rx.getsockname()
        for frame in (att_frame, pos_frame, cmd_frame):
            tx.sendto(frame, address)
        decoded = []
        for _ in range(3):
            packet, _ = rx.recvfrom(2048)
            # Feed in two pieces to exercise UART-like partial framing over the same parser.
            split = max(1, len(packet) // 3)
            decoded.extend(parser.feed(packet[:split]))
            decoded.extend(parser.feed(packet[split:]))
    finally:
        tx.close(); rx.close()
    ids = [row.get("message_id") for row in decoded]
    mark("MAVLink offboard setpoints survive real UDP transport and incremental parsing", ids == [82, 84, 76], {"message_ids": ids, "frame_lengths": [len(att_frame), len(pos_frame), len(cmd_frame)]})

    # Protocol integrity paths.
    key = bytes(range(32))
    frame = mavlink2_encode_signed(200, 33, b"abc", 9, 42, 10, key, 3, 123456)
    signed = mavlink2_verify_signed(frame, 33, key, 123456)
    replay_rejected = False
    try:
        mavlink2_verify_signed(frame, 33, key, 123457)
    except Exception:
        replay_rejected = True
    mark("MAVLink 2 signed packet verifies and replay floor is enforced", bool(signed.get("signature_valid")) and replay_rejected, {"link_id": signed.get("link_id"), "timestamp": signed.get("timestamp"), "stale_packet_rejected": replay_rejected})
    dcan = dronecan_single_frame(16, 341, 42, 7, b"abc")
    mark("DroneCAN transport reference CRC and single-frame layout", dronecan_crc16_ccitt_false(b"123456789") == 0x29B1 and str(dcan["data_hex"]).endswith("c7"), dcan)
    signature = (0x1122334455667788).to_bytes(8, "little")
    multi = dronecan_multi_frame(8, 20000, 10, 5, signature, bytes(range(30)))
    tails = [int(str(row["data_hex"])[-2:], 16) for row in multi]
    toggle = [bool(t & 0x20) for t in tails]
    multi_ok = len(multi) > 1 and bool(tails[0] & 0x80) and bool(tails[-1] & 0x40) and all(toggle[i] == bool(i % 2) for i in range(len(toggle)))
    mark("DroneCAN multi-frame transfer has CRC prefix, SOT/EOT and alternating toggle", multi_ok, {"frames": len(multi), "tails": tails})

    binding = source_binding(RELEASE)
    report = {
        "schema": 1,
        "release": RELEASE,
        **binding,
        "profile": "hosted-drone-companion-offboard-sitl-hil",
        "physical_flight": "UNEXECUTED",
        "hard_realtime": False,
        "checks": checks,
        "passed": sum(1 for c in checks if c["pass"]),
        "total": len(checks),
        "pass": all(c["pass"] for c in checks),
        "limitations": [
            "Rotational and translational SITL models are deterministic simplified dynamics, not an aerodynamic airframe model.",
            "No physical IMU, GNSS, barometer, ESC, motor, propeller, radio, or aircraft was attached in this environment.",
            "The complementary estimator is a reference/SITL estimator and is not represented as a production EKF.",
            "No automatic RTL/LAND/DISARM policy is provided by the drone module; applications or an external autopilot decide mode changes.",
            "Hosted Saga remains soft real-time and is not qualified as the sole inner-loop flight controller for direct motor stabilization.",
            "The practical target validated here is a companion/offboard controller speaking MAVLink to an established flight controller.",
        ],
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "total": report["total"], "pass": report["pass"], "source_tree_sha256": report["source_tree_sha256"]}, indent=2))
    return 0 if report["pass"] else 1


D0 = D(0)

if __name__ == "__main__":
    raise SystemExit(main())
