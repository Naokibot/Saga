# Advanced motion control in Saga 0.47

Saga 0.47 takes the next step after the 0.46 precision-servo layer: a control engineer can now keep the current loop, encoder state, identification, predictive control, disturbance/friction compensation and multi-axis correction in one readable Saga model, while bus access stays explicitly privileged.

## Current control without a separate DSL

```saga
use machine

let current = machine.foc_current(
    2.0, 120.0, 2.0, 120.0,
    0.08, 0.00012, 0.00012, 0.018,
    25.0, 24.0, 12.0
)

machine.foc_step(
    current,
    0.0, 6.0,
    ia, ib, ic,
    electrical_angle,
    electrical_speed,
    dc_bus,
    0.00005
)

let duty_u = machine.foc_duty(current, 0)
let duty_v = machine.foc_duty(current, 1)
let duty_w = machine.foc_duty(current, 2)
```

The loop state is a normal Saga object. PWM/gate-driver ownership is separate, so the same controller can be simulated without granting device authority.

## Encoder, identification and compensation

`encoder_integrated` unifies modulo absolute counts and ordinary incremental counts. Samples carry integer nanosecond timestamps, so velocity estimation does not have to infer time from loop count.

`rls2` makes small online model updates possible without a matrix framework. `disturbance_observer` and `friction_compensation` add explicit compensation stages rather than hiding them inside a servo object. `mpc2` provides a bounded fixed-horizon two-state controller for applications where a single PID is not enough.

## Synchronized axes

`axis_sync` implements explicit ratio/offset electronic gearing and bounded correction. It reports whether skew exceeds the configured limit; it does not decide whether that condition means log, controlled stop or safety trip.

## Fieldbus and time

Saga 0.47 exposes EtherCAT frame/datagram construction as pure data and raw Linux EtherCAT exchange as a device-capability operation. CAN-FD adds explicit BRS-aware send, frame flags and timestamped receive. Timestamp results state their provenance (`hardware`, `software`, `host`, `none`) instead of flattening all clocks into one label.

## MCU/RTOS source discipline

For code intended to become a fixed cyclic control function, annotate it:

```saga
@control_tick
fn control_tick(error: decimal) -> decimal {
    var correction = error
    for i in 0..3 {
        correction = correction * 0.5
    }
    return correction
}
```

The compiler rejects list construction, async/task structures, resource-lifetime changes, exceptions, unbounded loops and known blocking receive/exchange calls in this function in both Python and Go implementations.

This does **not** mean the hosted Python runtime has become hard real-time or zero-allocation. The annotation defines the Saga source contract from which an MCU/RTOS backend can produce and then verify an allocator-free target loop. Target WCET, IRQ latency, DMA/PWM scheduling, EtherCAT Distributed Clocks and safety behavior still require target-specific engineering and physical qualification.
