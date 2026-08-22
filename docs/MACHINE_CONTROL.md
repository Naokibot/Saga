# Machine Control

Saga's `machine` module is the hosted machine-control profile. It combines portable control algorithms with explicit, capability-gated hardware adapters.

## Timing model

`machine.timing_class()` returns `hosted-soft-realtime`. The hosted runtime uses monotonic clocks and periodic scheduling, but it does **not** claim bounded hard-real-time latency. Servo loops that must meet a hard deadline belong on an MCU/RTOS or a dedicated motion controller; Saga can supervise them over CAN, UART, SPI, or another bus.

`machine.monotonic_ns()` is monotonic within a process and has an implementation-defined origin. Do not compare its absolute value across processes or machines.

## Portable control layer

- PID with output clamping, integral limits, and anti-windup
- Slew/rate limiting
- Trapezoidal acceleration/deceleration profile
- Monotonic watchdog
- Safety latch with immediate registered-actuator stop
- Periodic soft-real-time control cycle with overrun/jitter counters
- Servo pulse mapping
- Incremental encoder position/velocity estimation

These functions do not require physical-device permission.

## Hardware adapters

Hardware adapters require `--allow-device` (or the standalone-runtime equivalent). On Linux the native profile supports:

- I2C through `i2c-dev`, including combined write/read with repeated START
- SPI through `spidev`
- UART through `termios` with `select`-based timeout handling
- classic CAN and CAN FD through SocketCAN
- Linux PWM sysfs
- IIO sensor/ADC reads restricted to `/sys/bus/iio/devices`
- servo output
- two-PWM H-bridge DC motor output with break-before-make

The portable control layer remains available on non-Linux hosts; unsupported hardware adapters fail closed.

## Safety model

A `SafetyLatch` is intentionally one-way until the application explicitly clears it. A trip immediately invokes registered actuator stop callbacks. DC motors register a zero-output stop when created. A guarded servo registers a zero-duty stop when `servo_guard` is applied. Attaching an actuator to a latch that is already tripped immediately puts that actuator in its software-defined safe state.

Software safety is not a substitute for machine safety hardware. Systems capable of injuring people or damaging equipment should use an independent hardwired emergency-stop chain, power/contactors or STO where appropriate, limit switches, fusing/current protection, and a safety-rated controller when required by the application. A Saga process crash, OS stall, kernel fault, bus fault, or power-stage failure must not be the only thing standing between a hazard and motion.

## Example control loop

```saga
use machine

let pid = machine.pid(1.2, 0.15, 0.02, -1.0, 1.0)
let profile = machine.profile(0.0, 0.0, 90.0, 45.0, 120.0)
let cycle = machine.cycle(10_000)
let watchdog = machine.watchdog(100)

let i = 0
while i < 100 {
    let target = machine.profile_step(profile, 0.01)
    let command = machine.pid_step(pid, target, 0.0, 0.01)
    print(target, command)
    machine.watchdog_feed(watchdog)
    machine.cycle_wait(cycle)
    i = i + 1
}
```

The example computes commands only. Connecting those commands to a physical actuator requires explicit device permission and an appropriate safety design.

## Live qualification

`tools/machine_control_qualification.py` performs the non-motion software qualification by default. It does not energize an actuator. Physical bus and motion qualification belongs in an operator-controlled lab with known wiring and external safety measures; missing hardware is reported as BLOCKED/UNEXECUTED, never PASS.

## Saga 0.36 industrial-control additions

### Jerk-limited S-curve planning

`machine.s_curve(position, velocity, acceleration, target, max_velocity, max_acceleration, max_jerk)` creates a portable motion planner. `s_curve_step`, `s_curve_velocity`, `s_curve_acceleration`, `s_curve_done`, and `s_curve_retarget` expose deterministic state. The planner clamps velocity/acceleration and limits acceleration change by `max_jerk * dt`; it also prevents stepping past the target.

### Safety-latched axis supervisor

`machine.axis(...)` combines a motion profile, PID output in `[-1,1]`, software travel limits, following-error supervision and a `SafetyLatch`. `axis_step(axis, measured_position, dt)` trips the latch and forces the command to zero when the measured position leaves its configured software limits or the planned/measured position difference exceeds the configured following-error limit.

This is a **supervisory axis controller**, not a certified servo loop. The real current/torque/velocity loop should normally execute in a drive, MCU/RTOS or motion controller.

### Modbus RTU and Modbus TCP

0.36 adds an industrial Modbus master surface:

- `modbus_rtu_open(path, baud, timeout_ms, unit_id)`
- `modbus_tcp_open(host, port, timeout_ms, unit_id)`
- `modbus_read_holding(master, address, count)`
- `modbus_read_input(master, address, count)`
- `modbus_read_coils(master, address, count)`
- `modbus_write_register(master, address, value)`
- `modbus_write_registers(master, address, values)`
- `modbus_write_coil(master, address, state)`
- `modbus_close(master)`

RTU validates CRC-16, unit id, response size and Modbus exception frames. TCP validates transaction id, protocol id, unit id, MBAP length and exception frames. Register/coil counts are bounded to the protocol maxima (125 read registers, 123 write registers, 2000 read coils). Malformed/short/exception responses fail closed.

Both hosted implementations require physical-device permission for Modbus. Modbus TCP also requires an explicit network host/port grant; the independent Go runtime accepts repeated `--allow-net host[:port]` grants for this machine-control path, matching the Python runtime's deny-by-default intent.

### Recommended architecture

For machinery capable of hazardous motion, use Saga as the orchestration/supervisory layer: recipes, sequencing, HMI, diagnostics, data logging, trajectory generation and PLC/drive communication. Keep hard safety and bounded-deadline control in safety-rated or real-time components. A software latch supplements, rather than replaces, independent E-stop/STO/limit circuits.

## Saga 0.37 endurance evidence

`tools/industrial_endurance_simulation_037.py` connects the existing `AxisController`, `SafetyLatch`, and `ModbusRTUMaster` to an in-memory deterministic PLC/drive/UART digital twin. The default qualification advances 168 simulated hours at a 100 ms supervisory cycle (6,048,000 cycles) and injects following-error, software-limit, emergency-stop, RTU CRC-corruption and response-timeout faults. Each safety trip must force output to zero and requires an explicit reset before motion resumes.

This is deliberately **simulation evidence**, not a physical endurance certificate. It does not reproduce EMI, grounding, connector faults, mechanical wear, real PLC/drive firmware, bus contention, OS scheduler tails or hard-real-time deadlines. Physical hardware-in-the-loop testing is still required before a machine deployment claim.

## Saga 0.46 precision machine-control additions

0.46 adds a common Python/Go precision-control layer rather than another hardware-specific façade:

- `pid2` / `pid2_step` / `pid2_reset`: 2-DOF PID with derivative-on-measurement, derivative filtering and back-calculation anti-windup;
- `motor_feedforward`: explicit `kS + kV + kA` model;
- `alpha_beta` / `alpha_beta_step` / `alpha_beta_reset`: lightweight position/velocity observation;
- `notch` / `filter_step` / `filter_reset`: second-order resonance filter;
- `clarke`, `park`, `inverse_park`, `svpwm`: PMSM/BLDC field-oriented-control math;
- `deadline_budget`, `budget_begin`, `budget_end`, `budget_stats_json`, `budget_reset`: hosted computation-budget observation without hidden stop/mode policy.

These additions are portable calculations and require no device capability. Hardware output remains a separate explicit action. See `spec/SAGA_PRECISION_MACHINE_0.46.md` and `docs/PRECISION_MACHINE_0.46.md`.
