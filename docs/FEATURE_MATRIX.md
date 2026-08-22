# Saga 0.23.0 Feature Matrix

| Capability | Profile/status | Notes |
|---|---|---|
| Variables, exact numbers, collections, control flow | Standard Core 1.0 | Native + Python reference |
| Functions, recursion, higher-order functions, lexical closures | Standard Core 1.0 | implemented |
| OOP, interfaces, abstract classes, generics | Standard Core 1.0 | implemented |
| Exceptions, option/result, enum/record/match | Standard Core 1.0 | implemented |
| Namespaced modules + visibility | Edition 2027 Preview | legacy flattened source inclusion retained for 1.0 |
| float32/float64 | Edition 2027 Preview | explicit exact/float boundary |
| fixed-width integers | Edition 2027 Preview | checked narrowing; arithmetic promotes to `int` |
| generic constraints + associated types | Edition 2027 Preview | semantic/interface constraints |
| `?` failure propagation | Edition 2027 Preview | result/option |
| resource/move/using/defer | Edition 2027 Preview | deterministic resource close and move checking |
| async/await/taskgroup | Edition 2027 Preview | isolated structured concurrency |
| timeout/cancel/channel/stream/actor | Edition 2027 Preview | bounded channel backpressure; serial actor state |
| unsafe boundary | Edition 2027 Preview | required for FFI/JIT native operations |
| derive + comptime | Edition 2027 Preview | semantic derivation + constant AST folding |
| Diagnostics v2 + LSP code actions | Toolchain | stable IDs, fixes, explain actions |
| deterministic lock/verify/pack | Toolchain | implemented |
| fixed-point Saga compiler + canonical Saga kernel | Official `saga-sh3` distribution | SH-3 qualified; Stage2/Stage3 compiler fixed point + deterministic kernel lowering |
| native standalone build | Native distribution | final Linux x86-64 normal binary static |
| scalar WASM | Build target | existing documented subset |
| embedded-wasm | Edition 2027 expert target | no import section; strict scalar library subset |
| C ABI/FFI Profile 1 | Optional `sagaffi` | scalar int64/float64; explicit unsafe |
| native scalar JIT | Optional `sagajit` | restricted Linux x86-64 integer-expression JIT |
| Native Hosted I/O/network/HTTP/DB/process/regex | Native Hosted | HTTP server + optimistic DB transactions added in 0.21 |
| RGBA8/PNG/JPEG/animation/camera/tilemap/particles/physics/WAV/assets | Portable Game | implemented |
| Desktop window/keyboard/mouse/gamepad/audio | Desktop Game | optional native backend |
| OpenGL / SDL Native2 / Vulkan present | Desktop Game backend | implementation mechanisms |
| SIR1 fragment | Portable shader IR | GLSL120/450, HLSL5, MSL2, WGSL |
| SIR1 compute | Edition 2027 Preview | GLSL450/HLSL5/MSL2/WGSL + CPU reference |
| Game API inventory | Native | 101 typed functions; checker/runtime/manifest aligned |
| Unicode source profile | Standard/Edition policy | UTF-8 + vendored Unicode 15.1 XID/NFC |
| Evolution proposal process | Governance | SEP template/process included |
| Standardization evidence registry | Tooling | evidence registry; not standards-body approval |

## 0.20.0 low-level and self-hosting profiles

- C ABI Profile 2: aggregate layout, by-value structs, callbacks, explicit raw-pointer ownership and lifetime checking. Linux x86-64 reference backend validated under `sagaffi`.
- Bare-Metal Profile 1: Cortex-M0 and STM32F030K6 target profiles, vector table, interrupts, volatile MMIO, NVIC, critical sections, minimal tick/yield/reset substrate, ELF/BIN output.
- SH-3 is qualified in the official `saga-sh3` implementation. Canonical compiler and language kernel sources are `selfhost/sh3/sh3c.saga` and `selfhost/sh3/kernel.saga`; the C11 VM/launcher are language-neutral bootstrap machinery. Go/Python implementations remain non-official references for differential testing.

## 0.23.0 application expansion profiles

- Web/PWA: 107 typed web APIs, 101 Browser Host operations, canonical SH-3 browser VM/kernel and real Chromium Blink/V8 integration.
- Backend: real Native Hosted HTTP listen/accept/respond server with close-safe acceptance and body ceiling.
- DB: optimistic transaction snapshot/commit/rollback with conflict detection and atomic replacement.
- Portable 3D Preview: cube/custom/OBJ meshes, transforms, perspective camera, reciprocal-depth software rasterization and wireframe rendering.
- Systems: platform/architecture/CPU/page-size introspection.

- Universal App Actions: 10 Saga source APIs plus 53 first-party browser operations; arbitrary future/vendor actions remain representable through namespaced operation identifiers and JSON payloads.

See `SAGA_USE_CASE_MATRIX_0.23.md` for capability and validation boundaries.
