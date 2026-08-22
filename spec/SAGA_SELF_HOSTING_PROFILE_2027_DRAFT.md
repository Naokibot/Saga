# Saga Self-Hosting Profiles — 2027 Draft

## SH-1 Operational Independence
Normal installation and execution can operate without another programming
language runtime/toolchain being installed on the end-user host.

## SH-2 Saga Compiler Fixed Point
The compiler is canonical Saga source and reaches a byte-identical Stage2/Stage3
fixed point from the same compiler source.

## SH-3 All-Source Self-Hosting
The official language implementation's lexer, parser, static semantics,
code/lowering logic and language runtime semantics are canonical Saga source. A
minimal published language-neutral bootstrap machine may remain, but it may not
contain Saga grammar/type/runtime policy.

## Saga 0.20.0 status

The official `saga-sh3` implementation qualifies for **SH-1 + SH-2 + SH-3**.

Canonical Saga sources:

- `selfhost/sh3/sh3c.saga`
- `selfhost/sh3/kernel.saga`

Published language-neutral bootstrap:

- `bootstrap/sh3/sh3vm.c`
- `bootstrap/sh3/launcher.c`
- `bootstrap/sh3/stage1.sbc`

Go and Python implementations are non-official references retained for
independent/differential conformance testing.
