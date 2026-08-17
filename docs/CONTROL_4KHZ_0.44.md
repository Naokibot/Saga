# 4 kHz control in Saga 0.44

A 4 kHz control loop has a nominal **250 us period**.

```saga
use machine
let clock = machine.cyclic_clock(4000)
while true {
    let due = machine.cycle_wait_due(clock)
    var i = 0
    while i < due {
        # one deterministic control-state update
        i = i + 1
    }
}
```

On Linux, the Python runtime uses a periodic kernel `timerfd`. If the process is delayed for multiple periods, the next `cycle_wait_due()` value is greater than one. That allows state-estimation/control integration to catch up without pretending the missed host deadlines did not happen.

`machine.cycle_stats_json(clock)` reports the selected backend, 250 us period, logical cycle count, wait calls, overruns, `last_due`, `max_due`, and timing jitter.

The independent Go runtime uses the same frequency/due-count semantics with an absolute-deadline sleep/spin implementation.

## Real-time boundary

Saga 0.44 qualifies the hosted control compute path and logical tick accounting. It does not certify that every physical GPIO/PWM/CAN/EtherCAT transaction occurred on an exact 250 us boundary. Motor-current/FOC loops, deterministic fieldbus clocks, hardware waveform generation, and safety-rated motion should remain in a qualified drive/MCU/RTOS/FPGA path unless separate physical timing evidence exists.