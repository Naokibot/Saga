# Saga 0.42 autonomy and advanced machine-control profile

Saga 0.42 exposes the supported high-level autonomy and industrial-control stack directly to Saga programs.

## Autonomy

The `drone` profile provides explicit visual-servo commands, timestamped hosted VIO, bounded pose-graph SLAM, multi-vehicle coordination and a MAVLink UDP session suitable for installed PX4/ArduPilot endpoints. Flight-policy changes remain explicit; the standard module does not automatically arm, choose RTL/LAND, or disarm.

The vision/media profiles provide real OpenCV DNN ONNX execution, an OpenCV-Zoo-compatible YOLOX path, structured GStreamer RTP process control and browser WebRTC media-track/data-channel operations.

## Advanced machine control

Saga source can use LQR design, state-space control, linear Kalman filtering, synchronized jerk-limited multi-axis motion, DH robot kinematics/Jacobians/resolved-rate control, PLC scans and timers, bounded process images, CANopen helpers and CiA-402 state/controlword handling, in addition to the earlier PID/axis/Modbus/CAN/I2C/SPI/UART/PWM/encoder/motor APIs.

`Saga-only` means that application logic and these supported abstractions are written in Saga without user-written Python/C/Go glue. Operating-system/device drivers and physical hardware interfaces remain implementation backends.

`tools/real_sitl_e2e_042.py` is the real-SITL connector for environments that already have an autopilot SITL process installed. The default qualification never promotes a missing external runtime to an executed result.