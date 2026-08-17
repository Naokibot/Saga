# Saga 0.43.0 — Fine-Grained Control + Lightweight Runtime Paths

Saga is an independent general-purpose programming language with its own grammar/type system, module model, native ABI/compiler/runtime, package tooling, an independent Go implementation, and a self-reproducing SH-3 compiler path.

## Fine-grained control

Saga 0.43 keeps drone flight policy explicit: the standard library does **not** automatically arm, RTL, LAND, or DISARM from battery, link, estimator, geofence, or vision state.

0.43 adds per-actuator target/min/max/neutral/deadband/slew control, a hosted cyclic clock with jitter/overrun telemetry, independent X/Y/Z velocity/acceleration/jerk trajectory limits, MAVLink attitude setpoints, position batches, and timeout control. Control allocation now caches the topology-dependent projection matrix instead of solving the four-axis system every cyclic update.

The machine profile retains LQR/state-space/Kalman, synchronized multi-axis motion, DH robot kinematics/Jacobian/resolved-rate control, PLC/process images, CANopen/CiA-402, Modbus, CAN/CAN-FD, I2C/SPI/UART/PWM/encoder/motor support. Application/control logic can be written in Saga; physical OS/device drivers remain runtime backends.

## Media and external qualification

The 0.43 environment executed real GStreamer through `libgstreamer-1.0`: `videotestsrc -> VP8 -> RTP`, with real RTP bytes received through an OS UDP socket. The real `webrtcbin` plugin loads, but full GStreamer WebRTC ICE is not claimed because `nicesrc/nicesink` are absent.

Official PX4/ArduPilot SITL binaries and the OpenCV Zoo pretrained YOLOX asset are not locally present, and this execution container blocks outbound binary downloads. Physical camera/drone/servo/PLC/fieldbus devices are also not attached. Those cases remain `UNEXECUTED`; Modbus/CANopen/six-axis machine evidence is explicitly HIL/loopback.

Final source tree SHA-256: `59fdf69e653676cba310b1cd90082f49765640b8026f4e933daaa93e77cf743c`.

Validation highlights: fine-control 7/7, selected drone/machine 65/65, language core 84/84, Python↔Go 48/48, module 14/14, Native Runtime 10/10, Native Codegen 17/17, Python/Go self-conformance 48/48 each, Go tests/vet PASS, internal security audit 0 issues.

Saga hosted control remains **soft real-time**. Physical E-stop/STO/interlocks, deterministic fieldbus masters, DMA/timer waveform generation, and certified safety functions remain separate qualification domains.