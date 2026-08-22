# Saga 0.13.0 — language design: simple entrance, deep ceiling

Saga 0.13.0 targets three properties at the same time: stability, writability,
and learnability. Depth is preserved by progressive disclosure rather than by
forcing advanced mechanisms into small programs.

## A beginner can start here

```saga
let name = "Saga"
print("Hello,", name)
```

No main class, headers, ownership syntax, pointer declaration or project build
script is required for an ordinary first program.

## Local code favors clarity

- `let` is immutable by default; mutation is explicit with `var`.
- local types can usually be inferred;
- conditions are real `bool` values, not implicit numeric/text truthiness;
- decimal literals are exact decimals;
- integer division can retain rational meaning;
- expected absence is `option[T]`, not ambient null.

## Architectural depth is available

Saga Language Edition 1.0 Draft includes:

- static types and runtime boundary contracts;
- lexical functions and stateful closures;
- classes and private state;
- inheritance and polymorphism;
- interfaces and abstract classes;
- generic functions and classes;
- generic `extends` and `implements` relations;
- invariant generic contracts;
- annotations and reflection metadata;
- exceptions and `option[T]` as separate error/absence models;
- isolated tasks and explicit value-transfer boundaries;
- deterministic package locking and standalone builds.

Example:

```saga
interface Repository[T] {
    fn save(value: T) -> T
}

class MemoryRepository[T](let initial: T) implements Repository[T] {
    override fn save(value: T) -> T = value
}

fn store[T](repository: Repository[T], value: T) -> T {
    return repository.save(value)
}

let repository: Repository[int] = MemoryRepository(0)
print(store(repository, 42))
```

## One language, progressive learning

The official Native toolchain provides:

```text
saga new project --level beginner
saga new project --level standard
saga new project --level advanced
saga learn
saga explain SAGA-T103
saga repl
```

These are not separate dialects. All levels compile under one grammar and one
Standard Core.

## Stability tools are part of the language experience

```text
saga fmt
saga lint --standard
saga test
saga check
saga build
```

Machine diagnostics use stable IDs independently of translated wording.
Standalone builds are reproducible under the deterministic build profile, and
the self-hosted compiler is accepted only after a Stage2/Stage3 fixed point.

## Why this can be deep without becoming C or Java syntax

Saga takes the architectural depth of large statically typed languages—generic
abstraction, explicit contracts, encapsulation, polymorphism, deterministic
builds and concurrency semantics—without requiring manual memory management or
class ceremony for every small program.

Raw pointer arithmetic and manual `free` are intentionally not the mechanism by
which Saga provides depth. Depth is expressed through types, interfaces,
encapsulation, exact values, controlled effects, packages and concurrency.
