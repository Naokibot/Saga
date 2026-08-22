# Saga C ABI / FFI Profile 1 Draft

This is an optional Expert profile and is not Standard Core.

- Every foreign call occurs inside `unsafe`.
- `extern "C" fn` requires `@link(library,symbol)` in the Native dynamic-link profile.
- The validated scalar ABI supports signed 64-bit integer and IEEE binary64 calls with at most four scalar arguments in the current reference backend.
- `int64` is the preferred portable C integer boundary type. Saga arbitrary-precision `int` is accepted only by the compatibility path after range validation.
- Foreign pointers, structs, callbacks and ownership-bearing buffers are not silently inferred. They require future explicit ABI profiles.
- A build without the FFI profile must fail closed.

This restricted first profile avoids pretending that arbitrary C layouts or ownership rules are portable.
