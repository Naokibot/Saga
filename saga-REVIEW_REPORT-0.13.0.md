# Saga 0.13.0 — source review report

## Scope

Reviewed the 0.12 codebase and the 0.13 changes across:

- independent Saga Native lexer/parser/type checker/runtime;
- Python reference lexer/parser/checker/interpreter;
- generic type relations;
- lexical closures;
- project tools and deterministic packaging;
- self-host compiler bootstrap;
- native installer;
- diagnostics and educational tooling;
- formatter/linter/test runner/REPL;
- Hosted reference APIs and plugin/security boundaries.

## Important issues found and fixed

### 1. Generic inheritance did not preserve type arguments

Before 0.13, `extends Box[int]` and `implements Repository[T]` could not be
represented fully by the Native class relation model. Relations now store full
type references, and inherited fields/method contracts are specialized before
override checking.

### 2. Python reference implementation lagged the Native generic model

The Python parser stored only relation names and therefore could not independently
check the same generic relation semantics. It now parses relation types and
performs generic-specialized inheritance/interface checks. Runtime inherited
field contracts are specialized as well.

### 3. Self-hosting was impossible from an already bundled compiler

0.12 standalone builds rejected nested compilation and copied an existing bundle
recursively. 0.13 identifies the native runtime prefix, strips an existing Saga
bundle, and can deterministically create the next compiler stage.

### 4. Installer previously accepted the seed-built compiler directly

0.13 installer now performs Stage1 -> Stage2 -> Stage3 on the target and installs
Stage2 only when Stage2 and Stage3 are byte-identical.

### 5. Native developer tooling was incomplete

The official no-external-runtime distribution now provides native `fmt`, `lint`,
`test`, and a stateful `repl` in addition to run/check/build/project/package and
conformance commands.

### 6. Language-version policy was inconsistent

New Native/Python project generation now targets Saga Language Edition 1.0 Draft.
Legacy project editions remain accepted for compatibility.

### 7. Broad fallback in inherited Python runtime-field specialization

A broad `except Exception` introduced during generic specialization could hide an
internal defect. It was removed; invalid relation types now become explicit Saga
runtime/type diagnostics instead of being silently ignored.

## Stability decisions

No additional everyday syntax was introduced after the generic-relation repair.
The rest of the release focused on deterministic builds, fixed-point compiler
proof, stable diagnostics, tooling, tests and compatibility.

## Remaining limitations

- Compiler self-hosting is fixed-point and Saga-sourced, but the Native execution
  kernel still has an independently seeded implementation source under Go.
- Windows and ARM64 binaries are cross-built and format-checked in this host;
  target hardware execution remains separate evidence.
- Hosted adapters that need cloud accounts, physical GPIO or Spark are not made
  part of Standard Core merely to claim breadth.
- Saga 1.0 is still a draft language edition; 0.13.0 is a pre-1.0 implementation.
