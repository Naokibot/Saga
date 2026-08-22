# Saga 0.18 self-hosting boundary

Saga 0.18 deliberately separates three claims:

1. **Operational independence — implemented.** Released Saga Native can run/check/build/test/package ordinary Saga programs without requiring Python, Go, Java, Node.js or another language runtime on the user's machine.
2. **Saga-sourced compiler-driver fixed point — implemented.** `selfhost/sagac.saga` is bundled Stage1 -> Stage2 -> Stage3 and Stage2/Stage3 must be byte-identical.
3. **All compiler/runtime source written in Saga — not yet implemented.** The primary lexer/parser/checker/interpreter/native execution kernel still has a published Go bootstrap implementation under `implementations/go/`.

The project previously used “self-hosted compiler” loosely for item 2. 0.18 tightens the terminology so a fixed-point driver is not confused with a fully Saga-authored compiler frontend/backend/runtime.

A future `All-Source Self-Hosting` profile may be claimed only when the normative lexer/parser/type checker/code generator/runtime sources used to build the official implementation are themselves Saga source, with a documented minimal bootstrap seed and diverse-double-compilation evidence. Until then `saga info` reports `all_runtime_source_self_hosted=false`.
