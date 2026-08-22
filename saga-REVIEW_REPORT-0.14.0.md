# Saga 0.14.0 source and language review report

Date: 2026-08-08  
Language edition: **1.0 RC1**  
Primary implementation: **Saga Native 0.14.0**

## Review objective

Review Saga as a general-purpose, internationally usable language candidate with emphasis on: independent execution, lightweight distribution, stability, learnability, deep type/system design, the complete pre-1.0 roadmap, package security, concurrency, developer tooling, and game-programming capability.

## Important defects found and fixed

1. **Task environment race (high).** Race Detector found a concurrent map read/write between worker-side lexical snapshotting and later parent declarations. Task preparation now takes the complete lexical/argument snapshot synchronously at task creation; workers receive only prepared isolated state. Race Detector passes after the change.
2. **Hosted DB atomicity (high).** A failed persistence operation could leave the in-memory KV state changed. `put/delete` now roll back on persistence failure; closed stores reject reads consistently.
3. **JSON ambiguity (medium/high).** Native JSON now rejects duplicate object keys and trailing non-whitespace content. Typed JSON code generation was also moved onto the same strict decoder, removing a separate looser parsing path.
4. **Package publisher trust (high).** A cryptographically valid signature no longer implies trust. Registry installation requires an explicit trusted publisher fingerprint or equivalent trust policy.
5. **Unsafe LSP rename (medium/high).** The prototype rename implementation matched lexical text rather than symbol scope and could rename unrelated shadowed names. Rename is disabled in 1.0 RC1 rather than exposing an unsafe refactor.
6. **Game render contract (medium).** `game.render` previously performed output while its API name suggested a pure rendering value. It now returns text; only `game.present` emits the frame.
7. **Game input buffering (medium).** Creating a fresh buffered reader on each call could lose already-buffered piped input. Input now uses a persistent synchronized reader.
8. **HTTP ambient behavior (medium).** Native HTTP no longer inherits environment proxy settings and does not automatically follow redirects, keeping network behavior explicit and reviewable.
9. **Runtime bloat (design).** Development tooling and standalone runtime were separated. Standalone programs now embed the smaller `saga-runtime`, not the full compiler/LSP/registry CLI, and execute verified embedded source directly from memory.

## Pre-1.0 roadmap review

The original language/tooling roadmap now has an implementation baseline for source units, manifest/lock, formatter, LSP, debugger, tests, option/result, enums, records, match/exhaustiveness, interpolation, typed JSON/SQL code generation, native build, scalar WASM, optional Python export, incremental builds, deterministic optimization, reproducible packaging, signed packages, publisher trust, concurrency isolation, and fixed-point self-hosting.

The term “implemented” does not erase backend scope: the direct WASM backend is intentionally a scalar subset, and the dependency-free game baseline is text-cell 2D rather than a GPU renderer. Those limitations are explicit instead of silently changing program meaning.

## Independence review

Saga Native execution requires no installed Python, Go, Java, Node.js, .NET, clang, or GCC runtime/toolchain. The Linux x86-64 CLI and runtime are statically linked. `saga info --json` declares `runtime_dependencies: []` and `compiler_toolchain_required: false`. The published bootstrap seed provenance remains visible; bootstrap provenance is not presented as a runtime dependency.

## External gates not falsely claimed

The review does not claim ISO/IEC publication/adoption, independent third-party security certification, production Internet registry operation, multi-country production adoption, or Windows/ARM64 real-device execution. These require organizations, infrastructure, credentials, or hardware outside this execution environment.
