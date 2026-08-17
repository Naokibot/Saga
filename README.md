# Saga 0.41.0 — Independent Language + Drone, Vision and Communications

Saga is a general-purpose programming language with its own grammar, parser/type system, module model, native ABI/compiler/runtime, package tooling, an independent Go implementation, and a self-reproducing SH-3 compiler path.

## Independence status

Saga is not a Python DSL: Saga source is parsed and type-checked by Saga front ends and has its own runtime/native code-generation contracts. The language-neutral SH-3 bootstrap VM/launcher builds as strict C11, and the Saga-written compiler reaches an exact Stage2/Stage3 fixed point. Optional host libraries such as OpenCV implement standard-library media backends; they do not define Saga syntax or type semantics.

## Advanced drone control

Saga 0.41 keeps all flight-policy changes explicit: the standard `drone` module does **not** automatically select RTL, LAND, or DISARM from battery, link, estimator, geofence, or vision state.

The drone profile provides quaternion attitude/rate/position control, jerk-limited 3D trajectories, general N-actuator/four-axis control allocation, allocation achieved/residual/saturation reporting, explicit actuator exclusion, MAVLink 2, DroneCAN, DShot/PWM helpers, and MAVLink link-quality observation. The reviewed deployment target remains a companion/offboard controller connected to an established autopilot such as PX4 or ArduPilot; Saga 0.41 is not qualified as a sole hard-real-time flight controller.

## Vision

The `vision` profile provides class-aware NMS, centroid tracking, calibrated pinhole pixel-to-bearing geometry, real OpenCV ArUco recognition, guarded camera/video input, OpenCV-DNN ONNX model loading/inference, and bounded tensor-value export for learned-model post-processing. The independent Go implementation provides the portable NMS/tracking/geometry core; OpenCV-specific camera/ArUco/ONNX parity is not claimed there.

## Communications

Saga supports MAVLink 2 common offboard messages, signing/replay checks, incremental stream parsing, DroneCAN transfer helpers, TCP, UDP and WebSocket transports, socket timeouts, peer-aware UDP receive, and MAVLink sequence/loss/duplicate/out-of-order/latency monitoring.

## Validation

Final source tree SHA-256: `9b8aeab4740ff83db42e089cbc93d7ba13f5c086b470a75621e9687d5db9defc`.

- Drone/Vision/Communications regression: **26/26 PASS**
- Autonomy/Vision/Communication qualification: **12/12 PASS**
- Existing practical drone qualification: **13/13 PASS**
- Python↔Go differential: **48/48 PASS**
- Module conformance: **14/14 PASS**
- Native Runtime qualification: **10/10 PASS**
- Native Codegen qualification: **17/17 PASS**
- Python self-conformance: **48/48 PASS**
- Go self-conformance: **48/48 PASS**
- Internal security audit: **0 issues**
- Go full tests and `go vet`: **PASS**

Executed vision evidence includes generated real pixels recognized as ArUco marker ID 7 and an MJPG AVI frame decoded by OpenCV. Model-specific inference for an arbitrary reviewed ONNX artifact, physical camera capture, physical aircraft flight, hardware-timed DShot/BDShot, and hard-real-time inner-loop stabilization remain explicitly **UNEXECUTED / NOT QUALIFIED**.
