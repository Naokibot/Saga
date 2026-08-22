# Language synthesis in Saga 0.45

Saga 0.45 closes a portability gap between the reference implementation and the independent Go implementation and turns a focused set of advanced constructs into one coherent Saga surface.

## What is new

### Async code without a second language model

```saga
async fn double(value: int) -> int {
    return value * 2
}

let pending: future[int] = double(21)
print(await pending)
```

The body still returns `int`; callers see `future[int]`. This keeps async code statically explicit without introducing callback-only APIs.

### Structured lifetime for concurrent work

```saga
taskgroup {
    refresh_cache()
    refresh_index()
}
print("both finished")
```

The group cannot be left while its Saga async work is still outstanding.

### Deterministic cleanup

```saga
fn answer() -> int {
    defer print("cleanup")
    return 42
}
```

`defer` runs LIFO on scope exit. `using` gives external/native resources a deterministic lifetime even though ordinary Saga memory remains managed.

### Explicit transfer only where it pays off

```saga
use task
var pool = task.pool(1)
task.shutdown(move pool)
pool = task.pool(1)
task.shutdown(move pool)
```

Saga does not impose ownership syntax on every value. `move` is focused on native/resource handles where double ownership or use-after-close is meaningful.

## Why this is Saga rather than a feature checklist

The features are intentionally connected to existing Saga rules:

- async results are ordinary static `future[T]` types;
- structured concurrency keeps isolated-agent semantics rather than creating implicit shared mutable state;
- resource transfer is checked without replacing Saga's garbage-collected value model;
- public async APIs are represented in the deterministic module ABI;
- new words are contextual so older source is not broken merely because it used a common word as a name;
- capability checks still decide whether hosted I/O authority exists.

This preserves the language's differentiating combination: readable source, static accountability, exact values, explicit authority, expressive scopes/pipelines and portable implementation boundaries.

## Influences and deliberate non-goals

The profile takes inspiration from Python's low ceremony, Ruby's readable scoped style, Go's structured cleanup/concurrency, Rust's explicit resource transfer, and Swift/Kotlin's async source shape. It deliberately does **not** copy their incompatible object models, null models, macro/metaprogramming systems, raw pointer models or package semantics.

The result is one Saga model rather than several foreign models bolted together.
