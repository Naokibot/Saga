# Saga 0.47.0 — Advanced Motion Control Profile

Saga 0.47 extends the machine stack from precision servo mathematics into a common advanced-motion layer shared by the Python reference implementation and the independent Go implementation.

## Added

- persistent FOC d/q current loop with PMSM decoupling/feed-forward, vector voltage limiting, anti-windup, inverse Park and SVPWM duty state;
- unified incremental/modulo-absolute encoder state with unwrap, explicit absolute alignment and timestamp-derived velocity;
- fixed-size two-parameter RLS online system identification;
- bounded two-state/one-input fixed-horizon MPC with box input constraints;
- one-dimensional disturbance observer and explicit Coulomb/viscous/Stribeck friction compensation;
- electronic-gearing multi-axis synchronization with bounded correction and skew-health reporting;
- EtherCAT datagram/frame/LRW codec plus Linux raw-L2 capability-gated exchange;
- CAN-FD BRS-aware send, BRS/ESI receive metadata and timestamped receive;
- hardware/software/host timestamp provenance reporting;
- `@control_tick` MCU/RTOS source profile enforced by both Python and Go checkers;
- a standalone allocation-free profile linter and advanced-motion examples/qualification.

## Boundaries

The hosted Python/Go runtimes remain hosted software runtimes. `@control_tick` forbids dynamic Saga constructs and unbounded/blocking control-flow patterns at the source level, but it is not proof that a future MCU object contains zero allocator calls. EtherCAT raw transport is not a complete master/Distributed-Clocks stack. Physical FOC, PWM timing, real encoders, EtherCAT/CAN-FD hardware, WCET and safety circuitry remain unqualified until exercised on target hardware.
