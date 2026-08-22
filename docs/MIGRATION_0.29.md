# Saga 0.29 Migration Guide

Saga 0.29 intentionally prioritizes the Natural Saga design over preserving every old spelling. The old core remains readable by the reference implementation where doing so does not create semantic ambiguity, but new code should prefer the natural surface.

## Safe automated migrations

Run:

```bash
saga migrate .
saga migrate . --write
```

Without `--write`, the command reports proposed changes. With `--write`, it writes only conservative rewrites and parses the migrated file before replacing it.

Currently automated when argument boundaries are simple and unambiguous:

- `transform(fn, values)` → `values.map(fn)`
- `filter(fn, values)` → `values.filter(fn)`
- `any(fn, values)` → `values.any(fn)`
- `all(fn, values)` → `values.all(fn)`
- `reduce(fn, values, initial)` → `values.fold(initial, fn)`
- `sort(values)` → `values.sorted()`
- `unique(values)` → `values.distinct()`

Nested or semantically different expressions are deliberately left unchanged rather than guessed.

## Binding migration

`let name = value` remains valid and remains the clearest spelling when immutability itself is important to the reader. For ordinary local setup, `name = value` is equivalent to an immutable first binding. Use `var` only when later mutation is required.

## Compatibility breaks allowed in this redesign

Natural 0.29 is allowed to remove or demote old features when they make the language less coherent. A compatibility spelling must not force the new grammar into ambiguity. Old native/Go binaries remain 0.28 implementations until they implement and pass the 0.29 differential suite.
