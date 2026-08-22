# Saga Native Scalar JIT Profile 2027 — Preview

The optional `sagajit` implementation profile is an Expert/unsafe feature, not Standard Core.

Validated backend: Linux x86-64 System V ABI with cgo-enabled executable-memory allocation.

Current accepted function subset:
- expression-body Saga functions;
- zero to four `int`/`int64` parameters;
- `int`/`int64` result;
- integer literals and parameters;
- unary minus;
- `+`, `-`, `*`.

The backend writes code into RW pages and changes them to RX before invocation (W^X discipline). JIT handles are resources and can be deterministically closed. Unsupported constructs are rejected. A default build contains no executable-memory JIT backend and fails closed.
