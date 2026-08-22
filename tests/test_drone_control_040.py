from __future__ import annotations

import json
import math
import unittest
from decimal import Decimal

from saga import run_source
from saga.stdlib.drone_control import (
    AttitudeController, AttitudeEstimator, DroneControlError, FlightManager, Geofence,
    MissionPlan, PositionController, QuadXMixer, QuaternionAttitudeController, RTLPlanner, RateController,
    dronecan_crc16_ccitt_false, dronecan_multi_frame, dronecan_single_frame, dronecan_single_frame_decode,
    landing_vertical_velocity, quaternion_from_rpy, mavlink2_decode, mavlink2_encode, mavlink2_encode_signed,
    mavlink2_verify_signed, mavlink_heartbeat, MAVLinkStreamParser, dshot_frame, pwm_esc_duty,
    mavlink_set_attitude_target, mavlink_set_position_target_local_ned, mavlink_command_long, mavlink_common_decode,
)
from saga.stdlib.machine_control import SafetyLatch

D = Decimal


class DroneControl040Tests(unittest.TestCase):
    def test_attitude_estimator_level_and_yaw_wrap(self):
        est = AttitudeEstimator(D("0.05"))
        for _ in range(100):
            r, p, y = est.update(D(0), D(0), D("0.1"), D(0), D(0), D("9.81"), D(1), D(0), D(0), D("0.01"))
        self.assertTrue(est.healthy)
        self.assertLess(abs(float(r)), 1e-6)
        self.assertLess(abs(float(p)), 1e-6)
        self.assertTrue(-math.pi <= float(y) <= math.pi)

    def test_cascaded_attitude_and_rate_controller(self):
        att = AttitudeController(D("4"), D("4"), D("2"), D("3"))
        rates = att.step([D("0.2"), D("-0.1"), D("0.3")], [D(0), D(0), D(0)])
        self.assertEqual(len(rates), 3)
        rate = RateController.create(D("0.5"), D("0.1"), D("0.01"), D("0.4"))
        torque = rate.step(rates, [D(0), D(0), D(0)], D("0.01"))
        self.assertTrue(all(D("-0.4") <= x <= D("0.4") for x in torque))

    def test_quaternion_attitude_controller_shortest_rotation(self):
        ctl = QuaternionAttitudeController(D("4"), D("4"), D("2"), D("3"))
        target = quaternion_from_rpy(D("0.2"), D("-0.1"), D("0.3"))
        current = quaternion_from_rpy(D(0), D(0), D(0))
        rates = ctl.step(target, current)
        self.assertEqual(len(rates), 3)
        self.assertTrue(all(abs(v) <= D("3") for v in rates))
        negated = tuple(-v for v in target)
        self.assertEqual(ctl.step(negated, current), rates)

    def test_position_controller_bounded_acceleration(self):
        ctl = PositionController(D("1"), D("0.8"), D("0.05"), D("0.01"), D("5"), D("3"))
        accel = ctl.step([D("10"), D(0), D("2")], [D(0), D(0), D(0)], [D(0), D(0), D(0)], [D(0), D(0), D(0)], D("0.02"))
        self.assertEqual(len(accel), 3)
        self.assertTrue(all(abs(x) <= D("3") for x in accel))

    def test_quad_x_mixer_desaturates(self):
        mix = QuadXMixer(D("0.05"), D("1"))
        outputs = mix.mix(D("0.7"), D("0.4"), D("0.3"), D("0.2"))
        self.assertEqual(len(outputs), 4)
        self.assertTrue(all(D("0.05") <= x <= D("1") for x in outputs))
        neutral = mix.mix(D("0.5"), D(0), D(0), D(0))
        self.assertEqual(neutral, [D("0.5")] * 4)

    def test_geofence_and_predictive_breach(self):
        fence = Geofence(D("35"), D("139"), D("100"), D("0"), D("120"))
        self.assertTrue(fence.contains(D("35"), D("139"), D("50")))
        self.assertFalse(fence.contains(D("35.01"), D("139"), D("50")))
        self.assertTrue(fence.predict_breach(D("35"), D("139"), D("50"), D("30"), D(0), D(0), D("4")))

    def test_mission_progression(self):
        mission = MissionPlan()
        mission.add(D("35"), D("139"), D("10"), D("2"), D("0.1"))
        mission.add(D("35.00001"), D("139"), D("12"), D("2"), D(0))
        self.assertEqual(mission.update(D("35"), D("139"), D("10"), D("0.05")), "hold")
        self.assertEqual(mission.update(D("35"), D("139"), D("10"), D("0.05")), "advance")
        self.assertEqual(mission.update(D("35.00001"), D("139"), D("12"), D("0.01")), "complete")
        self.assertTrue(mission.complete)

    def test_flight_manager_uses_only_explicit_mode_transitions(self):
        safety = SafetyLatch()
        manager = FlightManager(safety, D("0.2"))
        with self.assertRaises(DroneControlError):
            manager.arm(True)
        manager.update_health(True, True, D("0.8"), True, True, True)
        manager.arm(True)
        self.assertTrue(manager.flight_allowed())
        self.assertEqual(manager.mode, "ATTITUDE")
        # Health changes are observations only. Saga 0.40 has no automatic
        # battery/link/geofence/estimator mode transition.
        manager.update_health(False, False, D("0.01"), False, False, False)
        self.assertEqual(manager.state, "ARMED")
        self.assertEqual(manager.mode, "ATTITUDE")
        manager.set_mode("RTL")
        self.assertEqual(manager.mode, "RTL")
        self.assertTrue(manager.control_allowed())
        manager.disarm("operator command")
        self.assertEqual(manager.state, "DISARMED")
        self.assertEqual(manager.last_reason, "operator command")

    def test_rtl_and_landing_profile(self):
        rtl = RTLPlanner(D("35"), D("139"), D("5"), D("30"), D("2"))
        self.assertEqual(rtl.target(D("35.001"), D("139"), D("10"))["phase"], "CLIMB")
        self.assertEqual(rtl.target(D("35.001"), D("139"), D("35"))["phase"], "RETURN")
        self.assertEqual(rtl.target(D("35"), D("139"), D("20"))["phase"], "DESCEND")
        self.assertEqual(rtl.target(D("35"), D("139"), D("5.2"))["phase"], "LAND")
        self.assertEqual(landing_vertical_velocity(D("10"), D("1.5"), D("2"), D("0.4")), D("-1.5"))
        self.assertEqual(landing_vertical_velocity(D("1"), D("1.5"), D("2"), D("0.4")), D("-0.4"))

    def test_dronecan_single_frame_and_crc_reference(self):
        self.assertEqual(dronecan_crc16_ccitt_false(b"123456789"), 0x29B1)
        encoded = dronecan_single_frame(16, 341, 42, 7, b"abc")
        self.assertEqual(encoded["can_id"], (16 << 24) | (341 << 8) | 42)
        raw = bytes.fromhex(str(encoded["data_hex"]))
        self.assertEqual(raw[-1], 0xC7)
        decoded = dronecan_single_frame_decode(int(encoded["can_id"]), raw)
        self.assertEqual(decoded["payload_hex"], b"abc".hex())
        self.assertEqual(decoded["transfer_id"], 7)

    def test_dronecan_multiframe_crc_and_toggle_sequence(self):
        signature = bytes.fromhex("8877665544332211")
        payload = b"0123456789abcdef"
        frames = dronecan_multi_frame(8, 20000, 10, 5, signature, payload)
        self.assertGreater(len(frames), 1)
        data = [bytes.fromhex(str(f["data_hex"])) for f in frames]
        self.assertTrue(data[0][-1] & 0x80)
        self.assertFalse(data[0][-1] & 0x40)
        self.assertTrue(data[-1][-1] & 0x40)
        self.assertEqual([bool(d[-1] & 0x20) for d in data[:3]], [False, True, False])
        stream = b"".join(d[:-1] for d in data)
        expected_crc = dronecan_crc16_ccitt_false(signature + payload)
        self.assertEqual(stream[:2], expected_crc.to_bytes(2, "little"))
        self.assertEqual(stream[2:], payload)

    def test_mavlink_heartbeat_and_crc(self):
        frame = mavlink_heartbeat(7, 1, 1, 2, 3, 0x81, 0, 4)
        info = mavlink2_decode(frame, 50)
        self.assertEqual(info["message_id"], 0)
        self.assertEqual(info["sequence"], 7)
        self.assertEqual(info["payload_len"], 9)
        damaged = bytearray(frame); damaged[10] ^= 1
        with self.assertRaises(DroneControlError):
            mavlink2_decode(bytes(damaged), 50)

    def test_mavlink_v2_signed_roundtrip_and_replay_guard(self):
        key = bytes(range(32))
        frame = mavlink2_encode_signed(200, 33, b"abc", 9, 42, 10, key, 3, 123456)
        info = mavlink2_verify_signed(frame, 33, key, 123456)
        self.assertTrue(info["signature_valid"])
        self.assertEqual(info["link_id"], 3)
        with self.assertRaises(DroneControlError):
            mavlink2_verify_signed(frame, 33, key, 123457)
        bad = bytearray(frame); bad[-1] ^= 1
        with self.assertRaises(DroneControlError):
            mavlink2_verify_signed(bytes(bad), 33, key, 0)

    def test_generic_mavlink_frame(self):
        frame = mavlink2_encode(300, 77, b"payload", 255, 250, 200)
        self.assertEqual(mavlink2_decode(frame, 77)["payload_hex"], b"payload".hex())

    def test_common_mavlink_offboard_builders_and_stream_parser(self):
        att = mavlink_set_attitude_target(7, 42, 191, 1, 1, 0,
            [D(1), D(0), D(0), D(0)], [D(0), D(0), D(0)], D("0.5"), 1234)
        self.assertEqual(att[7], 82)
        self.assertEqual(len(att), 51)
        pos = mavlink_set_position_target_local_ned(8, 42, 191, 1, 1, 1, 0,
            [D(1), D(2), D(-3)], [D("0.1"), D("0.2"), D("0.3")], [D(0), D(0), D(0)], D("0.4"), D("0.05"), 1250)
        self.assertEqual(pos[7], 84)
        self.assertEqual(len(pos), 65)
        cmd = mavlink_command_long(9, 42, 191, 1, 1, 400, 0, [D(1), D(0), D(0), D(0), D(0), D(0), D(0)])
        self.assertEqual(cmd[7], 76)
        self.assertEqual(len(cmd), 45)
        parser = MAVLinkStreamParser()
        self.assertEqual(parser.feed(att[:10]), [])
        messages = parser.feed(att[10:] + pos)
        self.assertEqual([m["message_id"] for m in messages], [82, 84])
        self.assertTrue(all(m["known"] for m in messages))

    def test_common_mavlink_telemetry_decode(self):
        import struct
        payload = struct.pack("<I6f", 5000, 1.5, -2.0, -10.0, 0.1, 0.2, 0.3)
        frame = mavlink2_encode(32, 185, payload, 3, 1, 1)
        decoded = mavlink_common_decode(frame)
        self.assertEqual(decoded["message_id"], 32)
        self.assertAlmostEqual(decoded["fields"]["x"], 1.5)
        parser = MAVLinkStreamParser()
        messages = parser.feed(b"noise" + frame)
        self.assertEqual(messages[0]["fields"]["z"], -10.0)
        self.assertEqual(parser.dropped_bytes, 5)

    def test_esc_protocol_helpers(self):
        self.assertEqual(dshot_frame(D(0), False), 0)
        word = dshot_frame(D("0.5"), True)
        self.assertGreater(word, 0)
        packet = word >> 4
        checksum = word & 0xF
        x = packet
        expected = 0
        for _ in range(3):
            expected ^= x
            x >>= 4
        self.assertEqual(checksum, expected & 0xF)
        self.assertEqual(pwm_esc_duty(D("0.5"), D(1000), D(2000), D(2500)), D("0.6"))

    def test_saga_surface(self):
        out: list[str] = []
        run_source('''
use machine
use drone
let safety = machine.safety_latch()
let flight = drone.flight_manager(safety, 0.2)
drone.health_update(flight, true, true, 0.8, true, true, true)
drone.arm(flight, true)
print(drone.flight_allowed(flight))
let mixer = drone.quad_x_mixer(0.05, 1.0)
print(len(drone.mix_quad_x(mixer, 0.5, 0.0, 0.0, 0.0)))
let fence = drone.geofence(35.0, 139.0, 100.0, 0.0, 120.0)
print(drone.geofence_contains(fence, 35.0, 139.0, 10.0))
let rtl = drone.rtl(35.0, 139.0, 5.0, 30.0, 2.0)
print(len(drone.rtl_target_json(rtl, 35.001, 139.0, 10.0)) > 10)
let dcan = drone.dronecan_single_frame_json(16, 341, 42, 7, machine.bytes_from_hex("616263"))
print(len(dcan) > 10)
let hb = drone.mavlink_heartbeat(1, 1, 1, 2, 3, 0, 0, 4)
print(len(hb) > 12)
''', output=out.append)
        self.assertEqual(out, ["true", "4", "true", "true", "true", "true"])


if __name__ == "__main__":
    unittest.main()
