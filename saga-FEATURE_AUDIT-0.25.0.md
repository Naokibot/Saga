# Saga 0.25.0 feature audit

## Language and implementations

- Language Edition 1.0 RC1 runtime baseline plus Edition 2027 Preview.
- Language Specification 1.0 RC2 editorial candidate; not Final.
- Python reference implementation, independent Go Native Standard Core and official SH-3 all-source self-host profile.
- Static types/inference, exact numbers, closures, OOP/interfaces/generics/associated types, records/enums/match, option/result, exceptions, resource/move/using/defer and structured concurrency remain available.

## Hosted/application surface

- Hosted: 28 modules / 168 registered entry points.
- `security`: 11 APIs; `crypto` security extensions and AES-GCM retained.
- `game`: 101 Native typed APIs plus Python finite-frame pygame adapter.
- `web`: 101 Browser Host operations; Universal App: 10 source APIs / 53 browser operations.
- GPIO: output/input/PWM/read/write/on/off/close with explicit device capability.
- Spark: session/local session/SQL/range-count/stop with process capability.
- AWS cloud adapter: environment/client/public-method calls with cloud capability.

## Platforms

- Production Vulkan present path is live-qualified on a software Vulkan ICD; physical GPU remains separate evidence.
- Android/iOS StandardCoreRuntime generators build/vet/execute in regression tests; CI/device validators are included.
- Native-host qualification exists for Linux/Windows/macOS; current local PASS is Linux only.
- Physical gamepad/GPIO and live service qualification use explicit hardware/credential gates.

## Tooling

`run`, `check`, `build`, `test`, `fmt`, `lint`, `repl`, `debug`, `lsp`, `lock`, `verify`, `pack`, registry operations, capability audit, conformance, doctor, mobile generation, standards evidence and GA readiness are present in the reference distribution. `python -m saga` is supported.

## Qualification boundary

Internal/current-host validation passes. Core GA 1.0 remains blocked by Final 1.0 specification, native Windows/macOS execution evidence, live signed external HTTPS registry evidence and an independent signed security audit. Optional physical/service profile status is never inferred from mocks or cross-builds.
