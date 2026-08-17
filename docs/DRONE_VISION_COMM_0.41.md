# Saga 0.41: Drone, Vision and Communications Profile

Saga 0.41 extends the companion/offboard profile without adding automatic flight-policy decisions. Link, battery, estimator and vision state may be observed by an application, but the standard library does not automatically select RTL, LAND or DISARM.

## Advanced drone control

The `drone` module contains quaternion attitude control, angular-rate PID, position control, jerk-limited 3D trajectory generation, Quad-X mixing and a general control allocator. The allocator can exclude an actuator when the application explicitly requests it, which is useful for HIL/research and degraded-control experiments. It is not an automatic motor-failure detector.

For practical deployment, Saga is intended to generate high-level/offboard setpoints for a dedicated autopilot. The hosted runtime is not qualified as the sole high-rate stabilization firmware.

## Vision

The `vision` module provides class-aware NMS, centroid tracking, pinhole-camera bearing conversion and ArUco fiducial recognition. `video.open`/`video.read_frame` provide decoded frames and `video.open_camera` provides capability-gated physical camera input when a camera is available.

`vision.onnx_load` uses the optional OpenCV DNN backend to load ONNX models. `vision.onnx_forward_json` exposes a bounded total number of output tensor values together with shape/truncation metadata. The language core does not depend on OpenCV. Model-specific inference compatibility depends on the operators/backend supported by the installed OpenCV build and must be qualified with the exact deployment model.

## Communications

Saga supports MAVLink 2 framing/common offboard messages, signing/replay checks, stream parsing, DroneCAN transfer helpers, TCP, UDP and WebSocket networking. `net.set_timeout_ms` lets long-running communication loops use bounded socket waits. `net.udp_receive_from_json` retains source host/port metadata. `drone.link_monitor` measures MAVLink sequence gaps, duplicates, ordering and latency without changing flight mode automatically.

## Independence boundary

Saga is an independent programming language: it has its own grammar, parser/type system, module format, native ABI/compiler/runtime, package tooling and an independent Go implementation. Optional host libraries such as OpenCV are standard-library backends, not implementations of Saga syntax or semantics.

The SH-3 bootstrap compiler can rebuild itself to an exact Stage2/Stage3 fixed point. That demonstrates compiler self-reproduction for the covered compiler source; it does not mean every newly added hosted vision API has already been reimplemented inside SH-3.

## Review hardening

The 0.41 review fixed three especially important practical gaps: allocation now reports achieved demand/residual/saturation; ONNX inference exports a bounded total number of tensor values rather than shapes only; and peer-aware UDP receive preserves the endpoint needed for multiple vehicles or peers. UDP receive is capped at 16 MiB per call in both hosted Python and independent Go implementations.
