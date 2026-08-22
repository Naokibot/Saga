# Saga 0.42.0 Validation

## Completed regression inventories

- Language core: **84 tests + 6 subtests PASS**.
- Modules/generics/machine/drone/vision/0.42: **80/80 PASS**.
- Native runtime/codegen/object: **23/23 PASS**.
- Native aggregate/GC: **14 tests + 4 subtests PASS**.
- Runtime/security selection: **13/13 PASS**.
- Go `test ./...` and `go vet ./...`: **PASS**.
- Python self-conformance: **48/48 PASS**.
- Go self-conformance: **48/48 PASS**.

## 0.42 autonomy evidence

`tools/autonomy_stack_qualification_042.py` executes the same Saga MAVLink/UDP session used by real autopilot endpoints against a deterministic protocol-level emulator and completes **takeoff → translate → land**. It also executes a real ONNX graph through OpenCV DNN, sparse optical flow, calibrated ArUco PnP, visual-servo, hosted VIO, pose-graph SLAM, multi-drone planning, a Node WebRTC media-track/data-channel path, high-level advanced machine control and Saga-only examples.

Official PX4 SITL, official ArduPilot SITL and GStreamer process execution are separately reported `UNEXECUTED` when those binaries are absent; their absence is never converted into real-process PASS. `tools/real_sitl_e2e_042.py` is the executable real-SITL connector for an environment where the autopilot binary is installed.

## Boundaries

- Physical aircraft flight: **UNEXECUTED**.
- Physical camera: **UNEXECUTED**.
- Physical industrial equipment: **UNEXECUTED by the default non-destructive qualification**.
- Hardware-timed DShot/BDShot and hard-real-time flight-controller stabilization: **NOT QUALIFIED**.
- The included ONNX fixture is a real inference graph used to verify the complete runtime path, but it is not a pretrained production detector. The OpenCV Zoo YOLOX-compatible backend is implemented for a separately supplied model asset.
- "Saga-only" means the user control application and supported algorithms/protocol abstractions are written in Saga; OS/kernel/device drivers remain implementation backends.

Source identity is established by `release/source-manifest-0.42.0.json`; all final source-bound JSON evidence must match that manifest.
