# Saga 0.41.0 Review Report

## Scope

This review asked four questions:

1. Does Saga stand as an independent programming language rather than a Python DSL or wrapper?
2. Can Saga express advanced drone/offboard control?
3. Can Saga perform practical image-recognition pipelines?
4. Can Saga provide the communications needed by drone/robotics applications?

Automatic flight-policy transitions remain intentionally out of scope. Saga 0.41 does not automatically select RTL, LAND or DISARM from battery, estimator, link, geofence or vision state.

## Independent-language assessment

**Assessment: YES, with a clear implementation boundary.**

Saga has its own grammar, lexer/parser, type checker, nominal/module system, diagnostics, package format/tooling, native code generator/ABI/runtime and standard-library contract. It is not parsed as Python and does not translate Saga source into Python source as its language definition.

Two additional pieces of evidence matter:

- the independent Go implementation runs/checks the shared Standard Core conformance inventory without embedding the Python implementation;
- the SH-3 bootstrap VM and launcher compile as strict C11, and the Saga-written compiler rebuilds itself to an exact Stage2/Stage3 fixed point. The regenerated compiler image SHA-256 is `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`.

The boundary should not be overstated. The primary hosted implementation and much tooling are written in Python, while the independent implementation is Go. Optional hosted standard-library backends use operating-system/native libraries. In particular, ArUco/video/ONNX functionality uses OpenCV in the Python hosted implementation. That dependency does not implement Saga syntax or type semantics, but the newest media backend is not yet independently reimplemented in SH-3 or Go.

## Advanced drone-control review

The existing 0.40 profile already contained quaternion attitude control, rate PID, position control, Quad-X mixing, explicit flight modes, MAVLink 2, DroneCAN and companion/offboard message generation.

0.41 adds:

- jerk-limited three-axis trajectory generation;
- general N-actuator/four-axis minimum-norm control allocation;
- explicit actuator exclusion for HIL/degraded-control experiments;
- allocation reporting with requested/achieved demand, residual error, saturation and disabled-actuator indices;
- MAVLink sequence-gap/duplicate/out-of-order/latency monitoring;
- matching core implementations in Python and Go.

The allocator deliberately does not detect motor failure automatically and does not trigger an automatic flight mode. The application supplies the disabled actuator set.

**Deployment assessment:** suitable as a serious companion/offboard-control language candidate. It is still not qualified as the sole high-rate flight controller that directly stabilizes an aircraft and drives ESC waveforms. Missing evidence for that stronger claim includes production-grade estimator/sensor timing, hard real-time scheduling, hardware-timed DShot/BDShot, real flight-controller HIL and physical flight testing.

## Vision/image-recognition review

0.40 had basic image/video functions but did not provide a coherent recognition pipeline. 0.41 adds a `vision` standard module with:

- class-aware non-maximum suppression;
- centroid tracking with missed-frame aging;
- calibrated pinhole pixel-to-bearing geometry;
- actual OpenCV ArUco fiducial recognition;
- capability-gated physical camera open plus video frame extraction;
- OpenCV DNN ONNX model loading/inference;
- bounded tensor-value export (`vision.onnx_forward_json`) for classification/detection post-processing.

Review defect fixed: the initial ONNX adapter exposed only output shapes, which was not sufficient to implement learned recognition in Saga. The new value-export API exposes a caller-selected **total** value budget (maximum 100,000 values), including shape, total count and truncation state for every output.

Actual ArUco recognition and actual video decoding were executed. A reviewed arbitrary ONNX model artifact was not available in the qualification environment, so model-specific ONNX inference remains `UNEXECUTED`; the OpenCV DNN ONNX backend/API and bounded Saga adapter were verified without inventing a model result. Physical camera capture is also `UNEXECUTED` because no camera is attached.

The independent Go implementation implements NMS, tracking and camera geometry without OpenCV. OpenCV-specific ArUco/ONNX/video backend parity is not claimed for Go 0.41.

## Communications review

Saga already provided TCP, UDP, WebSocket, MAVLink 2 framing/common messages/signing/replay handling/stream parsing and DroneCAN helpers. 0.41 adds or hardens:

- explicit socket timeout control;
- MAVLink link-quality monitoring;
- peer-aware UDP receive (`host`, `port`, payload hex) for multi-vehicle/multi-peer links;
- UDP receive size cap of 16 MiB per call;
- independent Go UDP/timeouts/peer-aware receive parity.

Actual localhost UDP delivery of a Saga-generated `SET_ATTITUDE_TARGET` MAVLink 2 frame was executed and decoded during qualification.

## Defects found and fixed during review

1. **Learned inference returned shapes only.** Added bounded tensor-value export.
2. **ONNX output budget was per output.** Changed to one total inference-output budget.
3. **UDP receive discarded the source endpoint.** Added peer-aware receive API.
4. **Python UDP receive had no practical per-call upper bound.** Added a 16 MiB cap; Go uses the same cap.
5. **General custom allocator was missing from the Go exposed API/checker.** Added parity.
6. **Clamped allocation silently lost requested authority.** Added achieved/residual/saturation report.
7. **One new example used the wrong allocator call shape.** Type checking caught it; the example was corrected.

## Remaining limitations

- no physical aircraft flight in this environment;
- no physical camera qualification;
- no model-specific ONNX accuracy/operator qualification yet;
- no hard-real-time sole-flight-controller qualification;
- newest OpenCV-dependent vision backend is not implemented independently in Go/SH-3;
- full SH-3 kernel/current-hosted-stdlib qualification was not regenerated as one 0.41 run; the compiler Stage2/Stage3 fixed point was regenerated directly.

These limitations are recorded as boundaries, not treated as passing evidence.
