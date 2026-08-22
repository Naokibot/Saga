# Saga 0.44.0 — 4 kHz Hosted Control Profile

Saga 0.44 adds a control scheduling profile designed for 4,000 logical control ticks per second (250 us period) while keeping the hosted-runtime safety boundary explicit.

## 4 kHz scheduling

- `machine.cyclic_clock(4000)` creates a 250 us cyclic source.
- Linux uses the kernel `timerfd` periodic timer when available.
- `machine.cycle_wait_due(clock)` returns the number of control ticks that became due since the previous wait.
- Kernel expiration counts are authoritative, so temporary host pre-emption does not silently lose logical state updates.
- Other platforms use an absolute-deadline sleep/spin fallback.
- Timing telemetry reports backend, period, wait calls, logical cycles, overruns, `last_due`, `max_due`, and jitter.

At 4 kHz, callers should process `cycle_wait_due()` catch-up ticks deterministically. A value above one means the hosted process did not execute physical I/O at every 250 us boundary. This is intentionally reported rather than hidden.

## Control-compute budget

The 0.44 qualification workload combines cached multirotor allocation, a compact state-space command, and eight-channel actuator conditioning. Its p99 execution time must remain below the 250 us 4 kHz budget in the qualification environment.

## Boundary

This profile is hosted soft real-time. It is suitable for high-rate supervisory/HIL control on capable hosts, but it does not replace an RTOS, FPGA, hardware timer/DMA output engine, drive current loop, or certified safety controller when every physical edge must meet a hard deadline.
