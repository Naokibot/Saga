# Precision Machine Control 0.46

Saga 0.46 extends the common `machine` module around three principles: readable control intent, static contracts, and explicit hardware authority.

## Control loop building blocks

```saga
let velocity_ff = machine.motor_feedforward(0.18, 0.012, 0.0014, 30.0, 80.0)
let regulator = machine.pid2(4.0, 18.0, 0.07, 0.65, 0.004, 7.0, -48.0, 48.0)
let estimate = machine.alpha_beta(0.82, 0.12, 0.0, 0.0)
```

`pid2_step` performs proportional set-point weighting, derivative-on-measurement, derivative low-pass filtering, explicit feed-forward, saturation and back-calculation anti-windup.

## FOC math

`machine.clarke`, `machine.park`, `machine.inverse_park`, and `machine.svpwm` are algorithm-only helpers. They do not gain PWM, ADC, gate-driver, motor or network authority.

## Resonance management

`machine.notch(sample_hz, center_hz, q)` creates a stateful second-order notch filter. It uses a transposed Direct Form II implementation and can be reset explicitly.

## Hosted deadline observation

`machine.deadline_budget(period_us, budget_us)` measures periodic work. `budget_end` returns whether the measured section was within budget and `budget_stats_json` exposes deterministic summary fields.

A budget miss is information, not a hidden policy action. Saga does not silently stop a motor, change gains, skip work, or enter a degraded mode.

## Boundary

The 0.46 profile improves hosted precision-control programming. It does not convert a general hosted runtime into a certified hard-real-time safety controller. Physical timing qualification, electrical validation, HIL endurance, gate-driver dead-time, current-sense calibration and safety certification remain hardware/platform responsibilities.
