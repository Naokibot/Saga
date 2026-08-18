# Saga Precision Machine Control Profile 0.46

Status: implemented common profile for the Python reference implementation and the independent Go implementation.

## Philosophy

Control mathematics must remain readable and composable. Static contracts reject invalid calls before execution. Physical authority remains explicit. Stateful mathematical controllers are managed values, not move-only device resources.

## Common API

### Two-degree-of-freedom PID

`machine.pid2(kp: float, ki: float, kd: float, beta: float, derivative_tau: float, antiwindup_gain: float, output_min: float, output_max: float) -> native:pid2`

`machine.pid2_step(controller: native:pid2, setpoint: float, measurement: float, feedforward: float, dt_seconds: float) -> float`

`machine.pid2_reset(controller: native:pid2) -> unit`

### Motor feed-forward

`machine.motor_feedforward(ks: float, kv: float, ka: float, velocity: float, acceleration: float) -> float`

### Alpha-beta observer

`machine.alpha_beta(alpha: float, beta: float, initial_position: float, initial_velocity: float) -> native:alpha_beta`

`machine.alpha_beta_step(observer: native:alpha_beta, measurement: float, dt_seconds: float) -> list[float]`

`machine.alpha_beta_reset(observer: native:alpha_beta, position: float, velocity: float) -> unit`

### Resonance notch

`machine.notch(sample_hz: float, center_hz: float, q: float) -> native:biquad`

`machine.filter_step(filter: native:biquad, sample: float) -> float`

`machine.filter_reset(filter: native:biquad) -> unit`

### FOC mathematics

`machine.clarke(ia: float, ib: float, ic: float) -> list[float]`

`machine.park(alpha: float, beta: float, theta_rad: float) -> list[float]`

`machine.inverse_park(d: float, q: float, theta_rad: float) -> list[float]`

`machine.svpwm(alpha: float, beta: float, bus_voltage: float) -> list[float]`

### Hosted execution-budget observer

`machine.deadline_budget(period_us: int, budget_us: int) -> native:deadline_budget`

`machine.budget_begin(budget: native:deadline_budget) -> unit`

`machine.budget_end(budget: native:deadline_budget) -> bool`

`machine.budget_stats_json(budget: native:deadline_budget) -> string`

`machine.budget_reset(budget: native:deadline_budget) -> unit`

## Authority and ownership

Creating and updating controllers, observers, filters, transforms and budget observers requires no device capability. These operations do not touch hardware. Device handles remain governed by the existing machine capability/resource model.

## Timing and safety boundary

This API does not claim hard-real-time gate-driver operation, physical HIL qualification, servo current-loop certification, fieldbus conformance certification, or certified functional safety. `budget_end` never performs an implicit stop or safety transition.
