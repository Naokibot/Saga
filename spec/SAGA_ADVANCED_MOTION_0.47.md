# Saga Advanced Motion Control Profile 0.47

Status: implementation profile for Saga 0.47.

## Purpose

Saga 0.47 extends the 0.46 precision-machine layer into a common high-performance motion-control surface. Control mathematics remains ordinary managed Saga state; physical buses and actuators require explicit device authority; hidden stop/degrade policy is not introduced; and Python/Go implementations must agree on the promoted source surface.

## FOC current loop

`machine.foc_current(...)` creates a persistent d/q current controller. `machine.foc_step(...)` performs Clarke/Park measurement, d/q PI control, PMSM cross-coupling/feed-forward compensation, vector voltage limiting, anti-windup, inverse Park and SVPWM state update. Scalar getters expose currents, voltages and duty ratios without requiring list allocation in a cyclic function.

The API computes duty ratios only; ADC trigger phase, dead time, complementary PWM, gate-driver faults and hard current trips remain hardware responsibilities.

## Integrated encoder state

`machine.encoder_integrated(cpr, gear_ratio, modulus, direction, velocity_alpha)` supports unbounded incremental counts and modulo absolute/multi-turn count sources. `machine.encoder_sample` unwraps modulo transitions and derives filtered velocity from timestamps. `machine.encoder_align_absolute` explicitly aligns an absolute count to a known mechanical angle.

## Online identification and MPC

`machine.rls2` is a bounded two-parameter recursive least-squares estimator with fixed-size state. `machine.mpc2` is a two-state, one-input fixed-horizon controller with diagonal state cost, scalar input cost, box input constraints, bounded horizon and fixed projected-gradient iteration count.

## Disturbance, friction and synchronization

`machine.disturbance_observer` estimates additive disturbance in a one-dimensional velocity model. `machine.friction_compensation` evaluates Coulomb + viscous + Stribeck compensation with a smooth zero crossing. `machine.axis_sync` implements explicit-ratio electronic gearing with bounded correction and skew-health reporting; it never hides stop policy.

## EtherCAT / CAN-FD / timestamps

Pure EtherCAT datagram construction is unprivileged. Linux raw-L2 exchange is capability-gated through `machine.ethercat_open/exchange/close`. CAN-FD adds BRS-aware send, BRS/ESI receive metadata and timestamped receive. Timestamp provenance is reported as `hardware`, `software`, `host`, or `none`; hardware is claimed only when raw hardware time is actually present.

These are transport primitives, not a complete EtherCAT master with discovery, PDO/SDO configuration, ENI or Distributed Clocks servo.

## MCU/RTOS allocation-free source profile

A function annotated `@control_tick` rejects Saga list construction, closures/nested functions, async/taskgroup/task-pool work, `using`/`defer`/resource moves, exception control flow, `while`, non-literal range bounds, and known blocking receive/exchange APIs. Python and Go checkers use matching diagnostic IDs.

This is a source-level guarantee. A target backend claiming allocation-free execution must still prove no allocator calls in lowered code, preallocated state/scratch storage, bounded loops, nonblocking I/O and target WCET.

## Capability boundary

FOC, encoder state, identification, MPC, observer, friction, synchronization and EtherCAT frame construction need no device authority. Raw CAN/EtherCAT/device operations remain capability-gated resources.

## Conformance

A 0.47 implementation must demonstrate FOC numerical/voltage-limit behavior; encoder unwrap/alignment and timestamped velocity; RLS convergence; bounded MPC; disturbance/friction sanity; multi-axis gearing/skew; EtherCAT codec parity; CAN-FD/timestamp API presence behind device capability; matching `@control_tick` acceptance/rejection; and at least one advanced-motion Saga source executed by both common implementations.
