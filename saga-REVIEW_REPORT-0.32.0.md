# Saga 0.32.0 Review Report — Native Codegen ABI

## Scope

This review evaluates the 0.32 direct native-function backend against the
language's existing Natural/Module/Native Object semantics. The review is not a
claim that Standard Core as a whole has been converted to direct machine code.

## Implemented architecture

The new `codegen` build profile performs these steps:

1. load and type-check the complete Saga source graph with the reference checker;
2. derive one Native ABI 0.32 interface per source module;
3. lower every supported top-level Saga function to a linker-visible C/native
   function symbol;
4. compile each source unit independently to a real relocatable object;
5. compile a small C ABI support object (checked arithmetic and primitive print);
6. link startup + module objects + support object with the host C linker.

The Go Standard Runtime archive used by `standard`/`object` is not linked.

## Review findings and fixes

### R32-01 — cross-module calls must be linker relocations

A codegen backend that still routed calls through the embedded Standard Runtime
would not meet the requested ABI goal. The final design emits an ordinary extern
prototype in the caller and the stable ABI symbol in the callee. `nm` evidence
shows `U <symbol>` in the importer and `T <symbol>` in the dependency.

**Status:** fixed and covered by regression/qualification tests.

### R32-02 — C argument evaluation order is not Saga evaluation order

Directly emitting `callee(first(), second())` would permit C to evaluate
arguments in an implementation-defined order. Saga requires left-to-right.
Arguments are now materialized into typed temporaries in source order before the
native call.

**Status:** fixed; effectful argument-order regression passes.

### R32-03 — inclusive range `continue` can skip termination logic

A bottom-of-loop termination test is unsafe if Saga `continue` lowers directly
to C `continue`. The direct backend now targets a generated continuation label,
then performs terminal-element detection and checked step update.

**Status:** fixed; `continue` on the terminal path is covered.

### R32-04 — C signed remainder differs from Saga

C `%` truncates toward zero, while Saga follows floor-remainder semantics.
Native ABI support now adjusts non-zero remainders when divisor/result signs
differ. `-5 % 3` evaluates to `1`.

**Status:** fixed.

### R32-05 — Natural first assignment initially had no native local declaration

`next = value + 1` is a legal inferred immutable binding when `next` does not
exist. The backend originally treated all `Assign` nodes as mutation. It now
uses lexical type state to distinguish first binding from later assignment.

**Status:** fixed.

### R32-06 — unsupported dependency initialization could be silently ignored

A module object containing top-level initialization cannot be compiled as
functions-only code without changing import-time semantics. Dependency modules
with non-declaration top-level statements are now rejected before link.

**Status:** fail-closed by design.

### R32-07 — `unit` parameter would produce an invalid C ABI

`void` is a return representation, not a value parameter representation. ABI
0.32 explicitly excludes unit-valued parameters and rejects them before C
emission.

**Status:** fail-closed by design.

### R32-08 — multi-argument print formatting must not silently change

The support ABI initially has primitive one-value print operations. Emitting
one native print per Saga argument would change `print(a, b)` from one logical
line to multiple lines. ABI 0.32 therefore lowers exactly one print argument and
rejects wider formatting until a stable text/formatting ABI exists.

**Status:** fail-closed by design.

## ABI design review

ABI-stable value representations in 0.32 are intentionally limited to:

- Saga `int` -> checked deployment `int64_t`;
- Saga `bool` -> `uint8_t`;
- Saga `unit` return -> C `void`.

The direct profile does not redefine Standard Core's arbitrary-precision int.
Overflow in the deployment subset terminates through the ABI support object.
Exact rational division, text, collections, classes, closures, exceptions,
result/option propagation, hosted modules and class methods remain outside this
ABI.

## Incremental compilation review

The direct object cache key includes source SHA-256, own public native ABI,
direct dependency native ABIs, target and compiler identity. This permits:

- body-only dependency change -> rebuild dependency object, reuse importer;
- public ABI change -> invalidate importer;
- no change -> no compile and no link;
- object tampering -> content-hash failure and rebuild.

Build publication remains under a cross-process build lock with atomic output
replacement.

## Native evidence boundary

On the available Linux x86-64 toolchain, qualification checks real ELF
relocatable objects, machine-code disassembly, direct undefined/defined symbol
pairing, external C linkage through generated `.nabi.h`, final executable output,
incremental invalidation and reproducible clean builds.

No physical Windows/macOS ABI 0.32 qualification was performed in this review.
Their code paths must not be presented as qualified until the same suite runs on
those hosts.

## Verdict

Native Codegen ABI 0.32 is a real direct-function codegen/link boundary for its
documented subset. It is not yet a complete direct-native implementation of all
Standard Core semantics. The honest release label is **Preview**.
