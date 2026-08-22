# Saga Advanced Motion Control Profile 0.47

Status: implementation profile for Saga 0.47.

## 1. Purpose

Saga 0.47 extends the 0.46 precision-machine layer into a common high-performance motion-control surface. The profile keeps the language rules unchanged: control mathematics is ordinary managed Saga state; physical buses and actuators require explicit device authority; the portable numeric surface remains `decimal`; hidden stop/degrade policy is not introduced; and Python/Go implementations must agree on the promoted source surface.

This profile is not a hard-real-time certification. Host Python/Go execution, raw Linux networking, a successful software qualification, or the `@control_tick` source profile do not prove a target's WCET, interrupt latency, PWM edge timing, fieldbus distributed-clock accuracy, functional safety, or absence of allocator calls in generated MCU code.

## 2. FOC current loop

`machine.foc_current(kp_d, ki_d, kp_q, ki_q, resistance, ld, lq, flux, current_limit, voltage_limit, antiwindup_gain)` creates a persistent d/q current controller.

`machine.foc_step(loop, id_ref, iq_ref, ia, ib, ic, electrical_theta_rad, electrical_omega_rad_s, bus_voltage, dt_seconds)` performs Clarke/Park measurement, d/q PI control, PMSM cross-coupling/feed-forward compensation, vector voltage limiting, anti-windup, inverse Park and SVPWM state update. Scalar getters expose measured d/q current, d/q voltage and each duty ratio without requiring a Saga list in a cyclic function.

The API computes duty ratios only. It does not configure ADC trigger phase, dead time, complementary PWM, gate-driver faults, desaturation protection or hardware current trips.

## 3. Integrated encoder state

`machine.encoder_integrated(cpr, gear_ratio, modulus, direction, velocity_alpha)` supports both unbounded incremental counts (`modulus = 0`) and modulo absolute/multi-turn count sources (`modulus > 1`).

`machine.encoder_sample(encoder, raw_count, timestamp_ns)` unwraps modulo transitions and derives filtered velocity from sample timestamps. `machine.encoder_align_absolute` explicitly aligns a raw absolute count to a known mechanical angle. Position and velocity are exposed through scalar getters.

Timestamp quality is part of the input contract. A host timestamp does not become a hardware timestamp merely because it is numerically precise.

## 4. Online system identification

`machine.rls2(forgetting_factor, initial_covariance)` creates a bounded two-parameter recursive least-squares estimator. `machine.rls2_update(estimator, x0, x1, y)` updates the estimate and returns the residual. Scalar getters expose both parameters and the last error.

The algorithm is deterministic and fixed-size. Application code remains responsible for excitation quality, model selection, outlier handling and deciding whether an identified model may influence live control.

## 5. Fixed-horizon MPC

`machine.mpc2(...)` implements a two-state, one-input, fixed-horizon linear model-predictive controller with diagonal state cost, scalar input cost and box input constraints. Horizon is bounded to 1..32 and the projected-gradient iteration count is fixed by the implementation profile.

`machine.mpc2_step` returns one scalar command and retains a warm-start sequence. The common semantic contract is fixed storage at the Saga target level; the hosted reference implementation may allocate host objects internally and therefore is not itself the allocation-free MCU proof.

## 6. Disturbance observation and friction compensation

`machine.disturbance_observer(input_gain, damping, bandwidth_hz)` estimates an additive disturbance in a one-dimensional velocity model. `machine.disturbance_step` updates the low-pass disturbance state.

`machine.friction_compensation(coulomb, viscous, static, stribeck_velocity, velocity, smoothing_velocity)` evaluates an explicit Coulomb + viscous + Stribeck compensation model with a smooth zero crossing. It is feed-forward mathematics, not a stability guarantee.

## 7. Multi-axis synchronization

`machine.axis_sync(axis_count, correction_gain, correction_limit, skew_limit)` creates an electronic-gearing synchronizer. Each axis has an explicit ratio and offset. `axis_sync_begin(master_position)` freezes the reference for one update and `axis_sync_correction` returns a bounded scalar correction while recording skew health.

This layer does not silently command a stop when skew is excessive; it exposes health so application/safety policy remains explicit.

## 8. EtherCAT and CAN-FD

Pure EtherCAT datagram construction is available without device authority:

- `machine.ethercat_datagram`
- `machine.ethercat_frame`
- `machine.ethercat_lrw`
- `machine.ethercat_first_datagram_json`

Linux raw-L2 exchange is capability-gated through `machine.ethercat_open`, `machine.ethercat_exchange` and `machine.ethercat_close`.

CAN-FD retains `machine.can_open(interface, true)` and adds explicit `machine.canfd_send(..., brs)` and `machine.canfd_recv`. BRS/ESI are preserved in the frame report. Timestamping is enabled explicitly with `machine.can_timestamping`.

The 0.47 raw adapters provide protocol transport primitives; they are not a complete EtherCAT master with topology discovery, PDO/SDO configuration, Distributed Clocks servo, ENI processing or certified conformance.

## 9. Hardware-timestamped I/O

Linux adapters request `SO_TIMESTAMPING`. A received result reports `timestamp_source` as `hardware`, `software`, `host` or `none`. `hardware` is reported only when a raw hardware timestamp is actually present in the socket control message. Requested hardware timestamping therefore never upgrades fallback time by assertion.

Timestamped CAN-FD and EtherCAT reports use integer nanoseconds so control software can preserve acquisition order and latency evidence without converting through binary floating point.

## 10. MCU/RTOS allocation-free source profile

A function annotated `@control_tick` enters the 0.47 source profile. Both common implementations reject, inside that function:

- Saga list construction;
- closures or nested functions;
- `async`/`await`, task groups and dynamic task-pool work;
- `using`, `defer` and resource moves;
- exception control flow;
- `while` loops;
- `for` loops whose range bounds are not integer literals;
- known blocking receive/exchange APIs such as CAN-FD receive and EtherCAT exchange.

This is a source-level guarantee, not a target binary guarantee. A conforming MCU/RTOS backend claiming allocation-free execution must additionally demonstrate that the lowered control tick performs no allocator calls, uses preallocated state/scratch storage, has bounded loops and avoids blocking I/O.

## 11. Capability boundary

FOC, estimation, MPC, observer, friction, synchronization and EtherCAT frame construction require no physical-device capability. Raw CAN/EtherCAT/device operations remain capability-gated. This keeps simulation and control design reusable while making the moment code can affect real hardware explicit.

## 12. Conformance

A common implementation claiming the 0.47 profile must demonstrate:

1. FOC current-loop numerical and voltage-limit behavior;
2. incremental/absolute encoder unwrap and timestamped velocity behavior;
3. RLS convergence on a known two-parameter model;
4. bounded MPC command behavior;
5. disturbance-observer and friction-model sanity;
6. multi-axis electronic gearing and skew reporting;
7. EtherCAT datagram encoding/decoding parity;
8. CAN-FD/timestamped hardware APIs present behind device capability;
9. identical `@control_tick` acceptance/rejection in Python and Go;
10. at least one identical advanced-motion Saga source executed by both implementations.
