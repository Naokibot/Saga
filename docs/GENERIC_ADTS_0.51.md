# Saga 0.51 Generic Algebraic Data Types

Saga 0.51 extends the existing tagged-enum and exhaustive-match core with generic algebraic data types (ADTs).

```saga
enum Maybe[T] {
    None,
    Some(T)
}

let inferred = Maybe.Some(42)       // Maybe[int]
let empty: Maybe[int] = Maybe.None // contextual type for a nullary variant

match inferred {
    case Maybe.Some(value) { print(value) } // value: int
    case Maybe.None { print(0) }
}
```

## Type inference

Payload-bearing constructors infer type arguments by unification. If a constructor cannot determine every enum parameter from its payload, an expected type may complete the mapping:

```saga
enum Either[L, R] { Left(L), Right(R) }
let value: Either[int, text] = Either.Left(7)
```

A generic nullary variant has no payload from which to infer parameters, so it requires a contextual type. This is rejected intentionally:

```saga
let value = Maybe.None // SAGA-T113
```

## Match typing

Exhaustive matching remains mandatory when no `default` is present. Payload bindings are specialized from the matched value, so `Maybe[int]` makes `Some(value)` bind `value` as `int`, not `any` or an unresolved type variable.

## Compatibility

Non-generic enums keep their 0.50 behavior and runtime representation. Type parameters are compile-time information and do not change the existing tagged-value runtime layout. Namespaced source modules and `.smi.json` interfaces preserve enum type parameters as ABI-significant metadata.
