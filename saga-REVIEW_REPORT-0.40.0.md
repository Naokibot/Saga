# Saga 0.40.0 Source Review — Practical Drone Control

## Decision

**Companion/offboard control: READY FOR SITL/HIL AND CONTROLLED PHYSICAL INTEGRATION TESTING.**

**Sole flight-controller / direct ESC stabilization: NOT QUALIFIED.**

The review distinguishes protocol correctness from flightworthiness. Saga can now create and parse the standard MAVLink messages used by external controllers and use its existing UDP/UART transport. That is a credible route to PX4/ArduPilot integration. The current hosted runtime is not a credible replacement for the flight-controller inner loop.

## Requested change: automatic safety removed

The previous automatic mode-transition policy was removed from both the Python reference implementation and the independent Go implementation. `health_update` no longer changes state or mode. `RTL`, `LAND`, and other modes are selected only by explicit `set_mode` calls. The shared machine safety latch remains a manually/external-controlled primitive; it is not driven by drone telemetry policy.

## Defects and gaps found and fixed

1. The Go implementation and checker still exposed the removed failsafe API after the Python change. They were updated and regression-tested.
2. The 0.39 MAVLink layer only had generic framing/heartbeat/signing. Added concrete common-message builders for ids 82, 84 and 76 with correct MAVLink wire field ordering.
3. Added common telemetry decoding and a buffered stream parser so fragmented UART input does not require one complete packet per read.
4. Added a real localhost UDP qualification path rather than validating only in-memory bytes.
5. The old drone starter and example still called automatic failsafe APIs; replaced by explicit mode and offboard examples.
6. ESC helpers now distinguish protocol-word/duty calculation from hardware waveform generation.

## Direct-flight-controller blockers

- hosted soft-real-time scheduling and no hard deadline guarantee for gyro/rate loops;
- no production-grade EKF/state estimator;
- no complete high-rate IMU calibration, bias-estimation, notch and low-pass pipeline;
- no board-specific timestamp synchronization and sensor FIFO/interrupt backend qualified for flight;
- no hardware-timed/DMA DShot waveform backend;
- no physical airframe/ESC/propeller flight qualification.

## Practical offboard capabilities

- `SET_ATTITUDE_TARGET` builder;
- `SET_POSITION_TARGET_LOCAL_NED` builder;
- `COMMAND_LONG` builder;
- MAVLink common decoder + fragmented stream parser;
- guarded UDP via `net.udp_send` and UART via `machine.uart_write`;
- quaternion/rate/position control algorithms available for high-level external control;
- no automatic flight-mode policy in the Saga layer.
