# Saga 0.20.0 Feature Audit

## Language

Standard Core 1.0 RC1 and Edition 2027 Preview remain available. Edition 2027
includes float/fixed integers, generic constraints and associated types,
result/option propagation, resource/move safety, async/await, derive/comptime,
unsafe FFI gating, actors and compute IR.

## SH-3

**QUALIFIED** for the official `saga-sh3` implementation.

- compiler/lowering: canonical Saga source;
- lexer/parser/checker/runtime/built-ins: canonical Saga source;
- source loader/user lowering: canonical Saga source;
- Standard Core: 23 success + 11 diagnostic cases pass;
- Edition 2027: 14/14 passes through the SH-3 kernel;
- compiler Stage2/Stage3: byte-identical;
- kernel lowering from Stage2/Stage3: byte-identical;
- official Linux x86-64 runtime: static, empty-PATH verified.

## Reference implementations

The Go and Python trees are retained as non-official reference implementations.
Their presence in the source repository does not place them in the official SH-3
execution path.
