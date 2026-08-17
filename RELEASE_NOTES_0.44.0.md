# Saga 0.44.0 — 4 kHz Hosted Control Profile

Saga 0.44 adds a 4,000 Hz logical control profile with a nominal 250 us period.

## Added
- `machine.cyclic_clock(4000)` for frequency-based cyclic scheduling.
- `machine.cycle_wait_due(clock)` to expose the number of logical ticks that became due.
- Linux `timerfd` backend in the Python reference runtime.
- Absolute-deadline sleep/spin fallback for other hosted environments.
- Independent Go implementation with matching frequency/due-count semantics.
- 4 kHz qualification tool and regression tests.
- Timing telemetry for period, logical cycles, wait calls, overruns, due counts, backend and jitter.

## Validation
- 4000 logical ticks / 1.000011849 s = 3999.95 Hz.
- Full logical control workload: 4000 ticks / 1.000047906 s = 3999.81 Hz.
- Cached allocator + compact state-space + 8-channel actuator path: p99 56.142 us against a 250 us compute budget.

## Boundary
This is hosted soft real-time. Catch-up ticks are explicitly reported when the OS misses individual execution slots. Exact physical 250 us I/O deadlines require a qualified RTOS/PREEMPT_RT/drive/FPGA/hardware path and are not claimed by this release.