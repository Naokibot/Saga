# Saga 0.34.0 Review Report

## Review scope

This review treats 0.34 as a native runtime/ABI change, not a syntax-only release. The review covered source semantics, Python/Go parity, C ABI layout, incremental invalidation, object graph tracing, root lifetime, allocator reuse, fail-closed boundaries, and regression against previous Saga releases.

## Findings fixed during implementation

1. Payload enums initially existed only in parser/checker work; interpreter, Go implementation, SMI, native ABI, and GC tracing were completed so the feature does not split by backend.
2. Native GC roots originally stored only `SagaRef *`; tagged values carrying managed payloads would therefore not keep those payloads alive. Typed root entries and tagged payload scanning were added.
3. Lexical reference locals could leave root entries pointing at expired C stack slots after nested-block exit or loop control flow. Compiler-emitted root marks now unwind on normal exit, `break`, `continue`, and `return`.
4. Private class layout changes were initially at risk of looking source-private while still changing constructor/native field offsets. Native class ABI records the complete layout and invalidates importers.
5. Python and Go module interfaces previously represented nullary enum variants as sorted strings. Tagged-union discriminants make declaration order ABI-significant, so 0.34 uses ordered `{name,payload}` records in both implementations.
6. The Go runtime stored enum definitions by value, so exported module enum identity was not propagated to function closures. The exported enum cell is now namespace-qualified so module-returned tagged values match importer patterns.
7. Native collection/object display was deliberately kept fail-closed where the generic heap printer could not preserve reference-runtime observable formatting.

## Design assessment

The resulting design is coherent for a preview: all directly native aggregate references share one managed-reference model, and tagged unions use explicit payload metadata rather than ad-hoc object boxing. This gives later GC and optimizer work one graph representation.

The current collector prioritizes correctness and debuggability over latency. It should not be described as a production concurrent collector.

## Final regression status

Before final artifact packaging, the non-platform Python inventory passed **369 / 369**, and the source-manifest-bound Platform/Evidence inventory passed **9 / 9**, for **378 / 378** Python regression tests. Python and Go Self Conformance both pass **48 / 48**; Python ↔ Go differential conformance passes **48 / 48**; module graph conformance passes **14 / 14**; Native Aggregate/GC qualification passes **12 / 12**; and fuzzing completed 125,000 cases with zero unexpected host exceptions.

## Remaining high-priority work

- class inheritance/interface/virtual dispatch ABI;
- generic aggregate monomorphization;
- managed Option/Result descriptors;
- owned native text integrated with the managed heap;
- exception unwinding with managed roots;
- generational/incremental/concurrent GC work;
- stronger randomized GC/object-graph stress tests;
- Windows COFF and macOS Mach-O physical qualification for the new aggregate ABI.

## Follow-up review — 2026-08-16

A second source-level review found three release-quality defects that were not covered by the original 0.34 regression inventory.

1. `saga_map_put` read map metadata before validating the `SagaRef`. A C client passing `NULL` therefore crashed with a host segmentation fault instead of a Saga runtime diagnostic. Collection ABI entry points now validate references and element/key kinds before dereferencing them; set intersection also rejects incompatible element descriptors.
2. The offline installer still identified itself as 0.24.1 while packaging a 0.34.0 native runtime. The installer version is now 0.34.0, and release builds inject the release version with Go linker flags so the post-install version check cannot silently drift from the packaging script.
3. Source-only installer builds failed because `//go:embed payload/*` required generated release binaries. Payload embedding now lives behind the `saga_installer_payload` build tag, with a source-only empty FS for tests. The release builder enables the tag after populating the payload.
4. The `sagaruntime` build excluded `lsp.go`, but a shared FFI path depended on `maxInt` defined inside that LSP-only file. The helper is now in a build-independent source file, allowing the runtime profile to compile without the LSP.

The follow-up changes do not expand the 0.34 language surface. They harden the existing C ABI and repair release/installer reproducibility.

