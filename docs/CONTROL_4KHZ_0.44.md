# 4 kHz control in Saga 0.44

A 4 kHz loop has a **250 us period**. Saga 0.44 separates two questions that are often incorrectly conflated:

1. Can the controller compute 4,000 state updates per second?
2. Did physical I/O occur exactly on every 250 us deadline?

The first can be qualified in the hosted runtime. The second requires the OS, driver and hardware path to provide a deterministic real-time guarantee.

## Recommended loop

```saga
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

On Linux, `cycle_wait_due` is backed by `timerfd`. If the process is pre-empted for several periods, the next return value can be greater than one. That lets state estimation/control integration catch up without pretending the missed physical deadlines did not happen.

Use `machine.cycle_stats_json(clock)` to inspect timing. `overruns > 0` or `max_due > 1` means the host scheduler missed one or more individual execution slots even if the logical 4,000 tick count was preserved.

For motor-current loops, FOC, precise DShot waveforms, EtherCAT distributed clocks, or safety-rated motion, keep the hard real-time inner loop in the drive/MCU/RTOS/FPGA and use Saga as the higher-level 4 kHz supervisory/control layer only after hardware-specific qualification.
