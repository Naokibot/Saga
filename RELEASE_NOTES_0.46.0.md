# Saga 0.46.0 — Precision Machine Control Profile

Saga 0.46 deepens machine control without making machine programs a separate dialect. The release adds portable control mathematics and timing observability to the common Python/Go `machine` surface while retaining explicit device authority and the existing hosted soft-real-time boundary.

## Added

- `machine.pid2` / `pid2_step` / `pid2_reset`: 2-DOF PID with proportional setpoint weighting, derivative-on-measurement, derivative filtering, feed-forward input, output limiting and back-calculation anti-windup.
- `machine.motor_feedforward`: explicit `kS + kV + kA` motor feed-forward.
- `machine.alpha_beta` / `alpha_beta_step` / `alpha_beta_reset`: lightweight position/velocity observation for encoders and similar sensors.
- `machine.notch` / `filter_step` / `filter_reset`: second-order resonance-notch filtering.
- `machine.clarke`, `machine.park`, `machine.inverse_park`, `machine.svpwm`: portable PMSM/BLDC field-oriented-control mathematics.
- `machine.deadline_budget` and budget observation functions: hosted computation-budget measurement without hidden control policy.
- Common Python and independent Go checker/runtime support for the complete promoted 0.46 source surface.
- Precision-servo and FOC examples plus a source-bound cross-implementation qualification harness.

## Design

The new functions are deliberately small and composable. Saga does not add a monolithic servo object that silently chooses trajectory, estimation, safety or actuator policy. Programs can combine the existing S-curve/LQR/Kalman/CANopen/4 kHz facilities with the new observer, feed-forward, PID2 and notch stages while keeping every control decision visible in source.

The algorithmic functions require no device capability. Physical CAN/PWM/servo/motor/Modbus access remains separately capability-gated.

## Compatibility and timing boundary

Saga 0.45 language-synthesis semantics and Saga 0.44 hosted 4 kHz control remain compatible. The 0.46 profile does not claim a hard real-time current loop, deterministic physical PWM edge, certified E-stop/STO, or safety-rated watchdog. Such guarantees still require an appropriate drive, MCU/RTOS, FPGA, safety controller and target-specific qualification.
