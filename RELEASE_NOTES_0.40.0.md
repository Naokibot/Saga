# Saga 0.40.0 — Practical Drone Offboard Control

Saga 0.40 removes automatic flight-mode safety policy from the `drone` standard module and focuses the hosted runtime on explicit control plus practical companion/offboard integration.

## Changed

- Removed automatic RTL/LAND/DISARM selection from battery, link, estimator, position, and geofence telemetry.
- `FlightManager` now changes mode only through explicit `drone.set_mode(...)`; health updates remain observable and pre-arm checks remain explicit.
- Added MAVLink common builders for `SET_ATTITUDE_TARGET` (82), `SET_POSITION_TARGET_LOCAL_NED` (84), and `COMMAND_LONG` (76).
- Added MAVLink common telemetry decoding and an incremental stream parser suitable for fragmented UART reads and UDP datagrams.
- Added DShot 16-bit word generation and conventional PWM ESC duty conversion. DShot waveform/timer generation remains board-specific and is not claimed by the hosted runtime.
- Added `examples/drone/mavlink_offboard.saga` showing the guarded Saga UDP transport path.
- Updated the drone project template to describe PX4/ArduPilot companion/offboard control as the practical deployment profile.

## Deployment boundary

Saga 0.40 is reviewed as a candidate companion/offboard controller. It is not qualified as a sole flight controller that directly stabilizes an aircraft and drives ESCs. Hosted soft-real-time scheduling, the reference complementary estimator, lack of a board-specific high-rate sensor pipeline, and lack of hardware-timed DShot output remain blockers for that claim.
