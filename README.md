# Saga 0.44.0 — 4 kHz Hosted Control Profile

Saga 0.44 adds a hosted control profile for **4,000 logical control-state updates per second**, corresponding to a nominal **250 us period**.

On Linux, the Python reference runtime uses the kernel `timerfd` periodic timer. `machine.cycle_wait_due(clock)` returns the number of logical control ticks that became due since the previous wait, so temporary process pre-emption does not silently erase state updates. The independent Go implementation exposes the same frequency-based cyclic API and due-count semantics with an absolute-deadline sleep/spin scheduler.

Example:

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

## Qualification

Final reviewed source tree SHA-256: `cc58a362d0118f1b489f339cb90920e2423cfbf76a5ea3ad6dd44d05c5b07eb0`.

Source-bound 0.44 qualification observed:
- 4,000 logical ticks in **1.000011849 s**: **3999.95 Hz**
- Integrated full logical control workload: **4000 ticks / 1.000047906 s**, **3999.81 Hz**
- Cached allocator + compact state-space + 8-channel actuator conditioning: **p99 56.142 us**, below the 250 us compute budget
- Selected Python regression: **138/138 PASS**
- Python self-conformance: **48/48 PASS**
- Go self-conformance: **48/48 PASS**
- Python↔Go differential: **48/48 PASS**
- Module conformance: **14/14 PASS**
- Native Runtime: **10/10 PASS**
- Native Codegen: **17/17 PASS**
- Go tests and `go vet`: **PASS**

## Timing boundary

This is still **hosted soft real-time**. The host scheduler produced catch-up events (`cycle_wait_due() > 1`) in the qualification environment. Therefore this evidence proves that Saga can preserve and execute 4,000 logical state updates per second; it does **not** prove that a physical PWM/GPIO/CAN/EtherCAT edge occurred on every exact 250 us deadline.

Hard-deadline motor-current/FOC loops, deterministic fieldbus timing, hardware-timed waveforms, and certified safety motion require a qualified RTOS/PREEMPT_RT/drive/FPGA/hardware-specific backend. Physical E-stop/STO/interlocks remain external.