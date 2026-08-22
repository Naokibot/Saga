# Lightweight runtime architecture — Saga 0.14.0

Saga separates the **developer CLI** from the **application runtime**.

- `saga`: compiler/checker, formatter, linter, debugger, LSP, registry, code generation and package tooling.
- `saga-runtime`: the smaller execution/bundle runtime embedded into standalone Saga applications.

Both are Saga distribution artifacts and neither requires another programming-language runtime at use time. On Linux release builds they are statically linked. Standalone applications execute their verified embedded Saga bundle directly from memory instead of extracting source to a temporary directory.

The build cache keys the runtime plus canonical source payload. Rebuilding identical input reuses the prior deterministic application. Optimization occurs only after type checking, preserving diagnostics; current passes include constant folding and unreachable-branch elimination.
