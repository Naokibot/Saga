# Saga Production GA Control Profile 0.50

## Status

Saga 0.50 defines a production-GA **language/toolchain control profile**. The designation applies to the compiler/runtime/tooling release, not to an arbitrary machine built with Saga and not to IEC 61508 / ISO 13849 / IEC 62061 certification.

A physical machine deployment is fail-closed by `saga production-check --machine` until the project supplies source-bound hazard-analysis, WCET and HIL evidence and declares independent emergency-stop, STO/interlock and hardware-watchdog layers.

## 1. Control-critical source boundary

`@control_tick(rate_hz, budget_us)` identifies a periodic deterministic control kernel. For machine-production qualification the two integer literals are mandatory and must satisfy:

- `1 <= rate_hz <= 1_000_000`
- `budget_us > 0`
- `budget_us * rate_hz <= 1_000_000`

Compatibility mode still accepts the historical zero-argument spelling, but the machine-production gate rejects it.

## 2. Transitive control safety

A `@control_tick` function may call user code only when the callee is annotated `@control_safe` or `@control_tick`.

The compiler validates the complete statically resolved call graph and rejects:

- an unannotated user helper (`SAGA-C490`),
- recursion in the control graph (`SAGA-C485`),
- indirect/dynamic calls (`SAGA-C489`),
- non-approved builtins (`SAGA-C491`),
- raw/blocking/time-dependent machine calls (`SAGA-C492`),
- calls into external modules from the control region (`SAGA-C493`).

`@control_safe` helpers inherit the bounded source restrictions of `@control_tick`: no async/await, dynamic list construction, closure creation, resource move/lifetime changes, exceptions, unbounded while, or non-literal-bounded for loops.

## 3. Bounded state mutation

Within the production control surface:

- assignments may target parameters/local variables only,
- writes to shared/global variables are rejected (`SAGA-C487`),
- direct arbitrary object-field mutation is rejected (`SAGA-C488`),
- statically bounded range loops above 4096 iterations are rejected (`SAGA-C486`).

Deterministic stateful control algorithms use audited `machine.*` primitives whose state objects are created before entering the periodic kernel.

## 4. I/O separation

Raw CAN/CAN-FD/EtherCAT/I2C/SPI/UART/Modbus/PWM/device I/O, wall/monotonic clock acquisition and blocking waits are outside the production control kernel. Applications pass timestamped input state into the kernel and consume command output through a target-qualified adapter.

This separation is deliberate: hosted Python/Go execution is not promoted to hard real-time merely because the source has a deadline annotation.

## 5. Machine deployment gate

`python -m saga production-check <project> --native --machine` requires:

1. compile + Standard lint pass;
2. exact project lock pass;
3. byte-reproducible package;
4. byte-reproducible native build when `--native` is selected;
5. at least one explicit `@control_tick(rate_hz,budget_us)`;
6. `machine-safety.toml` with profile `machine-production-ga-1`;
7. external emergency stop declared;
8. STO or equivalent independent interlock declared;
9. hardware watchdog declared;
10. deterministic target class (`rtos`, `mcu`, `preempt_rt`, or `qualified-motion-controller`);
11. source-bound hazard-analysis JSON;
12. source-bound WCET JSON;
13. source-bound HIL JSON.

Each evidence object must use schema 1, declare its exact evidence kind, have `pass: true`, include the project source SHA-256, and identify `saga_release: 0.50.0`.

The gate validates the binding and required evidence shape. It does not fabricate independent certification or prove that the submitted evidence is truthful.

## 6. Safety boundary

Saga software must not be the sole safety layer for hazardous motion. Physical emergency stop, STO/interlocks and other safety functions required by the risk assessment remain independent of the ordinary Saga runtime.

The language does not silently arm, move, land, disarm, reset a safety latch, or choose a machine safety policy. Application and external safety systems remain explicit.

## 7. Compatibility

0.50 retains the 0.49 production/workspace model, 0.47 motion stack, 0.46 precision-control stack, 0.45 async/resource synthesis and 0.44 hosted cyclic APIs. `@control_safe` is additive. Existing non-production code is not forced to opt into the stricter transitive profile.
