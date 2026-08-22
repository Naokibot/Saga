# Precision machine control in Saga 0.46

Saga 0.46 makes the machine-control stack deeper without making normal control code look like a specialist DSL. The new layer fills the gap between the existing basic PID/S-curve tools and the existing advanced LQR/Kalman/CANopen/4 kHz facilities.

## What was added

### Better servo feedback

`machine.pid2` adds the control features normally needed when a basic PID starts becoming awkward: setpoint weighting, derivative-on-measurement, derivative filtering, feed-forward input and back-calculation anti-windup.

This matters on motion systems because a position or velocity command may step suddenly while the measured motion is continuous. Derivative-on-measurement avoids turning the setpoint step itself into a large derivative impulse.

### Lightweight state observation

`machine.alpha_beta` estimates position and velocity using a constant-velocity model. It is intentionally smaller than `machine.kalman` and works well as a readable encoder/resolver front end when the model does not justify a matrix filter.

### Resonance suppression

`machine.notch` provides a reusable biquad notch stage. It can sit between a feedback controller and the actuator command, or on a measured signal, without changing the controller API.

### PMSM/BLDC control math

`machine.clarke`, `machine.park`, `machine.inverse_park`, and `machine.svpwm` make the mathematical core of field-oriented control available directly from Saga. They are algorithm-only primitives. Actual high-frequency gate control remains a job for hardware/MCU/RTOS paths with the required electrical protections.

### Timing budget visibility

`machine.deadline_budget` measures how much host time a section consumes. Unlike a hidden watchdog policy, it reports the fact and lets the Saga program decide what that means.

## A readable composed loop

```saga
use machine

let observer = machine.alpha_beta(0.65, 0.08, 0.0, 0.0)
let velocity = machine.pid2(0.7, 0.2, 0.01, 1.0, 0.004, 8.0, -1.0, 1.0)
let resonance = machine.notch(1000.0, 120.0, 5.0)
let budget = machine.deadline_budget(1000, 650)

machine.budget_begin(budget)
let estimate = machine.alpha_beta_step(observer, measured_position, 0.001)
let ff = machine.motor_feedforward(0.04, 0.12, 0.01, target_velocity, target_acceleration)
let raw = machine.pid2_step(velocity, target_velocity, estimate[1], ff, 0.001)
let command = machine.filter_step(resonance, raw)
let late = machine.budget_end(budget)
```

Nothing in this sequence opens a device or silently changes the machine mode. Physical output is a separate explicit statement.

## Where Saga should be used

For a PC/Linux-class controller, Saga can own motion planning, 100 Hz–4 kHz hosted supervisory loops, drive communication, PLC logic, kinematics, diagnostics and logging. For a high-bandwidth current loop, precision step generation, certified safety reaction, or a deadline that must be bounded under all supported load, use an appropriate MCU/RTOS, drive or safety controller and let Saga supervise it.

This boundary is part of the language design, not a missing marketing claim: readable control software is more valuable when the timing and authority limits are stated precisely.
