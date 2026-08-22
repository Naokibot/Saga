# Saga Language Edition 2027 Preview

**Status:** implementation preview for public review and independent implementation. It is not an ISO/IEC publication or certification.

## Design rule: a small entrance, a deep ceiling

Edition 2027 extends the 1.0 RC1 core without requiring advanced syntax in introductory programs. `let`, inference, ordinary functions, lists and `if` remain sufficient for beginner programs. Advanced features are progressively disclosed and are designed to fail closed.

## Modules and visibility

A source unit may declare `module Name`. Importing such a file with `use "path.saga" as alias` creates a namespace instead of flattening its declarations. Only `public` top-level declarations are exported. `internal` is the default; `private` is reserved for implementation-local declarations. Qualified types use `alias.Type`. Public type identities in exported fields, methods, generic constraints, associated bindings and enum/function signatures are recursively qualified at the module boundary.

Legacy source units without `module` retain the 1.0 source-inclusion model. This preserves existing package layouts while allowing large projects to opt into namespacing.

## Numbers

The exact types `int`, `decimal` and `rational` retain their 1.0 semantics. Edition 2027 adds IEEE-754 `float32` and `float64`. Literal suffixes `f32` and `f64` are explicit. Exact and floating arithmetic do not mix implicitly. Conversion requires `float32(x)`, `float64(x)`, `decimal(x)` or `int(x)`.

Fixed-width boundary integer types are `int8`, `int16`, `int32`, `int64`, `uint8`, `uint16`, `uint32`, and `uint64`. Narrowing conversions range-check at runtime. Arithmetic on fixed-width integers promotes to arbitrary-precision `int`; overflow is therefore never silent.

## Generic constraints and associated types

A generic declaration may constrain a type parameter:

```saga
fn max[T](a:T,b:T)->T where T:Comparable { ... }
```

Multiple requirements use `+`. Standard semantic constraints are `Numeric`, `ExactNumeric`, `Float`, `Comparable`, `Hashable`, and `Send`; interfaces may also be constraints.

Interfaces may require associated types:

```saga
interface Source {
    type Item;
    fn get()->Item
}
```

A conforming class binds each requirement with `type Item = ConcreteType`. Generic code may refer to `T.Item` when `T` is constrained by the corresponding interface.

## Failure propagation

Postfix `?` unwraps `ok(v)`/`some(v)`. `err(e)` or `none()` returns immediately from the enclosing function. A `result` propagation site requires a compatible enclosing `result` error type; an `option` propagation site requires an enclosing `option` result.

## Resource safety

`resource class` declares a move-only lifetime-managed object. `move name` transfers a named resource binding. Reuse of the old binding is a static error. `using owned = expression { ... }` deterministically closes the resource after the block, including return/error paths. `defer expression` runs in LIFO order on lexical block exit.

Hosted native resources participate in the same deterministic-close model where supported.

## Structured concurrency

`async fn` calls return `future[T]`; `await` consumes a future. `taskgroup { ... }` owns futures created inside it and waits for all children before exiting. Failure marks remaining child futures cancelled before join.

The `task` module provides `await_timeout`, `cancel`, `cancelled`, bounded `channel`/`stream`, `send`, `recv`, `close`, serial `actor`, and `ask`. Cancellation in this preview is cooperative at the future result boundary; it is not arbitrary thread termination.

Task value transfer continues to use structural snapshots and the Send boundary. Resource handles, modules, channels and actor identities are not Send values unless a later profile explicitly says otherwise.

## Unsafe and C ABI

`unsafe { ... }` makes a foreign/native safety boundary visible in source. FFI APIs are unavailable outside that block. The optional `sagaffi` native profile supplies `use ffi`, dynamic-library symbol lookup, scalar `int64` and `float64` calls, and `extern "C"` declarations carrying `@link("library","symbol")`.

The default Native build fails closed: if the FFI profile is not built for the host, `ffi.available()` is false and foreign calls are rejected. No ambient shell or foreign pointer is exposed by the scalar profile.

## Derivation and compile-time functions

`@derive("Equal","Hash","Debug")` is compiler-recognized metaprogramming. It generates behavior semantically rather than textual source substitution, so it introduces no user-visible identifiers and is hygienic by construction.

`comptime fn` must have a pure expression body. Calls require compile-time constant arguments and are evaluated during optimization; the resulting value is inserted as a literal AST node. Hosted I/O, mutable state, async, extern and arbitrary runtime calls are excluded.

## Diagnostics 2

Human diagnostics show stable ID, source position, source line/caret, a plain-language reason, notes and targeted fixes where known. Unknown-name diagnostics may suggest a nearby visible spelling without changing the stable ID. JSON diagnostics use `saga.diagnostic.v2` and include a stable ID, primary flag, advice, fix records and dependent-error suppression count. Localized wording is not part of semantic conformance; stable IDs are.

## Edition compatibility

Projects select the edition in `saga.toml`. `language = "1.0"` remains accepted. `language = "2027"` opts into this preview contract. A source-level `edition 2027` marker is also accepted for standalone files. Edition changes may reserve new words, but a released edition's semantics are not silently changed by a newer compiler.

## Unicode

Edition semantics pin an identifier profile rather than following the host language's Unicode tables. The 0.18 implementation continues to use its audited vendored Unicode 15.1 XID/NFC data while the edition policy defines how a future edition can advance the table version without changing old source interpretation. UTF-8 validation, NFC enforcement and bidi-control rejection remain mandatory.

## Conformance

An implementation claiming Edition 2027 Preview shall declare which optional profiles it supports and shall pass the published 2027 conformance cases for every claimed feature. A project implementation, internal test or self-issued signature is not a third-party certification.

## Contextual evolution keywords

New 2027 words are parsed contextually where practical so older 1.0 source can continue to use names such as `async`, `resource`, `module`, and `await` in ordinary identifier positions. New syntax is recognized only in its defining shape (`async fn`, `resource class`, `unsafe { ... }`, etc.). This minimizes source breakage while the Edition mechanism remains the normative opt-in boundary.

## Experimental native scalar JIT

The optional Expert `sagajit` profile provides `use jit`. On the validated Linux x86-64/cgo backend it emits executable x86-64 machine code for a deliberately restricted pure `int`/`int64` expression-function subset (up to four scalar parameters; literals, parameters, unary minus, `+`, `-`, and `*`). Compilation and invocation require `unsafe`. The normal build is fail-closed and reports `jit.available() == false`.

This is a real machine-code execution path, but it is **not** a claim that arbitrary Saga programs are JIT compiled. Widening the JIT profile requires separate conformance vectors and architecture backends.

## Portable GPU compute IR

SIR1 now has both `stage fragment` and `stage compute`. Compute programs operate element-wise on a storage buffer with deterministic `scale`, `add`, and `clamp` operations. The same canonical IR can generate GLSL 4.50, HLSL 5, Metal Shading Language 2, or WGSL compute shader source; GLSL 1.20 is intentionally fragment-only. `game.shader_ir_compute_reference` executes the compute semantics on the CPU for deterministic conformance.

Backend source generation is portable language functionality. Actual GPU dispatch remains a renderer/device profile and must not be reported as physical-GPU validation without target evidence.

## Embedded Portable Profile

`build --target embedded-wasm` emits a freestanding WebAssembly library for the strict scalar subset. It has **no import section** and exports `public` Saga scalar functions directly. Top-level hosted work, `print`, async and extern functions are rejected rather than silently depending on an operating system. The target is intended as a portable firmware/RTOS embedding boundary, not as a claim that Saga already supplies a bare-metal kernel, linker script, board support package or device drivers.
