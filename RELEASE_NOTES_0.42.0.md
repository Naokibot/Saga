# Saga 0.42.0 — Integrated Autonomy + Advanced Machine Control

## Added

- MAVLink UDP offboard session usable with PX4/ArduPilot endpoints, plus a reproducible real-SITL E2E runner.
- Protocol-level E2E flight qualification: takeoff → translate → land over the same MAVLink/UDP path used by real SITL.
- Visual-servo controller with explicit body velocity/yaw-rate output; no automatic mode policy.
- Timestamped hosted VIO and bounded pose-graph SLAM primitives.
- Explicit multi-drone formation/deconfliction planner.
- OpenCV-Zoo-compatible YOLOX ONNX detector, sparse optical-flow velocity, calibrated ArUco PnP pose estimation and a generated real-ONNX detector fixture for forward-execution qualification.
- Structured GStreamer H.264/RTP sender/receiver backend.
- Browser WebRTC media-track and data-channel attachment in the SH-3 browser runtime.
- Discrete LQR gain design, state-space control, linear Kalman filtering, synchronized jerk-limited multi-axis motion.
- DH robot kinematics/Jacobian/resolved-rate control.
- PLC scan/process-image/TON primitives, CANopen NMT/SDO/PDO helpers and CiA-402 state/controlword helpers.
- Reproducible ONNX fixture generator and Saga-only advanced drone/machine examples.

## Review fixes

- Fixed synchronized multi-axis motion to use the actual `JerkLimitedProfile.step()` contract.
- Fixed pose-graph update direction discovered during qualification.
- Completed WebRTC media support: the browser runtime now attaches MediaStream tracks to the peer connection rather than negotiating an empty peer only.
- Kept external SITL/GStreamer availability separate from protocol/API qualification so unavailable binaries are never reported as executed.

## Boundaries

Saga user programs can now express the supported high-level control stack entirely in Saga. Device drivers, kernel scheduling, GPU/video stacks, physical fieldbus masters and hardware-timed PWM/DShot remain backend responsibilities. Official PX4/ArduPilot SITL and GStreamer process execution are only reported `EXECUTED` when the corresponding binaries are actually present. Physical flight and physical machinery remain separately qualified.
