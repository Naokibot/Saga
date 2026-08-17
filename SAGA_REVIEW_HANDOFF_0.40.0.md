# Saga 0.40.0 Reviewer Handoff

Review the release as two separate claims.

1. **Companion/offboard claim:** inspect `saga/stdlib/drone_control.py`, the Go independent implementation, `examples/drone/mavlink_offboard.saga`, and `tools/drone_control_qualification.py`. Confirm MAVLink 82/84/76 field layout, CRC handling, partial-stream parsing, and explicit-only flight mode transitions.
2. **Direct-flight-controller claim:** this release deliberately does not claim it. Review the documented blockers: soft-real-time host scheduling, reference estimator, sensor-conditioning/timing gaps, hardware-timed ESC output, and absent physical flight qualification.

The automatic RTL/LAND/DISARM policy from 0.39 must not be reintroduced as an implicit health callback. External autopilot behavior is outside the Saga policy layer.
