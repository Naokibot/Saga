# Saga 0.42.0 — Integrated Autonomy + Advanced Machine Control

Saga is an independent general-purpose programming language with its own grammar/type system, module model, native ABI/compiler/runtime, package tooling, an independent Go implementation, and a self-reproducing SH-3 compiler path.

## 0.42 autonomy

Saga keeps flight policy explicit: the standard `drone` module does **not** automatically select RTL, LAND, DISARM or arm a vehicle from health, link, vision or estimator state.

0.42 adds a MAVLink UDP offboard session for PX4/ArduPilot endpoints, visual-servo commands, timestamped hosted VIO, bounded pose-graph SLAM and multi-drone coordination. A protocol-level takeoff → translate → land E2E runs through real UDP sockets and Saga's MAVLink encode/parse path. Official PX4/ArduPilot SITL execution is reported separately and remains `UNEXECUTED` when those binaries are not installed.

The `vision` profile includes real ONNX DNN execution, an OpenCV-Zoo-compatible YOLOX backend, sparse Lucas-Kanade optical flow and calibrated ArUco solvePnP pose estimation. The `media` profile adds structured GStreamer RTP process control, while the browser SH-3 runtime can attach user-media tracks and create WebRTC data channels.

## Advanced machine control from Saga source

The `machine` profile exposes discrete LQR design, state-space control, linear Kalman filtering, synchronized jerk-limited multi-axis motion, DH robot kinematics/Jacobians/resolved-rate control, PLC scan/TON/process images, CANopen NMT/SDO/PDO and CiA-402 helpers in addition to existing PID/axis/Modbus/CAN/I2C/SPI/UART/PWM/encoder/motor APIs.

A Saga application can compose these supported high-level functions without Python/C/Go application glue. Physical NIC, serial/CAN, camera/GPU, DMA/timer and vendor fieldbus drivers remain runtime/OS/device backends.

## Validation

Final source tree SHA-256: `f925e9417b83ad3cac6f69add270417fbbe7e0417c278cca16fb3dda91a023ec`.

- Language core: **84 tests + 6 subtests PASS**
- Modules/generics/machine/drone/vision/0.42: **80/80 PASS**
- Autonomy stack qualification: **PASS**
- Practical drone qualification: **13/13 PASS**
- Python↔Go differential: **48/48 PASS**
- Module conformance: **14/14 PASS**
- Native Runtime: **10/10 PASS**
- Native Codegen: **17/17 PASS**
- Python self-conformance: **48/48 PASS**
- Go self-conformance: **48/48 PASS**
- SH-3 Stage2 == Stage3 fixed point: **PASS**
- Internal security audit: **0 issues**
- Go full tests and `go vet`: **PASS**

Physical aircraft flight, physical camera, physical industrial machinery, hardware-timed DShot/BDShot and hard-real-time inner-loop stabilization remain separately `UNEXECUTED / NOT QUALIFIED` in the current environment.