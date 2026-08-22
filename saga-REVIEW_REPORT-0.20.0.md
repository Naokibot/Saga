# Saga 0.20.0 SH-3 Review Report

## Review conclusion

The official `saga-sh3` implementation now satisfies the published SH-3 gate.
The previous Go semantic kernel is no longer part of the official SH-3 runtime
path; it is retained only as a reference implementation.

## Boundary reviewed

Canonical Saga sources:

- `selfhost/sh3/sh3c.saga`
- `selfhost/sh3/kernel.saga`

Allowed non-Saga bootstrap:

- `bootstrap/sh3/sh3vm.c`
- `bootstrap/sh3/launcher.c`
- published `bootstrap/sh3/stage1.sbc`

The C bootstrap was reviewed to ensure it exposes generic VM/value/text/list/file
primitives rather than Saga lexical, parser, type, class, generic, option/result
or Standard Core policy.

## Defects found and fixed

1. Associated type declarations in classes could make the type scanner consume
   past a semicolon/closing brace and hang. `;` and `}` are now valid type-scan
   boundaries.
2. Unary `await` returned a `future` wrapper instead of its value on the SH-3
   path. Future unwrapping now matches the Edition 2027 behavior.
3. Compute IR reference execution used an obsolete helper spelling and then fed
   exact IR constants into float arithmetic. The helper and numeric-flavor
   normalization were corrected.
4. Malformed hex bytecode validation allocated output before fully checking the
   input. Validation now happens before allocation.

## Evidence quality

The qualification runner independently rebuilds Stage2 and Stage3, lowers the
kernel through both compilers, runs Standard Core and Edition 2027 corpora,
tests the source loader/lowering path and verifies an empty-PATH distribution.
The source-boundary audit is fail-closed.

ASan/UBSan was also used on the C bootstrap. Valid-language execution shows no
sanitizer findings, and 500 malformed bytecode inputs showed no memory-corruption
or undefined-behavior finding.

## Remaining non-SH-3 work

Reference Go/Python implementations, optional graphics backends, platform FFI
shims and hardware adapters remain valuable independent/host implementations.
They are not part of the official SH-3 language semantic kernel and are not
relabelled as Saga source.
