# Saga 0.36 General-Purpose Readiness

Saga 0.36 is intended to be usable as a serious general-purpose language preview rather than a syntax demonstration. This document separates implemented engineering from claims that still require external evidence.

## Practical language/tooling surface

- static typing with inference, generics, constraints, associated types, classes/interfaces/inheritance, enums/tagged unions and exhaustive match;
- lexical closures, exceptions/finally, option/result, resource classes, async/structured concurrency and isolated CPU work;
- namespaced modules with public/internal visibility, deterministic `.smi.json` interfaces and incremental native builds;
- formatter, linter, test runner, REPL, debugger, LSP diagnostics/actions, package lock/verify/pack, signed registry workflow and project templates;
- exact integer/decimal/rational values plus explicit binary floats;
- hosted standard modules for files, networking/HTTP, JSON, DB, crypto/security, processes, UI/game, data/science and machine control;
- native executable, object-level separate compilation and WebAssembly profiles, with unsupported subsets failing closed;
- independent Python and Go implementations used for differential conformance rather than a single self-referential implementation.

## 0.36 maturity changes

The release version is now explicitly distinct from the Native Runtime ABI version. Saga 0.36 retains Native Runtime ABI 0.35 where layout semantics did not change. This avoids artificial ABI churn merely to make version numbers match.

A dedicated `machine` project template was added and the machine-control profile was expanded with S-curve planning, supervised axes and Modbus RTU/TCP. The reference implementation keeps hardware access capability-gated and defaults qualification to non-motion tests.

## Boundaries that remain before a 1.0 GA claim

- physical Windows/macOS native-runtime qualification and broader independent implementation evidence;
- open-world native class/plugin dispatch and cross-module generic-template specialization;
- production low-pause concurrent/compacting GC evidence;
- public ecosystem scale, long-term compatibility experience and independent security review;
- hard-real-time and safety certification are outside the hosted language profile;
- physical machine-control adapters require operator-controlled lab qualification on named hardware.

Therefore 0.36 should be described as a **reviewable general-purpose/industrial-control preview**, not as an ISO standard, safety-certified PLC language, or universally production-qualified runtime.
