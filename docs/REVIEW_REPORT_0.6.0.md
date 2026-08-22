# Saga Language Review Report — 0.6.0

## Scope

The review covered the lexer, parser, type checker, interpreter, object model, exact-number semantics, JSON/SQL boundaries, collections, concurrency, capability system, standard library contracts, command-line tools, standardization registry, Python packaging and the independent Go subset.

## High-severity corrections

1. **Class/interface subtyping was advertised but rejected by the checker.** Added inheritance and interface assignability, including run-time checks at dynamic boundaries.
2. **Accidental method replacement was possible.** Added mandatory `override` and compatibility validation.
3. **Host null leaked through JSON and SQL.** Added `option[T]`; JSON null/SQL NULL now become `none()` and cannot enter non-option ORM fields.
4. **Exact JSON behavior was not exact.** Decimal JSON numbers no longer pass through binary float; duplicate keys and nonstandard NaN/Infinity are rejected.
5. **Native APIs trusted host values without contracts.** Added argument and result validation for native and explicitly typed user functions.
6. **Native resources could leak when user code omitted close.** Added interpreter-owned resource cleanup.
7. **Standardization evidence status did not re-hash stored evidence.** Added evidence-file verification and excluded invalid records from readiness calculations.
8. **The Go implementation was counted too broadly.** Added explicit `experimental`, `core`, and `full` evidence levels; only evidenced core/full implementations qualify.

## Medium-severity corrections

- map keys and set elements now require hashable types;
- map/set lookup and removal validate key/element types;
- `unique` supports nested immutable lists without host hashing;
- set output is deterministic;
- higher-order functions validate callable parameter and predicate result types;
- annotation arguments are restricted to compile-time literal data;
- malformed numeric separators are rejected consistently;
- exponentiation is right-associative and binds above unary minus;
- project versions require SemVer and manifest paths cannot escape the root;
- the REPL preserves checked state transactionally;
- stable diagnostic categories were added;
- private fields are excluded from JSON and reflection;
- hosted return values are frozen into Saga-safe immutable values.

## Toolchain additions

- `saga fmt` and `saga fmt --check`;
- `saga lint --standard` and `--deny-warnings`;
- `saga test` with project-manifest discovery;
- `saga.toml` validation;
- stateful REPL;
- compatibility snapshot tooling;
- evidence-backed standardization verification.

## Remaining blockers for a mature general-purpose standard language

- no source-module/package resolver;
- no package signing, lock file or registry;
- no native compiler, stable ABI or language server;
- generic constraints and variance are not specified;
- Go implementation covers only Portable Core Level 1;
- performance, fuzzing, security review and portability evidence remain limited;
- no independent certification or ISO/IEC approval.

The release should therefore be described as a **Standard Profile Preview**, not a production-standard or ISO-standard language.
