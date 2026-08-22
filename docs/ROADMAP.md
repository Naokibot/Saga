# Saga Roadmap — 1.0 RC1 status

The original pre-1.0 implementation roadmap is complete at the **0.14.0 / Language Edition 1.0 RC1** baseline. “Complete” here means the feature has a working Native implementation and a validation path; it does not mean every backend has identical optimization depth or that external platform/vendor certification has been completed.

## Completed language and tooling baseline

- typed multi-source units, `saga.toml`, lockfile and reproducible `.sagapkg`
- formatter, standard linter, native test declarations, REPL, debugger and LSP
- `option[T]`, `result[T,E]`, enums, records, `match`, enum exhaustiveness and interpolation
- typed JSON and SQL declaration code generation
- native standalone backend with no external language runtime dependency
- direct scalar WebAssembly backend
- optional Python source exporter for interoperability only
- incremental build cache
- deterministic optimization passes (constant folding and unreachable branch elimination after type checking)
- signed packages with Ed25519 plus an explicit publisher trust store
- isolated, race-resistant task model
- fixed-point self-host compiler
- Native Hosted standard library for files, JSON, time, math, crypto/random, TCP, HTTP, persistent KV data, processes, regex and dependency-free game primitives
- package registry reference protocol/server implemented in Saga Native tooling
- stable structured diagnostics independent of translated message text

## 1.0 release gates (quality gates, not missing language features)

These are intentionally not represented as additional language syntax:

1. independent security audit by an organization outside the Saga implementation project;
2. Windows x86-64, Windows ARM64 and Linux ARM64 target-hardware execution evidence;
3. independent conformance laboratory results;
4. multi-country / multi-organization production adoption evidence;
5. public Internet registry operations with production identity, TLS, moderation and recovery procedures;
6. standards-body review if Saga is formally proposed to ISO/IEC JTC 1/SC 22 or another standards organization.

## Post-1.0 proposals

Post-1.0 work is not part of the 1.0 language promise. Candidate work includes a full-Standard-Core WebAssembly backend, hardware-accelerated window/audio game backend, optimizing native code generation beyond the runtime-AOT profile, and vendor-specific mobile distribution tooling. Such features shall not change 1.0 Standard Core semantics without the normal compatibility process.
