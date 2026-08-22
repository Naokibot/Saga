# Saga 0.9 diagnostic model

Status: candidate normative support document.

## Goals

Saga diagnostics are designed for learners, professional developers, IDEs, CI systems and independent conformance laboratories. Human prose is never the machine contract.

Each diagnostic exposes:

- a stable broad category (`SAGA-L001`, `SAGA-P001`, `SAGA-T001`, `SAGA-R001`, and resource/internal variants);
- a detailed diagnostic ID such as `SAGA-T101`;
- severity;
- source URI/name;
- a 1-based Unicode-scalar source range;
- a localized title and detail;
- a repair suggestion when one is known;
- a short explanation;
- an exit status defined by the CLI profile.

## Human output

Human output shall remain readable without colour. The reference renderer accounts for tabs, combining marks and East Asian wide/full-width characters when placing the visual marker. Normative columns remain Unicode-scalar positions so terminal display width cannot change a tool result.

Example:

```text
error[SAGA-T101]: Cannot assign to an immutable binding
  --> example.saga:2:1
   |
     2 | score = 90
   | ^^^^^ `score` is immutable because it was declared with `let`.
category: SAGA-T001
help: If mutation is intended, change the declaration from let to var.
why: Bindings declared with let are immutable. Mutable state must be declared explicitly with var.
more: saga explain SAGA-T101 --language en
```

## Localization

Japanese and English are bundled in the reference implementation. Diagnostic language does not change lexing, parsing, type checking, runtime semantics, source ranges or exit status. Conformance tests shall not match translated prose.

## Machine output

The machine-readable catalogue is `spec/diagnostics-0.9.json` and the diagnostic envelope schema is `spec/diagnostic-schema-2.json`.

`--diagnostic-format json` emits schema 2. The stable machine fields are `code`, `id`, `severity`, `filename`, `range`, and implementation/language version metadata.

`--diagnostic-format sarif` emits SARIF 2.1.0 for code-review and CI interoperability. Saga's diagnostic ID is the SARIF `ruleId`.

## Explanation command

```text
saga explain SAGA-T101 --language en
saga explain SAGA-T101 --language ja
```

The catalogue is intentionally small enough for high-quality explanations. New detailed IDs require a compatibility note and conformance tests.

## Editor integration

`saga lsp` implements a dependency-free stdio Language Server diagnostics bridge with full-document synchronization. It publishes the same detailed diagnostic ID, broad category, source range, localized explanation and suggested repair used by the CLI. Editor protocol behavior is tooling support and does not change Saga program semantics.
