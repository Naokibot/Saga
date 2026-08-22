# Saga Native Value ABI 0.33

Status: Preview, release 0.33.0.

## Purpose

ABI 0.33 extends the direct native function ABI introduced in 0.32 without
changing its core promise: a supported Saga function is emitted as an ordinary
linker-visible machine-code symbol and cross-module calls are native relocations.
Unsupported value semantics fail closed instead of silently falling back.

## Stable value representations

### `int`
Signed checked 64-bit integer in the direct ABI.

### `bool`
`uint8_t`, canonical values 0 and 1.

### `unit`
Stable as a return value. Unit parameters remain outside this ABI revision.

### `text`
Immutable borrowed UTF-8 slice:

```c
typedef struct {
    const uint8_t *data;
    uint64_t len;
} SagaText;
```

The ABI does not transfer ownership. A caller must keep borrowed input storage
alive for the duration required by the callee. String literals returned by a
compiled module reference static module storage. Owned dynamically allocated
text is intentionally deferred until the Saga native allocator/GC ABI.

### `option[T]`
For `T` in `{int,bool,text}`:

```c
typedef union { int64_t i64; uint8_t boolean; SagaText text; } SagaValue;
typedef struct { uint8_t present; SagaValue value; } SagaOption;
```

`present == 0` means `none`; `present == 1` means `some`.

### `result[T,E]`
For `T,E` in `{int,bool,text}`:

```c
typedef struct { uint8_t ok; SagaValue value; } SagaResult;
```

`ok == 1` selects the success payload and `ok == 0` the error payload. The
function signature recorded in `.nabi.json` determines the active union field.

## `?` propagation

For an `option[T]`, postfix `?` returns `none` from the current compatible
option-returning function when absent and otherwise unwraps `T`.

For `result[T,E]`, postfix `?` returns the existing `Err(E)` from the current
compatible result-returning function and otherwise unwraps `T`. The error type
must match statically.

## Native symbol identity

Public and internal supported top-level functions keep the deterministic ABI
symbol scheme `saga_abi033_m<module>_f<function>`, where source names are UTF-8
byte encoded into a path-independent symbol component.

## C interoperability

Each native module emits `.nabi.json` and `.nabi.h`. Headers include
`saga_native_abi033.h`; clients must compile against the matching support ABI.
The manifest records exact parameter/result descriptors and the public ABI hash.

## Explicit non-goals

ABI 0.33 does not stabilize native layout for enums/tagged unions, classes,
interfaces, objects, closures, collections, exceptions, arbitrary precision
integers, exact rational division, hosted APIs, owned strings or GC-managed
values. Such use in direct codegen is a compile-time failure.
