# Saga 0.39.0 — Drone Flight Control Preview

Saga 0.39 makes flight-control development a first-class hosted profile while preserving the 0.35 Native Runtime ABI and the 0.38 incremental GC feature level.

## Added

- `drone` standard module in the Python reference runtime and independent Go runtime.
- Complementary IMU/magnetometer attitude estimator for deterministic SITL and reference use.
- Cascaded flight-control loops: quaternion attitude control as the primary native path, angular-rate PID, position/velocity control, plus a simpler Euler-angle controller for education and deterministic SITL.
- Quad-X motor allocation with output desaturation and bounds.
- Mission waypoint tracking and cylindrical geofence with predictive breach detection.
- Two-tier flight safety: controlled HOLD/RTL/LAND failsafes preserve control authority, while hard DISARM/E-stop paths trip the shared machine safety latch; explicit reset, RTL and landing helpers are included.
- MAVLink 2 packet CRC, signed packet generation/verification, anti-replay timestamp guard, and HEARTBEAT helper.
- DroneCAN classic-CAN broadcast single-frame and multi-frame transfer encoding, tail byte/toggle/transfer-ID handling, data-type-signature CRC-16-CCITT-FALSE support, and single-frame decoding.
- `saga new <name> --template drone` SITL-first starter and drone examples.
- Drone-specific deterministic qualification/SITL tests.

## Safety boundary

This release does not claim a certified autopilot, hard real-time flight control, airworthiness approval, or physical flight qualification. The quaternion controller is intended as the stronger reference path, but the bundled estimator is still a complementary estimator rather than a production EKF. The default drone template does not open motors or ESCs. Real-aircraft integration must use guarded hardware adapters plus independent arming, power, and safety mechanisms.
