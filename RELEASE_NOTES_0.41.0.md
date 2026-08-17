# Saga 0.41.0 — Advanced Drone + Vision + Communications

## Added

- Quintic minimum-jerk 3D trajectories.
- Generic 4/6/8-rotor control allocation with explicit disabled-rotor isolation; disabled actuators are commanded to zero and unresolved demand is returned as residual.
- MAVLink sequence/loss monitoring, redundant-link de-duplication, token-bucket rate shaping, and TIMESYNC message 111 support.
- `vision` module: guarded OpenCV capture, OpenCV-DNN ONNX inference, YOLO v5/v8-style output post-processing and NMS, HSV region recognition, target tracking, JPEG/resize, pixel-to-camera ray and quaternion ray transforms.
- Independent Go geometry/tracking support with explicit DNN-unavailable reporting when no OpenCV adapter is present.

## Validation

The final source-bound qualification reports Drone/Vision/Comms 18/18, Python↔Go 48/48, module 14/14, Native Runtime 10/10, Native Codegen 17/17, Python self-conformance 48/48 and Go self-conformance 48/48. A generated ONNX identity network is loaded and executed through OpenCV DNN; a generated AVI is read through VideoCapture; synthetic imagery and YOLO tensors exercise detection/NMS/tracking.

## Boundary

Automatic RTL/LAND/DISARM policy remains intentionally absent. Saga 0.41 is reviewed as a companion/offboard controller for an established autopilot, not as a qualified sole hard-real-time flight controller. Physical aircraft and physical-camera testing are still unexecuted.