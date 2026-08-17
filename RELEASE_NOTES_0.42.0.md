# Saga 0.42.0 — Integrated Autonomy + Advanced Machine Control

0.42 adds a MAVLink UDP offboard session and real-SITL runner, visual servoing, hosted VIO, bounded pose-graph SLAM, multi-drone coordination, real ONNX object-detector qualification, OpenCV-Zoo-compatible YOLOX inference, structured GStreamer RTP process control and browser WebRTC media-track/data-channel support.

The machine profile adds discrete LQR design, state-space control, linear Kalman filtering, synchronized jerk-limited multi-axis motion, DH robot kinematics/Jacobian/resolved-rate control, PLC scan/TON/process images, CANopen NMT/SDO/PDO and CiA-402 helpers. Supported high-level application logic can be written in Saga without Python/C/Go application glue; hardware/OS drivers remain backend responsibilities.

Flight policy remains explicit. No automatic RTL/LAND/DISARM policy was added.

Final source tree SHA-256: `e808c2544b3e8bfbf06de5677ec79717d9b1790fb4081970f20fd00b2f46ad60`.

Official PX4/ArduPilot SITL and GStreamer process execution are reported `UNEXECUTED` in the qualification environment because those binaries were not installed. Physical flight, physical camera, physical industrial machinery and hard-real-time motor stabilization remain separately unqualified.