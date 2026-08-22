# SH-3 migration completion — Saga 0.20.0

The 0.19.0 migration plan is complete for the official `saga-sh3` implementation.

Completed migration:

1. Saga-owned lexer and Unicode/source scanner;
2. Saga-owned parser/evaluator;
3. Saga-owned static checker and safety preflight;
4. Saga-owned Standard Core runtime and built-ins;
5. Saga-owned Edition 2027 Preview semantics used by the 14-case conformance set;
6. Saga-owned source loader and deterministic user token-image lowering;
7. language-neutral C11 bootstrap VM/launcher with no Saga grammar/type policy;
8. Stage1 -> Stage2 -> Stage3 fixed point;
9. deterministic Stage2/Stage3 kernel lowering;
10. empty-PATH official runtime and self-host compiler validation;
11. source-boundary and sanitizer review.

`implementations/go/` and `saga/` remain in the repository as reference
implementations only. The official SH-3 runtime path is defined by
`implementations/sh3/OFFICIAL_IMPLEMENTATION.json`.
