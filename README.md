# Saga 0.49.0 — Production & Industrial Profile

Saga is an independent general-purpose language designed to remain readable while scaling into native systems and physical-machine control. 0.49 adds first-class large-system production gates and explicit periodic-control contracts on top of the 0.47 advanced-motion stack.

```saga
use machine

@control_tick(20000, 35)
fn current_tick(error: decimal) -> decimal {
    return error * 0.5
}

let guard = machine.control_guard(20000, 35, 100, 5)
let now = machine.monotonic_ns()
let input_ts = now
if machine.control_guard_begin(guard, input_ts, now) {
    let command = current_tick(1.0)
}
let healthy = machine.control_guard_end(guard, machine.monotonic_ns())
```

For large repositories, `saga-workspace.toml` groups independently locked projects and `saga production-check --native` fails closed on compile/lint/lock/reproducible-package/native-build problems while reporting minimum capability categories.

This is a production-candidate engineering profile, not a shortcut around independent security audits, physical host qualification, field history or functional-safety certification.

See `spec/SAGA_PRODUCTION_INDUSTRIAL_0.49.md`, `docs/PRODUCTION_INDUSTRIAL_0.49.md`, `RELEASE_NOTES_0.49.0.md`, and `saga-REVIEW_REPORT-0.49.0.md`.

## Retained Advanced Motion Control 0.47

Saga is an independent general-purpose programming language built around readable source, static accountability, exact-number defaults, explicit authority and progressively deeper systems capability.

Saga 0.47 extends the 0.46 precision-machine layer with a shared Python/Go advanced-motion surface: persistent FOC current control, integrated incremental/absolute encoders, online RLS identification, bounded MPC, disturbance/friction compensation, electronic gearing, EtherCAT/CAN-FD transport with timestamp provenance, and a compiler-enforced `@control_tick` MCU/RTOS source profile.

```saga
use machine

let foc = machine.foc_current(2.0, 80.0, 2.0, 80.0, 0.08, 0.00012, 0.00012, 0.018, 25.0, 24.0, 12.0)
machine.foc_step(foc, 0.0, 4.0, 0.2, -0.1, -0.1, 0.25, 40.0, 48.0, 0.0001)
let duty_u = machine.foc_duty(foc, 0)
```

Control mathematics remains ordinary Saga state. Raw EtherCAT/CAN/PWM/device I/O remains capability-gated. `@control_tick` rejects dynamic Saga allocations, async/task structures, resource-lifetime changes, exceptions, unbounded loops and known blocking receive/exchange operations, but it is a source-level MCU/RTOS contract rather than a claim that hosted Python/Go is hard real-time or that target object code has already been proven allocation-free.

See `spec/SAGA_ADVANCED_MOTION_0.47.md`, `docs/ADVANCED_MOTION_0.47.md`, `RELEASE_NOTES_0.47.0.md`, `saga-REVIEW_REPORT-0.47.0.md`, and `saga-VALIDATION-0.47.0.md`.

## Retained Precision Machine Control 0.46

Saga 0.46's 2-DOF PID, motor feed-forward, alpha-beta observer, resonance notch, Clarke/Park/inverse-Park, SVPWM and deadline-budget observer remain available. 0.47 builds on those primitives rather than replacing them.

## Retained Language Synthesis 0.45

Saga is an independent general-purpose programming language with its own grammar/type system, module model, native ABI/compiler/runtime, package tooling, independent Go implementation, and SH-3 self-host path.

Saga 0.45 makes `async`/`await`, lexical `taskgroup`, LIFO `defer`, deterministic `using`, and resource-focused `move` a coherent common surface across the Python reference implementation and the independent Go implementation. Public async module APIs are represented as `future[T]` in the deterministic `.smi.json` ABI.

```saga
async fn double(value: int) -> int {
    return value * 2
}

fn answer() -> int {
    defer print("cleanup")
    return await double(21)
}

print(answer())
```

The new words are contextual: an older program can still declare names such as `fn await()` where the spelling is not being used as the 0.45 construct. `move` is intentionally limited to move-only native resources; ordinary Saga values remain managed and do not acquire a general borrow-checker burden.

See `spec/SAGA_LANGUAGE_SYNTHESIS_0.45.md`, `docs/LANGUAGE_SYNTHESIS_0.45.md`, `RELEASE_NOTES_0.45.0.md`, `saga-REVIEW_REPORT-0.45.0.md`, and `saga-VALIDATION-0.45.0.md`.

## Retained 4 kHz hosted control profile

### 4,000 control ticks per second

Saga 0.44 introduces a 4 kHz hosted control profile with a **250 us period**.

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

On Linux, `CyclicClock` uses the kernel `timerfd` periodic timer. The kernel counts every expiration, so temporary process pre-emption does not silently erase logical control ticks. `cycle_wait_due()` returns the number of state updates that became due; `cycle_stats_json()` reports period, backend, wait calls, cycles, overruns, `last_due`, `max_due`, and jitter.

The cached control allocator, compact state-space path, and per-actuator conditioning remain available for high-rate loops. Saga still keeps physical E-stop/STO/interlocks and hazardous-motion safety policy outside the hosted language runtime.

## Timing boundary

The 4 kHz profile is **hosted soft real-time**. Counting/executing 4,000 logical state updates per second is distinct from guaranteeing a physical GPIO/PWM/CAN/EtherCAT edge on every exact 250 us boundary. Hard-deadline motor-current/FOC loops, hardware-timed waveforms, EtherCAT distributed-clock slaves/masters, and certified safety motion require the relevant RTOS/drive/FPGA/driver/hardware qualification.

See `docs/CONTROL_4KHZ_0.44.md`, `RELEASE_NOTES_0.44.0.md`, and `validation/control-4khz-0.44.0.json` for the detailed qualification boundary.