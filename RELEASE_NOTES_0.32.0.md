# Saga 0.32.0 — Native Codegen ABI Preview

Saga 0.32 introduces the first direct cross-module native function ABI.

## Highlights

- Each supported top-level Saga function is compiled to a linker-visible native
  machine-code symbol.
- Cross-module Saga calls are ordinary native relocations resolved by the OS
  linker; the Go Standard Runtime is not linked in the `codegen` profile.
- Stable ABI 0.32 value classes: checked `int64`, `bool`, and `unit` return.
- Per-module `.nabi.json` and `.nabi.h` artifacts.
- ABI-aware incremental object rebuild and link skipping.
- Left-to-right Saga argument evaluation preserved across direct native calls.
- Recursion, conditionals, loops, range iteration, checked arithmetic,
  short-circuit logic and Natural local bindings in the direct subset.
- Unsupported Standard Core semantics fail closed.

The complete Standard Core remains available through `standard` and `object`.
Native Codegen 0.32 is a deployment/codegen ABI preview, not a claim that all
Standard Core values and runtime facilities are directly lowered yet.
