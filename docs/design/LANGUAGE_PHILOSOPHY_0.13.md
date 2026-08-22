# Saga 0.13 language philosophy

Saga is designed around **progressive depth**: the first useful program should
require very few concepts, while large programs should not have to abandon the
language for stronger abstraction, type safety, concurrency, or deployment.

## 1. Stability first

- `let` is immutable by default; mutation is explicit with `var`.
- Numeric meaning is deterministic: decimal literals are exact decimals and
  integer division can preserve rational values instead of silently rounding.
- Conditions require `bool`; there is no implicit truthiness.
- Missing values use `option[T]` rather than ambient null.
- Generic types are invariant unless the specification explicitly says
  otherwise.
- Diagnostic IDs are stable API. Human wording may improve without breaking CI.
- Minor implementation releases may fix bugs but do not silently change valid
  Standard Core programs into programs with different observable meaning.

## 2. Easy at the beginning

A beginner only needs:

1. `let` and `var`
2. exact numbers and text
3. lists
4. `if` and `for`
5. functions

Top-level code is legal, so a `main` class or ceremony is not required.

```saga
let name = "Saga"
print("Hello,", name)
```

## 3. Depth is opt-in, not removed

When a program grows, Saga provides concepts associated with deeper languages:

- explicit static types and contracts;
- lexical scope and stateful closures;
- classes, inheritance, interfaces, abstract classes and polymorphism;
- generics with static checking;
- annotations and reflection metadata;
- exceptions and `option[T]` for two different failure/missing-value models;
- isolated concurrency and deterministic value-copy boundaries;
- packages, locking, verification and standalone native distribution;
- a self-hosted compiler fixed point.

The design rule is that none of these are prerequisites for a small program.

## 4. Avoid accidental complexity

Saga intentionally does not require manual memory management, pointer arithmetic,
header files, ownership/lifetime syntax, checked/unchecked integer mode switches,
or build-system boilerplate for ordinary programs. Those mechanisms can be
valuable in systems languages, but Saga's goal is to preserve their **depth of
abstraction and control** without making them the entry ticket to programming.

## 5. One language, three learning surfaces

`Saga new` exposes the same language at three starting levels:

- `beginner`: values and output;
- `standard`: functions and collections;
- `advanced`: interfaces, generics and architecture.

This is tooling guidance only. There are not three incompatible Saga dialects.
Every level uses one grammar and one Standard Core specification.
