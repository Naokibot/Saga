# Saga 1.0 style guide — draft

This guide is intentionally smaller than the language. It optimizes ordinary
code for readability while leaving advanced facilities available.

## Local code

- Prefer `let` and inferred local types.
- Use `var` only when the state really changes.
- Prefer short functions with explicit names over clever expression chains.
- Use exact `decimal`/`rational` semantics rather than encoding money or ratios
  through binary floating-point assumptions.

## Public boundaries

- Write parameter and return types on public functions and methods.
- Use `option[T]` for an expected absence; use exceptions for an operation that
  failed rather than merely returned no value.
- Put mutable state behind a class method or closure instead of exposing a
  mutable field without a reason.
- Introduce an interface when there are multiple implementations or a real
  architectural boundary, not for every class.

## Generics

- Start with a concrete function. Generalize to `[T]` when callers genuinely
  need more than one type.
- Generic class and interface arguments are invariant in Saga 1.0 Draft.
- Typed `extends` and `implements` relations should preserve domain meaning;
  avoid inheritance used only to share a few lines of code.

## Concurrency

- Prefer isolated tasks and value transfer.
- Do not treat scheduling order as program state.
- Keep native resources at the task that owns them.

## Learning rule

A beginner should be able to read the first 20 lines of a project without
understanding generics, inheritance, annotations, reflection or concurrency.
Architecture may be deep; entry points should remain obvious.
