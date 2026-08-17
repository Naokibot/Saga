# Saga 0.40.0 — Practical Drone Offboard Control

Saga is a general-purpose programming language with native/system, machine-control and drone-control profiles.

## Drone profile

Saga 0.40 removes automatic RTL/LAND/DISARM policy from the `drone` standard module. Health telemetry is observable, but flight-mode changes are explicit application commands.

The practical deployment target is a **companion/offboard controller** connected to an established autopilot such as PX4 or ArduPilot using MAVLink. Saga provides quaternion/rate/position control primitives, MAVLink 2 common offboard messages, stream parsing, DroneCAN helpers, mission/geofence primitives, and guarded UDP/UART transports.

Saga 0.40 is **not qualified as a sole flight controller** that directly stabilizes an aircraft and drives ESCs. The hosted runtime is soft real-time; the built-in estimator is a reference/SITL estimator; DShot support generates a protocol word but not a hardware-timed DMA waveform.

The complete source, tests, specifications and validation tooling are being added to this repository from the reviewed 0.40 release tree.
