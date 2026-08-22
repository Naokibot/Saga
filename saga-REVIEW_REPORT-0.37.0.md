# Saga 0.37.0 Review Report

## Review goal

Saga 0.37.0 closes several structural gaps identified after 0.36: closed-world native virtual dispatch, dependent-module generic specialization limits, long final major-GC sweep pauses, shallow debugger/profiler evidence, package-index scaling limits, and missing desktop/industrial qualification paths.

The release identity is **Saga 0.37.0**. The Native Runtime ABI remains **0.35** because the existing value/layout ABI is preserved; the new dispatch and GC entry points are additive.

## Implemented runtime/compiler work

### Low-pause major GC

- Major marking remains incremental and object-budget bounded.
- Major sweep is now also incremental and object-budget bounded when low-pause mode is enabled.
- New runtime controls expose low-pause enablement, poll/step progress, configured budget, last/max pause work, and incremental-sweep counters.
- Objects allocated during an active sweep are protected from the current collection without being incorrectly promoted.
- The existing collector mode remains the default; low-pause major collection is opt-in.

This is **not a pauseless collector**. Nursery/minor collection is still stop-the-world, and no hard real-time latency bound is claimed.

### Open-world native dynamic dispatch

- Native virtual dispatch no longer emits a switch over subclasses visible in the current compilation graph.
- The runtime now owns a synchronized type/interface/method registry.
- A separately compiled/native extension can register a subtype and override after the base module was compiled.
- Generated ABI headers expose stable type IDs and dispatch-slot constants so extensions do not need to parse JSON metadata.
- Registration is idempotent and serialized with C11 mutexes where threads are available.
- Virtual invocation resolves the effective method through the runtime registry.
- ABI metadata declares `runtime_feature_level: 0.37` and the open-world dispatch protocol explicitly. Pre-0.37 binaries that never register their native classes are not silently advertised as open-world compatible; they need rebuilding or a registrar shim when mixed into the new dispatch path.

### Cross-module generic specialization

- Public generic functions imported from another module can be specialized at the caller for concrete argument types.
- Public generic classes imported from another module can be monomorphized at the caller, including methods and constructors.
- Explicit imported annotations such as `lib.Box[int]` and inferred concrete uses are both supported.
- Specializations retain owner-module template semantics while emitting caller-local concrete native symbols.

### Debugger/profiler

Python reference implementation:
- lexical-parent watches in nested scopes;
- bounded event recording with dropped/truncated counts;
- `--watch`, `--record`, and `--max-events`;
- statement hit counts and elapsed-interval profiling;
- heap current/peak evidence using `tracemalloc`.

Independent Go implementation:
- corresponding lexical watch/record behavior;
- bounded JSON debug records;
- statement-interval profile output;
- Go heap statistics;
- atomic JSON report replacement.

Profiler timings are elapsed statement intervals, not instruction-level CPU attribution.

## Package ecosystem work

- Registry metadata now has a SQLite index with WAL mode, busy timeout, explicit connection closing, and a schema version.
- FTS5 trigram substring search is used where available; SQL LIKE remains a safe compatibility fallback.
- Publish/index synchronization is handled through triggers and upserts.
- A synthetic 100,000 package-version corpus qualification exercises indexed search, concurrent readers, and SQLite integrity.

This scale test is **not evidence of 100,000 real community packages, real adoption, CDN/network behavior, publisher diversity, or package quality**.

## Desktop qualification work

A reproducible cross-target qualification now builds, for representative x86-64 targets:

- Saga CLI;
- standalone Saga runtime;
- target test binary;
- PE32+ structural validation on Windows output;
- Mach-O 64-bit structural validation on macOS output.

Review discovered that Linux-only machine-hardware tests had been compiled unconditionally for Windows/macOS. They were split behind the correct Linux build constraint. Windows/macOS **physical execution remains UNEXECUTED** because those hosts are not present in this environment.

## Industrial endurance simulation

A deterministic accelerated digital twin connects the real Python `AxisController`, `SafetyLatch`, and `ModbusRTUMaster` transaction/parser path to an in-memory PLC/drive/UART model. It injects:

- following-error fault;
- soft-limit excursion;
- emergency stop;
- corrupted Modbus RTU CRC;
- dropped Modbus response / timeout.

The seven-day equivalent run is simulation evidence only. It does not reproduce EMI, grounding, mechanical wear, physical bus arbitration, real device firmware, hard-real-time scheduling, certified STO, SIL/PL behavior, or servo-current-loop dynamics.

## Defects found and fixed during review

1. **Closed-world native dispatch** — visible subtypes were compiled into dispatch logic. Replaced with an open runtime registry.
2. **Imported explicit generic annotation fail-close** — cross-module generic inference worked but explicit `module.Type[T]` annotations still hit the former restriction. Fixed.
3. **Dynamic-dispatch diagnostic collision** — newly introduced runtime diagnostic IDs overlapped older text/exception identifiers. Moved to a distinct range.
4. **Concurrent first-use dispatch race** — a generated C `static` registration flag could race. Removed; registration is now idempotent and synchronized in the runtime registry.
5. **SQLite connection lifetime leak** — registry helpers relied on a transaction context manager that did not close the connection under current Python behavior. Fixed with explicit closing.
6. **Package substring scaling** — full SQL wildcard scans were not adequate for the scale target. Added FTS5 trigram indexing with safe fallback.
7. **Cross-target test build break** — Linux machine-device tests referenced Linux-only implementation types during Windows/macOS test compilation. Split platform-neutral and Linux hardware tests.
8. **Qualification tool PYTHONPATH dependency** — ecosystem and industrial qualification scripts could fail when executed directly from the repository root. They now self-register the project root like the other review tools.
9. **Stale native-game API validator reference** — validator pointed at a nonexistent 0.36 snapshot even though the hosted game API surface remained unchanged. Added a 0.37 carry-forward snapshot and aligned the validator.
10. **Dead closed-world helper/comment residue** — obsolete subclass-enumeration helper methods and misleading comments were removed after the open-world conversion.
11. **`saga_gc_step(0)` compatibility regression** — the first low-pause implementation coerced a zero work budget to one object, changing the established “start a major cycle without consuming mark work” behavior. Zero-budget step semantics were restored; `saga_gc_poll()` supplies a nonzero budget when progress is desired.

## Safety and maturity assessment

0.37 is materially closer to a general-purpose native language runtime, but it is still a preview line. In particular:

- low-pause applies to major collection; minor GC remains STW;
- open-world registration is implemented but repeated registration is optimized for correctness rather than minimum construction overhead;
- desktop output has cross-target build evidence, not physical OS execution evidence;
- industrial endurance is digital-twin evidence, not physical equipment qualification;
- no hard-real-time, safety certification, or functional-safety claim is made.

## Next high-priority work

- concurrent/incremental nursery strategy or a separately specified real-time heap profile;
- unloadable dynamic modules and dispatch-registry reclamation/versioning;
- shared/cached cross-module generic instantiation across package boundaries;
- source-level native debugger integration, sampling profiler, flamegraph/export support;
- hosted public registry/CDN, publisher identity/attestation, transparency/logging, and real ecosystem adoption;
- physical Windows/macOS runtime, filesystem, GUI, signing, installer, and device qualification;
- physical hardware-in-the-loop and long-duration PLC/drive/CAN/encoder/motor testing.
