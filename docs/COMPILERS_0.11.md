# Saga 0.11 native and WebAssembly compilation

## Standard profile

```bash
saga build main.saga --target native --profile standard --output app
saga build main.saga --target wasm --profile standard --output app.wasm
```

The compiler links source units at build time and builds a standalone copy of the independent Go Standard Core implementation containing the program. No Python installation is required to execute the output. This **runtime-AOT** path preserves Standard Core semantics including lexical closures, arbitrary-precision/exact numbers, OOP, generics and exceptions.

The WASM output currently targets Go's `wasip1` port. The adjacent WIT file is a companion interface/adapter contract, not proof that the binary itself is a WebAssembly Component.

## Scalar profile

```bash
saga build main.saga --target native --profile scalar --output tiny
saga build main.saga --target wasm --profile scalar --output tiny.wasm
```

This path directly lowers a deliberately small int/bool/control-flow subset to C and then invokes clang. Unsupported semantics are rejected rather than silently changed.
