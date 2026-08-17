# Saga 0.41.0 Validation

Final source tree SHA-256: `9b8aeab4740ff83db42e089cbc93d7ba13f5c086b470a75621e9687d5db9defc`.

## New 0.41 functionality

- Python drone/vision/communication regression: **26/26 PASS**.
- Autonomy/Vision/Communication qualification: **12/12 PASS**.
  - 3D jerk-limited trajectory and limits
  - six-motor allocation with an explicitly disabled actuator
  - allocation achieved/residual metadata
  - MAVLink link monitoring
  - actual localhost UDP carrying `SET_ATTITUDE_TARGET`
  - NMS/tracking/pinhole geometry
  - actual OpenCV ArUco marker recognition
  - actual OpenCV MJPG frame decoding
  - bounded ONNX tensor-value adapter
  - peer-aware UDP receive
  - OpenCV DNN ONNX backend API availability
- Existing practical drone qualification: **13/13 PASS**.
- Go 0.41 drone/vision/UDP regressions: PASS; `go vet` PASS.

## Independent-language evidence

- Strict C11 SH-3 bootstrap VM build: PASS.
- Strict C11 language-neutral launcher build: PASS.
- SH-3 Stage1 -> Stage2 compiler rebuild: PASS.
- SH-3 Stage2 -> Stage3 compiler rebuild: PASS.
- Stage2 == Stage3 byte-for-byte: PASS.
- Compiler image SHA-256: `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`.
- Python Standard Core self-conformance: **48/48 PASS**.
- Go Standard Core self-conformance: **48/48 PASS**.
- Python<->Go differential conformance: **48/48 PASS**.
- Module conformance: **14/14 PASS**.

## Existing-language/runtime regression

- core language / standard language / natural language: **70 tests PASS**;
- modules / generic relations: **22 tests PASS**;
- ecosystem: **15 tests PASS**;
- full-stack / runtime safety+scale / security profiles: **32 tests PASS**;
- Native Runtime qualification: **10/10 PASS**;
- Native Codegen qualification: **17/17 PASS**;
- machine-control qualification: PASS, physical hardware `UNEXECUTED`;
- internal security audit: PASS, **0 issues**;
- specification review lint: PASS.

## Explicitly unexecuted / not qualified

- physical camera capture: no physical camera attached;
- arbitrary reviewed ONNX-model inference: no reviewed model artifact bundled in the qualification environment;
- physical aircraft flight: no aircraft/autopilot/ESC/propeller test rig attached;
- hardware-timed DShot/BDShot and hard-real-time inner-loop stabilization: not qualified.

ArUco image recognition and video decode are real executed media paths and are distinct from the unexecuted items above.
