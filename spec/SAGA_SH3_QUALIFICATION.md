# Saga SH-3 All-Source Self-Hosting Qualification — 0.20.0

**Status: QUALIFIED for the official `saga-sh3` implementation.**

SH-3 is the strongest Saga self-hosting profile. It means that the official
implementation's language semantics are canonically implemented in Saga source,
not merely that a compiler driver happens to be written in Saga.

## Required canonical Saga responsibilities

The official SH-3 implementation SHALL define in canonical `.saga` source:

1. lexical analysis and Unicode/source validation;
2. parsing and declaration/expression control structure;
3. static semantic/type/safety checks;
4. Standard Core runtime semantics and built-ins;
5. Edition 2027 Preview language semantics claimed by the release;
6. classes/interfaces/generics/associated types, option/result, resources,
   structured task/actor semantics and deterministic core values;
7. source-unit/project-root loader semantics needed by the compiler/runtime;
8. deterministic user lowering/token-image generation;
9. the bootstrap compiler/lowering driver itself.

For 0.20.0 the canonical sources are:

- `selfhost/sh3/sh3c.saga`
- `selfhost/sh3/kernel.saga`

## Bootstrap exception

A small bootstrap substrate may remain non-Saga only when it is
language-neutral. The 0.20.0 bootstrap boundary is:

- `bootstrap/sh3/sh3vm.c` — dynamically tagged generic stack/list/text VM;
- `bootstrap/sh3/launcher.c` — sibling-image launcher only;
- `bootstrap/sh3/stage1.sbc` — published bootstrap compiler image.

The C sources may implement generic machine operations, memory/value handling,
host argv/file primitives and bytecode loading. They SHALL NOT implement Saga
lexing, parsing, type/class/generic/option/result/resource semantics or Standard
Core policy.

## Qualification evidence required for 0.20.0

A release claims SH-3 only when all gates pass:

- strict C11 bootstrap build;
- Stage1 -> Stage2 and Stage2 -> Stage3 compiler rebuild;
- byte-identical Stage2 and Stage3 compiler images;
- Stage2 and Stage3 independently compile the canonical Saga kernel to
  byte-identical output;
- Standard Core success corpus: 23/23;
- Standard Core diagnostic corpus: 11/11 with stable diagnostic IDs;
- Edition 2027 Preview corpus: 14/14 through the canonical Saga kernel;
- canonical source-unit loader test;
- deterministic Saga-written SH3IMG1 user lowering and execution;
- empty-PATH official distribution execution;
- empty-PATH `sagac` self-host compiler execution;
- static source-boundary audit of every non-Saga official bootstrap source.

Reference Go and Python implementations are retained for differential testing,
portability and regression work. They are explicitly outside the official SH-3
execution kernel and do not weaken or replace the canonical Saga sources.

## What SH-3 does not claim

SH-3 is a source/self-hosting property. It does not by itself claim that every
optional operating-system adapter, graphics driver, FFI shim, vendor SDK or
third-party package is written in Saga. Such host adapters are outside language
semantics and remain separately qualified by their own profiles.
