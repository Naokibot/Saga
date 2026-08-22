# Saga 0.18.0 feature audit

## Stable Standard Core

Language Edition 1.0 RC1 remains available and includes immutable/mutable bindings, static typing and inference, exact integer/decimal/rational arithmetic, bool-only conditions, collections, functions/recursion/higher-order functions, lexical closures, classes, inheritance, interfaces, abstract classes, generics, private members, annotations, exceptions, `option[T]`, `result[T,E]`, enums, records, exhaustive `match`, interpolation, multi-source projects, isolated tasks and standard tests.

## Edition 2027 Preview

- namespaced modules, aliases and visibility;
- float32/float64 plus fixed-width boundary integers;
- generic constraints and associated types;
- `?` option/result propagation;
- resource/move/using/defer safety;
- async/await/taskgroup, cancellation/timeout, bounded channels/streams and actors;
- explicit `unsafe` boundary;
- compiler-recognized derive and pure compile-time functions;
- Diagnostics v2 and LSP code actions;
- optional scalar C FFI and native JIT profiles;
- no-import Embedded Portable WASM profile.

## Graphics/game

- 92 statically typed Native game APIs with checker/runtime/manifest alignment.
- Portable RGBA8 framebuffer, PNG/JPEG, animation, camera, tilemap, particles, AABB 2D physics, WAV and asset cache.
- Desktop native window, realtime keyboard/mouse/gamepad state and audio.
- OpenGL programmable renderer, SDL Native2 accelerated presentation, optional Vulkan framebuffer-present backend.
- SIR1 canonical shader IR with SHA-256 identity.
- Fragment generation: GLSL 1.20/4.50, HLSL 5, MSL 2, WGSL.
- Compute generation: GLSL 4.50, HLSL 5, MSL 2, WGSL plus deterministic CPU reference execution.

## Toolchain and ecosystem

`run`, `check`, `build`, `test`, `fmt`, `lint`, `repl`, `debug`, `lsp`, `lock`, `verify`, `pack`, `registry`, `capabilities`, `learn`, `explain`, `conformance`, `doctor`, `info`, code generators and standards evidence tooling remain available. The ordinary Linux Native binary is self-contained and statically linked; optional Desktop/FFI/JIT profiles have explicit native-host dependencies.

Signed package/trust infrastructure and the public static registry profile remain separate from language semantics. Package signatures establish integrity/identity, not automatic publisher trust.

## Implementation diversity and bootstrap

- Saga Native and Python reference remain independent lexer/parser/checker/runtime code paths for Standard Core and pass the published cross-implementation suite.
- The clean-room C11 subset from 0.17 remains a third implementation subset, not a complete Standard Core implementation.
- The Saga compiler **driver** is Saga source and reaches a reproducible fixed point.
- The Native runtime/execution kernel still has published Go seed/runtime source. SH-3 all-runtime-source self-hosting is not claimed.

## International/standards engineering

- normative English specifications and machine-readable compatibility manifests;
- UTF-8 source, vendored Unicode 15.1 identifier/NFC tables and a per-Edition Unicode upgrade policy;
- stable diagnostics independent of translated text;
- Edition compatibility model and public SEP governance template;
- deterministic locking/packaging and fixed-point bootstrap evidence;
- conformance profiles that separate project evidence from independent certification.

## Deliberate profile limits

- C ABI Profile 1 is scalar; arbitrary structs, callbacks and ownership-bearing raw pointers are not yet portable ABI claims.
- Native JIT is a restricted Linux x86-64 integer-expression profile, not whole-language JIT compilation.
- Embedded target is freestanding/no-import WebAssembly, not a bare-metal kernel/BSP.
- Compute IR source/reference semantics are portable; physical GPU dispatch remains backend/host evidence.
