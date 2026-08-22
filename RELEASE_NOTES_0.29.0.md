# Saga 0.29.0 release notes — Natural Core Preview

Saga 0.29.0 is a language-surface redesign focused on programmer intent, progressive disclosure and Safe by Default semantics.

Implemented in the Python reference frontend/runtime:

- immutable first-assignment bindings (`name = "Saga"`), with `var` reserved for mutation;
- first-class trailing closures with contextual `it` and explicit multi-parameter blocks;
- method-oriented collection APIs and chaining;
- `|>` pipeline sugar;
- conservative same-line bare arguments for library-defined DSLs;
- contextual higher-order function type checking;
- `saga migrate` for provably safe legacy collection rewrites;
- Natural Core self-conformance cases and regression tests;
- scalar AOT first-assignment lowering.

Review fixes made during this redesign include restoring strict callback contracts after an initial regression, rejecting an ambiguous bare-call/subtraction parse, and adding runtime `fn` validation for Saga closures.

This release does **not** claim that the 0.28 Go/native implementation already conforms to Natural 0.29. Independent/native parity, native closure lowering for the full natural collection surface, external audit, and physical platform qualification remain separate evidence gates.

## Follow-up correctness fixes

A second review of the packaged Natural Core found and fixed several boundary-condition defects: lexical-scope loss in the Standard native feature detector, missing standalone closure expressions, closure-return context leakage, control-header/trailing-closure brace ambiguity, and cross-callable `break`/`continue` leakage. Regression tests and self-conformance cases now cover these behaviors.

## Third review correctness fixes

A further boundary/state review repaired migration rewrites inside strings/comments, incorrect pipeline lowering for legacy `reduce`/`find`, missing Natural pipeline stage names such as `map`/`sorted`, duplicate closure parameters, pipeline/control-header brace ambiguity, incomplete guaranteed-return analysis for nested blocks and `try/finally`, and two REPL consistency defects (failed-submission namespace leakage and non-idempotent class/inheritance checking). The REPL now rolls back uncommitted top-level namespace/declaration changes after a failed submission and incremental class checking is idempotent.

## Fourth review correctness fixes

Type-system and dynamic-boundary review repaired function-subtyping soundness (contravariant parameters/covariant results), invariant generic handling, lexical generic type-variable scope, unknown nominal-type validation, block-consistent local-function hoisting, runtime contracts for values arriving through `any`, deep REPL rollback of Saga-owned object/closure state, fail-fast task Send checks for local functions, structured source-unit stack-exhaustion diagnostics, dynamic callable signature validation, and runtime generic type substitution. Standard/native `list[any]`-style signatures are also treated as hosted-boundary wildcards without weakening user-defined generic invariance. These changes strengthen Safe by Default without changing the Natural surface syntax.

The review harness was also hardened so external attestation-verifier subprocesses have explicit timeouts; CI no longer waits indefinitely on a stalled verifier/host process.

## Full-language readiness review

The independent Go frontend/runtime is now versioned 0.29.0 for the declared Natural Core common profile. Natural bindings, first-class/trailing closures, pipelines, collection/text/map/set extension APIs, same-line bare arguments, and bare-call DSL blocks are implemented in both Python and Go. The common self/differential inventory has been expanded, and Standard Native bundles can execute the Natural surface instead of rejecting it solely for frontend-parity reasons.

The readiness review also corrected reference assignment evaluation order, lexical source/project path-policy ordering, runtime zero-divisor diagnostic identity, and a flaw in the Go self-conformance harness that previously skipped runtime-error cases whenever an error was expected.

Saga remains a **Natural Core Preview**, not a 1.0 GA claim. Common namespaced modules/separate compilation, larger real-world dogfooding, broader generated differential testing, ecosystem/governance maturity, and independent external qualification remain release gates.
