# Saga 0.42 Autonomy and Advanced Machine-Control Profile

## Goal

Saga 0.42 removes the need for application authors to write Python/C/Go glue for the supported autonomy and advanced-control algorithms. A Saga program can construct the estimator/controller/planner/protocol objects, execute the control logic and exchange data through the standard modules.

This does **not** mean the language replaces an operating-system driver, a CAN controller, an EtherCAT-capable NIC, a camera driver, a GPU driver or a DMA/timer peripheral. Those remain implementation backends beneath the language runtime, just as they do for other systems languages.

## Drone/offboard stack

- quaternion/rate/position control from earlier releases
- jerk-limited trajectory generation and generic actuator allocation
- explicit visual servoing
- timestamped IMU propagation plus explicit visual/flow correction (hosted VIO)
- bounded 2D pose-graph SLAM
- multi-vehicle state/formation/deconfliction planner
- MAVLink 2 common messages, signing/replay checks and stream parsing
- `MAVLinkOffboardSession` over UDP for PX4/ArduPilot SITL or real autopilot endpoints
- `tools/real_sitl_e2e_042.py` for reproducible heartbeat + setpoint E2E against an installed SITL

Flight policy stays application-controlled. The standard module does not automatically arm, switch to RTL/LAND, or disarm from health/vision/link state.

## Vision

- camera/video capture through the guarded OpenCV backend
- sparse Lucas-Kanade optical flow with explicit metric depth/scale
- calibrated ArUco solvePnP 6DoF marker pose
- real ArUco recognition
- class-aware NMS and centroid tracking
- camera bearing geometry
- generic OpenCV-DNN ONNX execution
- OpenCV Zoo YOLOX preprocessing/grid/stride decode/NMS
- deterministic real-ONNX object-detector fixture for qualification

The qualification fixture is a small real ONNX graph with object-detector-shaped output. It proves model parsing/forward/result conversion; it is not represented as a pretrained production detector. The YOLOX path is compatible with the OpenCV Zoo YOLOX ONNX layout when that model asset is supplied.

## Video communications

- structured GStreamer H.264/RTP camera sender and receiver commands; no shell interpolation
- availability checks that fail closed when GStreamer/webrtcbin is absent
- browser SH-3 runtime `RTCPeerConnection` operations
- `media.request_user_media` → `webrtc.add_media_stream`
- WebRTC data channel creation for telemetry/control signaling
- explicit SDP/ICE operations; signaling transport remains application-selected

## Advanced machine control available from Saga source

- PID, S-curve and supervised axis control
- state-space control
- discrete LQR controller-gain design
- linear Kalman filter
- synchronized multi-axis jerk-limited motion
- serial manipulator standard-DH forward kinematics
- numeric Jacobian and damped resolved-rate control
- PLC-style input sample → logic → output commit scan
- TON timer
- bounded byte/bit process image
- CANopen NMT, expedited SDO upload/download and PDO COB-ID helpers
- CiA-402 controlword/state decoding
- existing Modbus RTU/TCP, CAN/CAN-FD, I2C, SPI, UART, PWM/servo/encoder/motor interfaces

The application-level sequence can therefore be written in Saga only. A particular physical protocol that is not implemented by the runtime (for example a vendor-specific PROFINET stack) is not silently claimed to exist; it requires a backend/adapter.

## Qualification boundary

The release distinguishes four evidence classes:

1. **EXECUTED** — code ran in the current environment.
2. **PROTOCOL E2E** — real sockets/protocol frames ran against the protocol-level emulator.
3. **UNEXECUTED** — API exists, but required external binary/hardware was absent.
4. **NOT QUALIFIED** — physical/hard-real-time claims that need a hardware lab or independent evidence.

The current environment has no PX4/ArduPilot SITL or GStreamer binaries, so official process execution is UNEXECUTED. Node/WebRTC browser-backend logic, OpenCV DNN, OpenCV image/video paths and MAVLink/UDP protocol E2E are executed.
