from __future__ import annotations

import json
import socket
import tempfile
import threading
import unittest
from decimal import Decimal as D
from pathlib import Path

from saga.stdlib.autonomy_advanced import (
    MultiDroneCoordinator,
    PoseGraphSLAM,
    VisualInertialOdometry,
    VisualServoController,
)
from saga.stdlib.machine_advanced import (
    CANopen,
    CiA402,
    DHKinematicChain,
    LinearKalmanFilter,
    PLCScanEngine,
    ProcessImage,
    StateSpaceController,
    SynchronizedMotionGroup,
    discrete_lqr_gain,
)
from saga.stdlib.media_streaming import webrtc_browser_recipe_json
from saga.stdlib.vision_control import OpenCVDirectObjectDetector, sparse_optical_flow_velocity_bgr, aruco_pose_bgr


class AutonomyMachine042Tests(unittest.TestCase):
    def test_visual_servo_is_policy_free_and_bounded(self):
        servo = VisualServoController(D(1), D(1), D(2), D(1), D(3), D(2), D(1), D(".01"))
        command = servo.step(500, 300, 640, 480, D(".02"), D(".10"))
        self.assertLessEqual(abs(command["vx"]), D(3))
        self.assertLessEqual(abs(command["vy"]), D(3))
        self.assertLessEqual(abs(command["vz"]), D(2))
        self.assertLessEqual(abs(command["yaw_rate"]), D(1))
        self.assertNotIn("mode", command)

    def test_vio_visual_correction_reduces_position_error(self):
        vio = VisualInertialOdometry()
        vio.imu(D(0), [D(0)] * 3, [D(0)] * 3)
        for i in range(1, 101):
            vio.imu(D(i) / D(100), [D(0)] * 3, [D(".1"), D(0), D(0)])
        before = abs(vio.position[0])
        vio.visual_position([D(0), D(0), D(0)], D(".8"))
        self.assertLess(abs(vio.position[0]), before)
        self.assertEqual(vio.imu_updates, 100)
        self.assertEqual(vio.visual_updates, 1)

    def test_pose_graph_is_bounded_and_anchors_origin(self):
        slam = PoseGraphSLAM(max_nodes=8)
        a = slam.add_pose(0, 0, 0)
        b = slam.add_pose(1.3, 0.2, 0)
        c = slam.add_pose(2.5, 0.2, 0)
        slam.add_constraint(a, b, 1, 0, 0, 1)
        slam.add_constraint(b, c, 1, 0, 0, 1)
        origin = list(slam.poses[0])
        slam.optimize(80, D(".03"))
        self.assertEqual(slam.poses[0], origin)
        self.assertEqual(len(slam.poses), 3)

    def test_multi_drone_planner_reports_conflicts(self):
        coordinator = MultiDroneCoordinator(D(2), D(4))
        coordinator.update(1, [0, 0, -5], [0, 0, 0])
        coordinator.update(2, [1, 0, -5], [0, 0, 0])
        plans = coordinator.plan({1: [10, 0, -5], 2: [10, 3, -5]})
        self.assertEqual(set(plans), {1, 2})
        self.assertTrue(coordinator.conflicts())
        for velocity in plans.values():
            speed2 = sum(float(v) ** 2 for v in velocity)
            self.assertLessEqual(speed2, 16.000001)

    def test_lqr_state_space_kalman(self):
        K = discrete_lqr_gain(
            [[D(1), D(1)], [D(0), D(1)]], [[D(0)], [D(1)]],
            [[D(1), D(0)], [D(0), D(1)]], [[D(1)]], 50,
        )
        self.assertEqual(len(K), 1)
        self.assertEqual(len(K[0]), 2)
        controller = StateSpaceController.create(
            [[D(1), D(1)], [D(0), D(1)]], [[D(0)], [D(1)]], K,
            [[D(1)]], [D(0), D(0)], [-D(5)], [D(5)],
        )
        self.assertEqual(len(controller.command([D(1)])), 1)
        filt = LinearKalmanFilter.create(
            [[D(1)]], [[D(1)]], [[D(".01")]], [[D(".1")]], [D(0)], [[D(1)]],
        )
        filt.predict()
        self.assertGreater(filt.update([D(1)])[0], D(".8"))

    def test_motion_kinematics_plc_canopen_process_image(self):
        group = SynchronizedMotionGroup.create([D(0), D(0)], D(10), D(20), D(100))
        group.retarget([D(5), D(2)])
        step = group.step(D(".01"))
        self.assertEqual(len(step["position"]), 2)

        arm = DHKinematicChain.create([[D(1), D(0), D(0), D(0)], [D(1), D(0), D(0), D(0)]])
        self.assertEqual(len(arm.forward([D(0), D(0)])), 4)
        self.assertEqual(len(arm.resolved_rate([D(0), D(0)], [D(0), D(".1"), D(0)])), 2)

        plc = PLCScanEngine(D(".01"))
        plc.sample_json('{"start":true}')
        self.assertTrue(plc.read("start"))
        self.assertFalse(plc.ton("t", True, D(".02")))
        self.assertTrue(plc.ton("t", True, D(".02")))
        plc.write("motor_enable", True)
        self.assertTrue(json.loads(plc.commit_json())["motor_enable"])

        cob_id, payload = CANopen.sdo_download(0x6040, 0, 1, 15, 2)
        self.assertEqual(cob_id, 0x601)
        self.assertEqual(payload.hex(), "2b4060000f000000")
        self.assertEqual(CiA402.state(0x27), "OPERATION_ENABLED")

        image = ProcessImage.create(8)
        image.write_int(0, 2, False, 1234)
        image.write_bit(31, True)
        self.assertEqual(image.read_int(0, 2, False), 1234)
        self.assertTrue(image.read_bit(31))

    def test_actual_onnx_fixture_executes(self):
        try:
            import numpy as np
        except Exception as exc:  # pragma: no cover - dependency boundary
            self.skipTest(str(exc))
        fixture = Path(__file__).parent / "fixtures" / "tiny_object_detector.onnx"
        detector = OpenCVDirectObjectDetector(fixture, 32, 32, D(".5"), True)
        dark = np.zeros((64, 64, 3), dtype=np.uint8)
        bright = np.full((64, 64, 3), 255, dtype=np.uint8)
        self.assertEqual(detector.detect(dark, ["bright"]), [])
        out = detector.detect(bright, ["bright"])
        self.assertEqual(len(out), 1)
        self.assertGreater(out[0].confidence, D(".9"))

    def test_real_optical_flow_and_aruco_pose_frontend(self):
        try:
            import cv2
            import numpy as np
        except Exception as exc:
            self.skipTest(str(exc))
        prev=np.zeros((160,160,3),dtype=np.uint8)
        for y in range(20,150,30):
            for x in range(20,150,30): cv2.circle(prev,(x,y),3,(255,255,255),-1)
        curr=cv2.warpAffine(prev,np.float32([[1,0,4],[0,1,2]]),(160,160))
        flow=sparse_optical_flow_velocity_bgr(prev,curr,D(100),D(100),D(2),D(".1"))
        self.assertGreaterEqual(flow["tracked"], 10)
        self.assertAlmostEqual(flow["median_du"], 4.0, delta=.25)
        self.assertAlmostEqual(flow["median_dv"], 2.0, delta=.25)

        dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        marker=cv2.aruco.generateImageMarker(dictionary,7,100)
        image=np.full((240,320),255,dtype=np.uint8); image[70:170,110:210]=marker
        pose=aruco_pose_bgr(cv2.cvtColor(image,cv2.COLOR_GRAY2BGR),0,D(".2"),D(300),D(300),D(160),D(120))
        self.assertEqual(len(pose),1); self.assertEqual(pose[0]["id"],7); self.assertGreater(pose[0]["tvec_m"][2],0)

    def test_webrtc_recipe_includes_media_track_path(self):
        recipe = json.loads(webrtc_browser_recipe_json())
        self.assertIn("webrtc.add_media_stream", recipe["operations"])
        self.assertIn("webrtc.create_data_channel", recipe["operations"])
        self.assertEqual(recipe["media"], "media.request_user_media")


if __name__ == "__main__":
    unittest.main()
