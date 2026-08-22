# Saga 0.33.0 Validation Report

Release: **0.33.0 — Human-Centered Native Value ABI Preview**

## Final release inventory

- Python unittest inventory excluding manifest-bound Platform/Evidence: **356 / 356 PASS**.
- Final Platform/Evidence inventory: **9 tests**, rerun against the final source manifest and required to be 9/9 before packaging.
- Python Self Conformance: **46 / 46 PASS**.
- Go Self Conformance: **46 / 46 PASS**.
- Natural common Python↔Go differential: **46 cases**, rerun source-bound after the final manifest and required to be 46/46.
- Module graph cross-implementation conformance: **13 / 13 PASS** before final source binding; the final run is repeated after manifest creation.
- 0.33 Human-Centered/Native Value dedicated regression: **9 / 9 PASS**.
- Native Codegen regression inherited from 0.32: **8 / 8 PASS**.
- Native Codegen qualification: **17 / 17 PASS**.
- Fuzz smoke: **100,000 parser cases + 25,000 expression cases = 125,000**, unexpected host exceptions: **0**.
- `go test ./...`: PASS.
- `python -m compileall saga tools`: PASS.
- Specification review lint: PASS.

The release is not considered fixed until Platform/Evidence, differential and
module conformance are rerun against `release/source-manifest-0.33.0.json`, and
the distribution ZIP is extracted into a clean directory and checked again.

## Native Value ABI evidence

Direct machine-code builds exercised:

- borrowed UTF-8 `text` parameters and return values, including Japanese text;
- `option[int]` construction, absence and unwrap-with-default;
- `result[int,text]` construction and unwrap-with-default;
- postfix `?` result early-return propagation;
- cross-module `text` and `option` direct native symbols;
- generated C headers calling Saga `text` and `option` functions directly.

The direct ABI deliberately fails closed on class/object and native enum layout.
Owned text/GC semantics are not inferred from the borrowed text ABI.

## Human-centered language evidence

- `enum` + `match` executes in the Python reference implementation.
- Missing enum variants fail with `SAGA-T112`.
- `unless` is normalized to the existing `if not` semantic model.
- public enums preserve qualified nominal identity across modules.
- Python and Go generate identical enum-bearing SMI exports, ABI SHA-256 and
  build SHA-256.

## Evidence boundary

Passing these tests is strong regression and cross-implementation evidence for
the tested profiles. It is not evidence of independent third-party audit,
formal proof, hard-real-time certification, or untested physical platforms.
