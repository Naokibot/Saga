# Saga 0.33.0 Review Report

## Review goal

Freeze the previously partial 0.33 Human-Centered Native Value work into a
reproducible release candidate without hiding regressions behind new syntax.

## Implemented surface

### Human-centered common language

- `enum` with nominal variant values.
- exhaustive `match`; missing variants are rejected with `SAGA-T112`.
- `unless` as syntax normalized to `if not`, avoiding a second runtime model.
- public enum identity through namespaced modules and `.smi.json` interfaces.

### Native Value ABI 0.33

- borrowed immutable UTF-8 `SagaText`.
- `SagaOption` for payloads `int`, `bool`, `text`.
- `SagaResult` for success/error payloads `int`, `bool`, `text`.
- direct native `some/none/ok/err`, unwrap operations and compatible postfix
  `?` propagation.
- generated `.nabi.json`/`.nabi.h` descriptors and C interoperability.

## Bugs found and fixed during finalization

1. **Go public enum SMI validation** — public enum types were accidentally
   rejected as internal types by the Go public-surface validator. Public enums
   are now included in the exportable nominal set.
2. **Go `unless` typed-nil panic** — a nil `*Block` stored in a `Stmt` interface
   made the checker believe an else branch existed, leading to a panic. The
   parser now stores an actually nil `Stmt` when no else branch is present.
3. **Native regression assumptions** — historical direct-codegen regression
   tests still asserted that `text` was unsupported. They now preserve the old
   scalar/link/incremental guarantees while using object/class ABI as the
   intentional fail-closed boundary.
4. **External C include path** — ABI 0.33 generated headers include
   `saga_native_abi033.h`; the qualification and regression harnesses now pass
   the support include directory explicitly.

## Design review

The release deliberately chooses progressive disclosure over feature count.
`unless` reduces reading friction but normalizes to existing semantics. Enum
matching improves readability while adding compile-time completeness checking.
Native text is borrowed rather than pretending an ownership/GC ABI exists.
Unsupported managed layouts remain compile-time errors.

This direction is influenced by the human-centered, programmer-happiness
tradition associated with Ruby, but Saga neither copies Ruby's dynamic runtime
semantics nor claims endorsement by Yukihiro Matsumoto. Saga keeps static
contracts, capability boundaries, deterministic module ABI and native
compilation as independent design commitments.

## Remaining priority work

- owned Native Text + allocator/GC;
- native enum/tagged-union layout;
- list/map/set ABI;
- object/class/interface layout and dispatch;
- closure environment ABI;
- exception/unwind ABI;
- generic monomorphization;
- native async/structured concurrency;
- HIR/MIR/SSA optimizer pipeline.

Therefore 0.33 remains a preview rather than Saga 1.0 GA.
