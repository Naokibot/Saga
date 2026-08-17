# Saga 0.42.0 — Integrated Autonomy + Advanced Machine Control

0.42 adds a MAVLink UDP offboard session and real-SITL runner, visual servoing, hosted VIO, bounded pose-graph SLAM, multi-drone coordination, real ONNX object-detector qualification, an OpenCV-Zoo-compatible YOLOX path, sparse optical-flow velocity, calibrated ArUco PnP pose estimation, structured GStreamer RTP process control and browser WebRTC media-track/data-channel support.

The machine profile adds discrete LQR design, state-space control, linear Kalman filtering, synchronized jerk-limited multi-axis motion, DH robot kinematics/Jacobian/resolved-rate control, PLC scan/TON/process images, CANopen NMT/SDO/PDO and CiA-402 helpers. Supported high-level application logic can be written in Saga without Python/C/Go application glue; hardware/OS drivers remain backend responsibilities.

Flight policy remains explicit. No automatic RTL/LAND/DISARM policy was added.

Final source tree SHA-256: `f925e9417b83ad3cac6f69add270417fbbe7e0417c278cca16fb3dda91a023ec`.

Official PX4/ArduPilot SITL and GStreamer process execution are `UNEXECUTED` in the qualification environment because those binaries were not installed. The included ONNX fixture is an actual executable detector graph, but not a pretrained production model; the YOLOX backend is implemented for a separately supplied compatible model asset. Physical flight, physical camera and physical industrial machinery remain separately qualified.