# Saga 0.36.0 Review Report

## Review goal

Saga 0.36.0 moves the 0.35 native-runtime line toward practical general-purpose use and adds a deliberately supervised industrial-machine-control profile. The review treats machine control as a safety-sensitive integration surface: unsupported or ungranted physical/network access must fail closed, protocol inputs must be bounded, and hosted soft real-time behavior must not be described as hard real time.

The native runtime ABI remains **0.35** because this release does not intentionally change the previously frozen native value/layout contract. Release identity and ABI identity are now treated as separate version axes.

## General-purpose maturity work

- Retains the 0.35 managed runtime: owned text, managed Option/Result, exceptions with root unwind, native inheritance/interface dispatch, generational/incremental collector work, and generic monomorphization.
- Retains namespaced modules, public/internal visibility, separate compilation, incremental builds, Python and independent Go implementations, native/WASM paths, package tooling, formatter/LSP, hosted APIs, capability gating, and machine/game/application profiles.
- Adds a `machine` project template so a new control project starts from a simulation-first safety-latched structure instead of directly energizing physical outputs.
- Separates release version `0.36.0` from Native Runtime ABI/language-interface version `0.35`, avoiding ABI churn without a layout break.

## Machine-control additions

### Supervised motion

- `JerkLimitedProfile` provides bounded jerk, acceleration, and velocity with target retargeting and no target overshoot in the tested profile.
- `AxisController` combines a motion profile, PID loop, output clamp, soft travel limits, following-error supervision, and `SafetyLatch`.
- A tripped safety latch forces the commanded actuator output to zero and prevents a new motion target from being accepted until the surrounding application performs its recovery policy.

### Modbus

- Modbus RTU master support over the existing UART adapter.
- Modbus TCP master support over TCP.
- Holding/input register reads, coil reads, single/multiple register writes, and single-coil writes.
- RTU CRC-16 checking, bounded register/coil quantities, exception-response validation, and response-length checks.
- TCP MBAP transaction/protocol/unit/length validation and per-transaction socket deadlines.
- Modbus TCP requires both machine/device authority and an explicit network grant for the target host/port in both maintained implementations.

## Findings fixed during review

1. **Long-running Modbus TCP timeout defect** — a deadline set only when a connection was established could expire during later transactions. The Go master now refreshes the deadline for every transaction.
2. **Unbounded/ambiguous RTU timeout configuration** — a zero timeout could create unreliable blocking behavior. RTU now requires a positive timeout.
3. **Generic native Modbus handle validation** — shared native operation signatures use a common value surface, but runtime dispatch now rejects values that are not Saga RTU/TCP Modbus masters instead of invoking arbitrary host methods.
4. **Network capability gap in the independent Go implementation** — machine Modbus TCP now accepts explicit `--allow-net host[:port]` grants and rejects ungranted destinations. Imported source modules inherit only the resolved grant set.
5. **Machine template binding bug** — the generated loop counter originally used an immutable binding; the template now uses a mutable variable and passes checking/execution.
6. **Capability metadata** — the machine profile now records `network` alongside `device` and `realtime-control` because Modbus TCP is a network-bearing machine-control path.

## Safety assessment

Saga 0.36 is suitable for **supervisory and hosted soft-real-time control**, test benches, robotics coordination, PLC/drive communication, data acquisition, set-point generation, and safety-aware orchestration when appropriate external hardware protections are present.

It is **not** claimed to be a certified hard-real-time controller, safety PLC, SIL/PL implementation, or a replacement for independent emergency-stop/interlock circuitry. Servo current/torque loops, deterministic sub-millisecond control, and certified safety functions should remain in an MCU/RTOS, drive, PLC, or dedicated safety controller as appropriate.

## Remaining high-priority work before a 1.0 general-purpose claim

- physical Windows/macOS qualification for the current native runtime and installers;
- open-world native subclass/interface loading and broader cross-module generic specialization;
- lower-pause production GC work beyond the current preview collector model;
- larger public package ecosystem, reproducible registry operations, and independent security review;
- debugger/profiler depth and longer-running performance/stress evidence;
- physical qualification of representative I2C/SPI/UART/CAN/PWM/encoder/drive/Modbus equipment;
- a separately specified hard-real-time/offload story rather than pretending hosted JVM/OS scheduling is deterministic.
