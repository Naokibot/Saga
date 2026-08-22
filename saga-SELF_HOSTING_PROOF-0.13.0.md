# Saga 0.13.0 — self-hosting proof

## Result

**PASS — fixed-point compiler self-hosting.**

Official compiler source:

- `selfhost/sagac.saga`

Published Linux x86-64 Saga Native Stage0 built the compiler in three stages:

1. Stage0 -> Stage1 from the Saga compiler source;
2. Stage1 -> Stage2 from the same source;
3. Stage2 -> Stage3 from the same source.

Stage2 and Stage3 were byte-identical.

```text
Stage2 SHA-256:
efade3e00f804b0ec49e3c5b2446d4ea2cb9d60212775a2852a0d24e1cfaeabf

Stage3 SHA-256:
efade3e00f804b0ec49e3c5b2446d4ea2cb9d60212775a2852a0d24e1cfaeabf
```

Compiler payload SHA-256:

```text
c6376197819f226b627af7c66a758af23e91a6e065d466e682618e5e3b3fa552
```

The native installer repeats this fixed-point build on the target machine. It
installs Stage2 as the official `sagac` only after Stage2/Stage3 equality is
verified. A mismatch fails installation.

## Installed-toolchain proof

The installed self-hosted compiler was used, with external language toolchains
removed from `PATH`, to build a Saga program containing:

- a generic interface;
- a generic implementing class;
- a stateful lexical closure.

The standalone application printed:

```text
41
42
```

The built application also ran with an empty/nonexistent PATH.

## Trust boundary

This proof establishes compiler-level self-hosting: the official compiler
program is Saga source and reaches a reproducible fixed point.

The Saga Native execution kernel remains a separately audited bootstrap/runtime
substrate. Its seed source is currently published under `implementations/go/`.
As with a self-hosted compiler running on a VM or runtime, that kernel is not an
end-user dependency on the Go toolchain: released Saga Native binaries are
self-contained and statically linked on Linux.

This document intentionally does **not** claim that every source file of the
runtime kernel has been rewritten in Saga. That stronger claim is distinct from
compiler self-hosting and remains outside the 0.13.0 self-hosting profile.
