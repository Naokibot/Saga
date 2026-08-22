# Saga 0.42.0 Review Report

## Overall assessment

Saga remains an independent language and 0.42 substantially closes the gap between "drone/control primitives" and a usable companion-computer autonomy stack. The new high-level industrial-control API also removes the need for user-written host-language glue for the supported algorithms and protocol framing.

## Drone and autonomy review

**Ready as an application/offboard stack:** visual-servo command generation, timestamped hosted VIO, pose-graph SLAM, multi-drone coordination, MAVLink UDP session and explicit setpoint streaming are implemented. A takeoff → translate → land sequence is exercised through real UDP sockets and Saga MAVLink encoding/parsing against a deterministic protocol-level autopilot emulator.

**Not falsely promoted to official SITL evidence:** the current container has neither PX4 nor ArduPilot SITL installed and cannot fetch external binaries. Therefore official PX4/ArduPilot process execution is `UNEXECUTED`. `tools/real_sitl_e2e_042.py` is provided to run the same session against an installed endpoint.

**Still not a sole flight-controller qualification:** hosted VIO/SLAM is useful for companion work but is not represented as EKF2/EKF3/VINS/ORB-SLAM equivalence; hard-real-time inner-loop stabilization and hardware-timed motor output are outside this evidence.

## Vision review

A real pixel front-end is also exercised: sparse Lucas-Kanade flow estimates frame translation and calibrated ArUco corners are converted to a 6DoF marker pose with solvePnP.

An actual ONNX protobuf graph is generated into the test fixture and executed by OpenCV DNN. Dark and bright inputs produce different detector results and the bright input returns a bounded box/confidence. This verifies model load → preprocessing → forward → detector result conversion. The OpenCV Zoo YOLOX layout is also implemented, but a downloaded pretrained production YOLOX asset could not be executed in this network-restricted environment.

## Video review

The GStreamer backend uses structured argv and fails closed when `gst-launch-1.0`/`webrtcbin` are unavailable. Browser WebRTC previously supported negotiation without attaching media; 0.42 adds media-track attachment and data-channel creation. A Node browser-API mock executes two track additions and a telemetry data channel.

## Machine-control review

The Saga standard API now exposes LQR/state-space/Kalman, synchronized motion, robot DH/Jacobian/resolved-rate, PLC scan/timer/process image, CANopen and CiA-402 in addition to existing PID/axis/Modbus/CAN/serial/device interfaces. Saga source examples execute the complete high-level flow without Python/C/Go application glue.

The phrase "Saga only" applies to the **user program and supported control abstractions**. Hardware access still requires runtime/OS/device backends. This is an implementation boundary, not a second programming language exposed to the Saga application.
