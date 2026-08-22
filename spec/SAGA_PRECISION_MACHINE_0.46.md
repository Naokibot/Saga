# Saga Precision Machine Control Profile 0.46

Status: implementation profile for Saga 0.46.

## 1. Purpose

Saga 0.46 strengthens the portable machine-control surface without turning Saga into a vendor-specific PLC or motion-controller dialect. The profile follows the language's core design rules:

- control code should read like ordinary Saga;
- the default numeric surface remains `decimal`;
- physical I/O remains capability-gated and is never opened implicitly;
- advanced control should be composable from small explicit primitives rather than hidden policy;
- the Python reference implementation and the independent Go implementation must accept the same promoted source surface;
- hosted scheduling remains soft real-time and must not be described as hard real-time.

The 0.46 additions are control algorithms and observability primitives. They do not bypass the 0.44 timing boundary, replace an MCU/RTOS current loop, or replace certified machine-safety hardware.

## 2. Two-degree-of-freedom PID

`machine.pid2(kp, ki, kd, beta, derivative_tau, antiwindup_gain, output_min, output_max)` creates a 2-DOF controller.

`machine.pid2_step(controller, setpoint, measurement, feedforward, dt_seconds)` returns a bounded `decimal` command.

Normative behavior:

1. `beta` is in `0..1` and weights the setpoint only on the proportional path.
2. Derivative action is computed from the negative measurement derivative, not the error derivative. A setpoint step therefore does not create derivative kick by itself.
3. `derivative_tau >= 0`. A zero value disables derivative filtering. A positive value applies a first-order low-pass to the derivative state.
4. `antiwindup_gain >= 0`. Saturation error is fed back into the integrator by back-calculation.
5. The integral contribution is bounded to the configured output interval.
6. `machine.pid2_reset` clears integral and derivative history.

This controller is intended for servo velocity/current supervisory loops where the classic `machine.pid` surface is not expressive enough.

## 3. Motor feed-forward

`machine.motor_feedforward(ks, kv, ka, velocity, acceleration)` evaluates

`ks * direction + kv * velocity + ka * acceleration`.

`direction` is explicit and deterministic: velocity determines direction when non-zero; otherwise acceleration determines it; when both are zero the static term is zero. The function performs no I/O and requires no device capability.

## 4. Alpha-beta observer

`machine.alpha_beta(alpha, beta, initial_position, initial_velocity)` creates an allocation-light constant-velocity observer.

`machine.alpha_beta_step(observer, measurement, dt_seconds)` returns `[position, velocity]`.

`machine.alpha_beta_reset(observer, position, velocity)` replaces the state explicitly.

The observer is useful for encoder/resolver position smoothing and velocity estimation when a full Kalman model is unnecessary. It is not an estimator-health or failover policy.

## 5. Mechanical resonance filtering

`machine.notch(sample_hz, center_hz, q)` creates a second-order digital notch filter. `center_hz` must be below Nyquist and `q` must be positive.

`machine.filter_step(filter, sample)` evaluates a transposed direct-form-II biquad using two persistent states. `machine.filter_reset` returns those states to zero.

The public Saga surface remains `decimal`. Calculation of trigonometric filter coefficients necessarily crosses an approximate transcendental boundary; the resulting finite coefficients are converted back to the implementation's Saga decimal surface before the cyclic state update.

## 6. Field-oriented-control transforms

0.46 promotes the following motor-control math to the common `machine` surface:

- `machine.clarke(ia, ib, ic) -> list[decimal]` returns `[alpha, beta, zero]` using the amplitude-invariant three-phase Clarke transform;
- `machine.park(alpha, beta, theta_rad) -> list[decimal]` returns `[d, q]`;
- `machine.inverse_park(d, q, theta_rad) -> list[decimal]` returns `[alpha, beta]`;
- `machine.svpwm(alpha, beta, bus_voltage) -> list[decimal]` returns three clamped duty ratios in `0..1` using common-mode centering.

Angles are radians. `bus_voltage` must be positive. The functions compute values only: they do not configure PWM timers, dead time, ADC triggering, gate drivers, current-sense amplifiers, or emergency shutdown hardware.

## 7. Deadline-budget observation

`machine.deadline_budget(period_us, budget_us)` creates a hosted timing observer where `0 < budget_us <= period_us`.

- `machine.budget_begin(budget)` starts one measurement.
- `machine.budget_end(budget) -> bool` records elapsed host time and returns whether the configured computation budget was exceeded.
- `machine.budget_stats_json(budget)` reports sample count, violations, last/max elapsed microseconds, period and budget.
- `machine.budget_reset(budget)` clears statistics.

The observer never changes actuator commands or control modes. Policy remains visible in Saga source. This is deliberate: measurement and policy are separate so a programmer can choose whether a violation should log, skip noncritical work, degrade a feature, request a controlled stop, or be ignored during a bench experiment.

## 8. Composition rule

0.46 does not introduce one monolithic `servo_axis(...)` call with hidden state. The intended composition is:

1. trajectory (`s_curve` or `motion_group`),
2. measurement/observer (`encoder`, `alpha_beta`, or `kalman`),
3. feed-forward (`motor_feedforward`),
4. feedback (`pid2`, `state_space`, or `fast_state_space`),
5. optional resonance conditioning (`notch`),
6. explicit output (`motor_write`, `pwm_write`, CANopen/CiA402, Modbus, or an external drive),
7. explicit timing observation (`cyclic_clock`, `deadline_budget`).

This keeps beginner code readable while allowing an experienced controls engineer to replace one layer without replacing the entire program.

## 9. Capability and safety boundary

All algorithms added by this profile are portable calculations and need no physical-device permission. Existing hardware adapters remain denied unless the process receives device capability.

No 0.46 function constitutes a safety-rated stop, Safe Torque Off, emergency stop, limit circuit, or certified watchdog. For machinery capable of hazardous motion, independent hardware safety and an application-appropriate real-time control architecture remain required.

## 10. Conformance

A common implementation claiming the 0.46 Precision Machine Control profile must demonstrate:

- 2-DOF PID saturation, derivative-on-measurement, and anti-windup behavior;
- alpha-beta observer state evolution;
- deterministic notch reset behavior;
- Clarke/Park/inverse-Park/SVPWM numerical sanity;
- deadline-budget state/error behavior;
- static type checking for the promoted native functions;
- at least one identical Saga source program accepted and executed by both the Python reference implementation and the independent Go implementation.
