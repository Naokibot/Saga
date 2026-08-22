# Saga 0.41.0 — Autonomous Systems, Vision and Communications

Saga 0.41 keeps explicit flight-policy control from 0.40 and adds reusable primitives for higher-level drone/autonomy software.

## Added
- Jerk-limited 3-axis NED trajectory generation.
- General multirotor control allocation with actuator-disable support for HIL/research.
- MAVLink sequence/loss/latency link monitoring.
- `vision` standard module: NMS, centroid tracking, pinhole camera rays, ArUco detection and OpenCV-DNN ONNX model loading/inference.
- Camera capture and video frame extraction through guarded device capability.
- Network socket timeout configuration for communication loops.

## Scope
Saga remains qualified primarily as a companion/offboard controller, not as a sole hard-real-time flight controller. Learned ONNX inference uses the optional OpenCV media backend; the core language, parser, type system, native compiler, runtime and package model do not depend on OpenCV.

## Review hardening
- Control allocation now exposes achieved demand, residual error, saturation and disabled-actuator metadata through `drone.allocation_report_json`.
- ONNX inference now exposes bounded tensor values through `vision.onnx_forward_json`; `max_values` is a total inference-output budget, not a per-output budget.
- UDP receive can retain peer host/port and payload through `net.udp_receive_from_json` for multi-vehicle links.
- UDP receive buffers are capped at 16 MiB per call in the hosted Python and independent Go implementations.
- The Go implementation now exposes custom allocation matrices in addition to Quad-X and has peer-aware UDP receive parity.
