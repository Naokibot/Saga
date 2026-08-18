# Saga 0.45.0 — Language Synthesis Profile

Saga 0.45 promotes a focused cross-language synthesis surface into the common Python/Go language model while preserving Saga's own semantics.

## Added

- Common `async fn` / `await` typing and execution; an async declaration returning `T` is called as `future[T]`.
- Lexical `taskgroup` structured-concurrency joining for Saga async calls.
- LIFO `defer` cleanup on fallthrough, return and error paths, including first-class closures.
- `using name = resource { ... }` deterministic resource lifetime.
- Resource-focused `move` with static and runtime use-after-move rejection and mutable reinitialization support.
- Contextual treatment of `async`, `await`, `defer`, `using`, `taskgroup` and `move` to preserve ordinary identifier compatibility.
- Common `.smi.json` encoding of public async APIs as `future[T]`, with Python/Go ABI agreement tests.
- Common hosted `task.pool`, `task.submit`, and `task.shutdown` support in the Go implementation to match the reference implementation.

## Compatibility

The exact-number model, option/result semantics, capability security, modules, native ABI/runtime, machine/drone profiles, and Saga 0.44's 4 kHz hosted-control facilities are retained.

The new resource ownership facility is intentionally narrow: Saga remains a managed-memory language and does not add a general borrow checker or raw-pointer memory model.

## Qualification boundary

`async`, `taskgroup`, and task pools provide structured hosted concurrency semantics, not a hard-real-time scheduling guarantee. The 4 kHz physical-I/O and certified-motion boundaries documented in 0.44 remain unchanged.
