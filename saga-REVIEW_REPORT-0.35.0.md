# Saga 0.35.0 Review Report

## Review scope

This review treats Saga 0.35 as a native runtime/ABI release. It specifically reviews the six requested areas together rather than as isolated syntax changes:

- inheritance, interfaces and virtual dispatch;
- managed Option/Result payloads;
- owned native text;
- exception unwinding;
- generational/incremental/concurrent-sweep GC;
- generic aggregate/function monomorphization.

The review also covers C ABI cleanliness, `setjmp`/`longjmp` rules, GC mutation barriers, incremental invalidation, source/Go implementation regression, release installer behavior, and fail-closed boundaries.

## Findings fixed during implementation and review

1. **Virtual calls were initially compiler-internal only.** Linker-visible virtual-dispatch wrapper symbols and deterministic dispatch slots were added to the public native ABI so C clients can call through a base/interface contract.
2. **Hierarchy changes can alter generated closed-world dispatch.** The object cache now includes a digest of the complete resolved dispatch graph so hierarchy/override changes invalidate dependent native objects.
3. **Managed Option/Result roots originally covered only direct refs/tagged values.** Typed Option/Result roots now carry payload-kind descriptors and trace selected managed-ref or owned-text payloads.
4. **Borrowed text was insufficient for concatenation and exception messages.** `SagaText` now carries an explicit owner reference; owned copy/concat/scalar conversion allocate immutable managed text objects.
5. **`setjmp`/`longjmp` observable-local correctness needed C volatile semantics.** User bindings observed after a longjmp and GC root-slot pointers are emitted with the required volatile lifetime boundary. A mutation-before-throw regression verifies the value remains defined after catch.
6. **`return`, `break` and `continue` originally failed closed across `finally`.** Pending-finally lowering now executes cleanup in inner-to-outer order before the control transfer. Cleanup executes outside the corresponding protected exception frame, so cleanup exceptions propagate outward correctly.
7. **Incremental major collection required mutation safety.** Root rescanning, an object write barrier and mark-on-allocation rules prevent new edges/objects from being lost during an active major mark.
8. **Minor tracing could recurse forever through a remembered old-object cycle.** Old remembered objects now use the mark bit as a scan guard during minor collection; a two-old-object cycle regression exercises this path.
9. **Concurrent sweep initially risked allocator-counter races.** Dead objects are synchronously detached/accounted before worker handoff; the optional sweep thread only physically frees detached memory and does not mutate allocator counters.
10. **Generic aggregate inference did not accept explicit `Box[int]` declarations.** Explicit local generic aggregate annotations now instantiate the same deterministic specialization used by constructor inference.
11. **Native support C emitted volatile-qualifier warnings after the unwind fix.** The internal root-push slot is now `volatile void *`; the support runtime compiles cleanly under `-Wall -Wextra -pedantic`.

## ABI design assessment

The six features now share a coherent managed-reference model instead of introducing backend-specific ownership rules. `SagaRef` is the graph identity used by classes, collections, owned text and managed Option/Result payloads. Exception frames own a GC root mark, and generic aggregate specializations receive concrete nominal identities/type ids.

Virtual dispatch is deliberately a **closed-world application graph** in 0.35. It is deterministic and separately compiled, but it is not an open-world plugin/dynamic-class ABI. The class/interface graph is part of the build invalidation key.

The collector is accurately described as **generational + incremental major marking + optional concurrent physical sweep**. It must not be described as fully concurrent tracing, compacting, parallel, hard-real-time, or a production low-pause collector without additional evidence.

## Regression and executable evidence before final source freeze

The complete Python test inventory was executed in bounded per-module runs: **389 / 389 PASS across 34 test modules**. This includes the new Native Runtime 0.35 regression module (**10 / 10 PASS**) and all retained historical language/native/review/security modules.

Additional executable evidence:

- Python Self Conformance: **48 / 48 PASS**.
- Go Self Conformance: **48 / 48 PASS**.
- Python ↔ Go differential conformance: **48 / 48 PASS**.
- Module graph conformance: **14 / 14 PASS**.
- Native Runtime ABI 0.35 qualification: **10 / 10 PASS**.
- Native Codegen qualification: **17 / 17 PASS**.
- Go implementation: `go test ./...` and `go vet ./...` PASS.
- Native installer: `go test ./...` and `go vet ./...` PASS.
- Parser fuzz: **100,000** cases; expression fuzz: **25,000** cases; unexpected host exceptions: **0**.
- Native support runtime + owned text + GC + exception harness under AddressSanitizer/UndefinedBehaviorSanitizer: PASS with no sanitizer report.
- Linux x86-64 offline installer: embedded-payload verification, clean temporary install, `Saga Native 0.35.0`, and installed Self Conformance **48 / 48 PASS**.
- Go Native/Runtime cross-builds produced for Linux amd64/arm64, Windows amd64/arm64, and macOS amd64/arm64. Installer cross-builds produced for Linux amd64/arm64 and Windows amd64/arm64.

## Remaining explicit preview boundaries

- open-world/dynamically loaded subclass extension is not part of the 0.35 dispatch ABI;
- generic inheritance remains fail-closed;
- generic methods remain fail-closed;
- cross-module generic-template instantiation remains fail-closed;
- nested Option/Result descriptors are not stored directly inside list/map/set/object heap slots;
- concurrent marking, compaction and hard real-time pause guarantees are not claimed;
- Windows/macOS native runtime *physical execution* of ABI 0.35 was not performed in this Linux review environment; cross-compilation is not a substitute for physical qualification.

These are intentionally documented limitations, not hidden fallback paths.
