# Saga 0.41.0 Review

## Scope

This review asks four questions:

1. Does Saga stand as an independent programming language rather than a Python DSL or wrapper?
2. Can Saga express advanced drone/offboard control?
3. Can Saga perform practical image-recognition pipelines?
4. Can Saga provide the communications needed by drone/robotics applications?

Automatic flight-policy transitions remain intentionally out of scope. Saga 0.41 does not automatically select RTL, LAND or DISARM from battery, estimator, link, geofence or vision state.

## Independent-language assessment

**Assessment: YES, with a clear implementation boundary.**

Saga has its own grammar, lexer/parser, type checker, nominal/module system, diagnostics, package format/tooling, native code generator/ABI/runtime and standard-library contract. It is not parsed as Python and does not translate Saga source into Python source as its language definition.

The independent Go implementation runs/checks the shared Standard Core conformance inventory without embedding the Python implementation. The SH-3 bootstrap VM and launcher compile as strict C11, and the Saga-written compiler rebuilds itself to an exact Stage2/Stage3 fixed point. The regenerated compiler image SHA-256 is `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`.

The boundary should not be overstated: the primary hosted implementation and much tooling are written in Python, the independent implementation is Go, and optional hosted standard-library backends may use operating-system/native libraries. OpenCV implements an optional vision backend, not Saga syntax or language semantics. OpenCV-specific ArUco/ONNX/video support is not independently reimplemented in Go/SH-3 yet.

## Advanced drone-control review

0.41 provides quaternion attitude control, rate PID, position control, jerk-limited three-axis trajectory generation, general N-actuator/four-axis control allocation, explicit actuator exclusion, achieved/residual/saturation reporting, MAVLink 2, DroneCAN and link-quality observation. The allocator deliberately does not detect motor failure automatically and does not trigger a flight-mode transition.

**Assessment:** suitable as a serious companion/offboard-control language candidate. It is not qualified as the sole high-rate flight controller directly stabilizing an aircraft and driving ESC waveforms. Missing evidence includes production estimator/sensor timing, hard-real-time scheduling, hardware-timed DShot/BDShot, physical flight-controller HIL and physical flight testing.

## Vision/image-recognition review

0.41 adds class-aware NMS, centroid tracking, calibrated pinhole pixel-to-bearing geometry, actual OpenCV ArUco recognition, guarded camera/video input, OpenCV DNN ONNX loading/inference and bounded tensor-value export through `vision.onnx_forward_json`.

Review hardening changed the ONNX output limit from a per-output bound to one total inference-output budget (maximum 100,000 values). Actual ArUco recognition and actual video decoding were executed. Arbitrary reviewed-model ONNX inference remains `UNEXECUTED` because no reviewed ONNX model artifact was available in the qualification environment. Physical camera capture is also `UNEXECUTED`.

The independent Go implementation covers NMS, tracking and camera geometry without OpenCV. OpenCV-specific media-backend parity is not claimed for Go 0.41.

## Communications review

Saga supports TCP, UDP, WebSocket, MAVLink 2 framing/common messages/signing/replay handling/stream parsing and DroneCAN. 0.41 adds explicit socket timeout control, MAVLink link-quality observation, peer-aware UDP receive (`host`, `port`, payload) and a 16 MiB UDP receive cap in both hosted Python and independent Go implementations.

Actual localhost UDP delivery of a Saga-generated `SET_ATTITUDE_TARGET` MAVLink 2 frame was executed and decoded during qualification.

## Defects found and fixed

1. Learned inference returned tensor shapes only; bounded tensor values were added.
2. ONNX output budget was per output; changed to one total inference budget.
3. UDP receive discarded the source endpoint; peer-aware receive was added.
4. UDP receive had no practical per-call upper bound; a 16 MiB cap was added.
5. General custom allocator was missing from the Go exposed API/checker; parity was added.
6. Clamped allocation hid lost control authority; achieved/residual/saturation reporting was added.
7. A sample used the wrong allocator call shape; type checking caught and corrected it.

## Remaining boundaries

- physical aircraft flight: UNEXECUTED;
- physical camera qualification: UNEXECUTED;
- arbitrary reviewed-model ONNX operator/accuracy qualification: UNEXECUTED;
- hard-real-time sole-flight-controller qualification: NOT QUALIFIED;
- newest OpenCV-dependent vision backend not independently implemented in Go/SH-3;
- full current-hosted-stdlib SH-3 qualification was not regenerated as one 0.41 run, although the compiler Stage2/Stage3 fixed point was regenerated directly.

Final source tree SHA-256: `9b8aeab4740ff83db42e089cbc93d7ba13f5c086b470a75621e9687d5db9defc`.
