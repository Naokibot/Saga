# Saga 0.29 — Full-Language Readiness Review

Status: **Natural Core Preview; serious controlled-project capable, not 1.0 GA.**

## Executive judgement

Saga is no longer a toy interpreter or syntax prototype. It has a real lexer/parser, static checker, runtime, two independently implemented frontends/runtimes for the declared Natural Core profile, exact-number semantics, objects/generics/interfaces, Option/Result, exceptions, closures, structured task APIs, packages/locks, diagnostics, formatter/linter/LSP/REPL, capability-gated hosted APIs, and native/WASM build paths. Natural Core source, including trailing closures, pipelines and same-line bare calls, can be packaged into the Go-based Standard Native bundle without the Python runtime.

For a controlled application, teaching/research environment, internal tool, or a project willing to pin the compiler/runtime release, Saga is technically usable as a general-purpose language. It should **not** yet be marketed as a mainstream production language or Saga 1.0 GA. The remaining gates are architectural and ecosystem-level rather than merely missing syntax.

## Readiness matrix

| Area | Judgement | Evidence / remaining concern |
|---|---|---|
| Grammar and semantics | Strong | Natural syntax is parsed and executed by Python and Go; ambiguity regressions are tested. |
| Type safety | Strong preview | Function variance, generic invariance, dynamic `any` boundaries and runtime generic substitution are checked; further soundness fuzzing remains desirable. |
| Error model | Strong | Stable Saga diagnostics are used instead of leaking host exceptions; runtime-diagnostic conformance is now tested end-to-end. |
| Standard/Natural APIs | Strong | Collection, text, map and set Natural surfaces are implemented in both common implementations. |
| Independent implementation | Materially improved | Common conformance corpus agrees in both implementations; randomized differential testing supplements it. This is not formal equivalence. |
| Native delivery | Strong preview | Standard Native bundle executes Natural bindings, closures, pipelines and bare-call DSL syntax. Scalar C AOT remains intentionally fail-closed subset. |
| Toolchain | Strong preview | CLI, REPL, formatter, linter, migration, LSP, package/lock, diagnostics and qualification tools have regression coverage. |
| Multi-file architecture | **Needs work for very large projects** | Natural/legacy source units share one compilation namespace. Edition 2027 namespaced modules exist in the Go preview, but are not yet the common reference-language module model. |
| Performance/scalability | Promising, not proven at industry scale | Large synthetic compilation units are accepted, but multi-million-line builds, incremental compilation and long-running production workloads have not been independently benchmarked. |
| Ecosystem/governance | **Not GA-ready** | Public package ecosystem depth, long-term compatibility governance, third-party implementations/adoption and independent audits remain external gates. |
| Physical/platform claims | Evidence-gated | Device/GPU/mobile/OS qualifications must stay separate; simulated/cross-build evidence is not physical certification. |

## Changes made by this review

1. Fixed assignment target/RHS evaluation order in the reference runtime.
2. Made Natural first binding follow inferred `let` shadowing rules.
3. Hardened project/source path handling against symlink-component policy bypasses while preserving relative project discovery.
4. Ported Natural binding, first-class/trailing closures, pipeline lowering and Natural extension APIs to the independent Go implementation.
5. Added same-line bare-argument calls and trailing-block DSL calls to Go using the same conservative ambiguity rules as the reference parser.
6. Removed the obsolete Standard Native parity refusal for Natural bare calls after executable parity was demonstrated.
7. Expanded self/differential conformance to include Natural APIs, bare-call ambiguity and runtime diagnostics.
8. Fixed the Go conformance harness so expected runtime errors are actually executed and verified.
9. Stabilized remainder-by-zero diagnostic identity across implementations.
10. Clarified implementation-release versus language-spec/edition metadata in Go `info`/conformance output.

## Required gates before 1.0 GA

- Make namespaced modules/export visibility a common, normative Python+Go language path rather than a Go-only preview or shared-namespace inclusion model.
- Add broader property-based / AST-generated cross-implementation differential testing and retain minimized regressions.
- Dogfood Saga on at least one substantial multi-module application and measure build time, runtime behavior, memory, debugging and upgrade cost.
- Establish explicit compatibility/deprecation policy and release governance.
- Maintain a real public package ecosystem with signed/reproducible publishing and operational registry evidence.
- Obtain independent security/compiler review and keep physical target qualification separate from simulated evidence.

The correct release label remains **Saga 0.29.0 Natural Core Preview**.
