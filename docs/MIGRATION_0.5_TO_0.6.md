# Migrating Saga 0.5 programs to 0.6

## Add override to replacement methods

A method that implements an interface method or replaces a parent method must now be explicit:

```saga
class Child() extends Parent {
    override fn name() -> text = "child"
}
```

This prevents accidental replacement after a parent API changes.

## Use option[T] for absent values

JSON `null` and SQL `NULL` now become `none()` rather than leaking a host null value.

```saga
let value: option[text] = none()
print(unwrap_or(value, "fallback"))
```

ORM fields that can contain SQL NULL must use `option[T]`.

## Review JSON output

Decimals are emitted as exact JSON numbers. Nonintegral rational values, bytes, sets and unit require an explicit conversion. Duplicate object keys are rejected during decoding. Private fields are not serialized.

## Review collection keys

Map keys and set elements must be hashable Saga scalar types. Nested lists can still be deduplicated with `unique`, which no longer relies on host hashing.

## Review exponentiation

Exponentiation now follows mathematical precedence:

```saga
-2 ** 2      // -4
(-2) ** 2    // 4
2 ** 3 ** 2  // 512
```

The exponent must have an exact integer value at run time.

## Python requirement

The supported reference runtime is CPython 3.13 because Saga 0.6 fixes identifiers to Unicode 15.1.
