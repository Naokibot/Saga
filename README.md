# Saga 0.41.0 — Advanced Drone + Vision + Communications

Saga is a general-purpose programming language with native/system, industrial machine-control, and drone companion/offboard profiles.

## Drone profile

Saga 0.41 keeps flight-mode changes explicit: the standard `drone` module does not automatically select RTL, LAND, or DISARM from battery, link, estimator, or geofence state.

The practical deployment target remains a **companion/offboard controller** connected to PX4 or ArduPilot over MAVLink. 0.41 adds minimum-jerk 3D trajectories, generic 4/6/8-rotor control allocation with explicit failed-rotor isolation, MAVLink link-loss monitoring, redundant-link de-duplication, token-bucket rate shaping, and TIMESYNC.

The new `vision` profile adds guarded OpenCV camera/video capture, ONNX inference, YOLO-style post-processing/NMS, color-region recognition, target tracking, JPEG/resize helpers, and calibrated pixel-to-camera/body ray transforms. The Python hosted backend runs OpenCV DNN; the independent Go implementation provides geometry/tracking and explicitly reports DNN unavailable without an OpenCV adapter.

Validation: Drone/Vision/Comms 18/18, Python↔Go 48/48, module 14/14, Native Runtime 10/10, Native Codegen 17/17, Python self 48/48, Go self 48/48. Source tree SHA-256: `af73721b17e2f18b5a60b7c7e88ac925f7c5329416bfe30d87c768ac4e0befe9`.

Saga 0.41 is **not qualified as a sole hard-real-time flight controller** that replaces a Pixhawk-class autopilot or directly guarantees motor stabilization. Physical flight and physical-camera qualification remain unexecuted in this environment.