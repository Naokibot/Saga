# Saga 0.29.0 Natural Core Validation

## Scope

This file records first-party validation of the reviewed Natural Core source tree. It is not a third-party audit or physical platform qualification.

## Follow-up defect verification

The 2026-08-12 follow-up review reproduced and repaired:

- false Natural-feature detection for lexically captured mutable variables in Standard native bundle analysis;
- missing standalone first-class closure expressions;
- incorrect closure `return` typing and enclosing-function return-type leakage;
- trailing-closure/control-flow brace ambiguity for call expressions in `if` / `while` / `for` headers;
- `break` / `continue` leakage across closure and nested-function boundaries.

Each repair has a dedicated regression test.

## Test results

The complete unittest inventory contains **260 tests** after the third-review regressions. After the source-manifest is regenerated, all 260 tests are required to pass.

Additional validation performed in this review:

- Python `compileall` over `saga/`, `tests/`, and `tools/`: PASS.
- Built-in self-conformance: **24 / 24 PASS**.
- Fuzz smoke: **100,000 parser cases + 25,000 expression cases**, unexpected host exceptions: **0**, PASS.
- Othello self-play regression: PASS.
- Standard native lexical-closure bundle regression: PASS when the Go toolchain is available in this environment.

## Natural Core behaviors explicitly verified

- `name = "Saga"` introduces an immutable inferred binding.
- `greet = { print("Hello") }` is a zero-argument first-class closure.
- contextual collection callbacks receive implicit `it`.
- parameterized stored closures can use an explicit `fn[...]` contextual type.
- `return` exits the closure itself and is independent of an enclosing function return type.
- callback return paths must agree on a compatible result type.
- `if ready() { ... }`, `while condition() { ... }`, and `for x in values() { ... }` preserve their body braces.
- a trailing closure inside a control header is explicitly disambiguated with parentheses.
- `break` and `continue` cannot jump across callable boundaries.
- Natural syntax unsupported by the independent Go/native frontend continues to fail closed instead of being mislabeled conforming.

## Evidence boundary / open gates

The following remain open and must not be represented as completed by this first-party review:

- full independent Go/native implementation parity for Natural 0.29;
- differential conformance across two independent implementations;
- third-party security/source audit bound to the final source manifest;
- Windows/macOS/iOS/Android and physical hardware qualification for final binaries;
- GA 1.0 promotion.

The correct status remains **Natural Core Preview**.

## Final reviewed-tree result

- Complete unittest suite: **260 / 260 PASS** across the bounded test groups used for this review.
- Built-in self-conformance: **24 / 24 PASS**.
- Fuzz smoke: **125,000 total generated cases**, unexpected host exceptions: **0**, PASS.
- Final source manifest is regenerated after this report and must self-verify before packaging.

## Third-review defect verification

The third review additionally verifies:

- migration does not alter strings or comments while still rewriting safe code spans;
- Natural pipeline names (`map`, `distinct`, `sorted`, `take`, `fold`, `none`) execute through the collection extension surface;
- legacy pipeline `reduce` / `find` preserve their historical collection argument position;
- duplicate closure parameter names are rejected;
- pipeline-stage closures do not steal `if` / `while` / `for` body braces; parenthesized headers explicitly enable them;
- nested blocks and `try/finally` participate correctly in guaranteed-return analysis;
- failed REPL submissions do not leave uncommitted top-level bindings/functions in runtime-only state;
- repeated REPL class checks, inheritance, interfaces, and abstract bases remain valid across submissions;
- formatter parse round-trip: **55 / 55 compilable repository Saga sources PASS**;
- parser/expression fuzz smoke: **125,000 generated cases, 0 unexpected host exceptions**.

## Independent implementation check after third review

- Go implementation regression: `go test ./...` — PASS.
- Python reference Self Conformance: **24 / 24 PASS**.
- Python↔Go differential run over the current 24-case self-conformance inventory: **15 / 24 match**.
- The 9 mismatches are Natural 0.29 surface cases (`SC015`–`SC020`, `SC022`–`SC024`) that the independent Go frontend does not yet implement. This is an expected open parity gate, not a PASS claim.
- Consequently the release remains **Natural Core Preview** and must not be promoted to GA 1.0 on the basis of this first-party review.

## Fourth-review type/dynamic-boundary verification

The fourth review adds explicit verification for:

- function result covariance and parameter contravariance;
- invariant standard generics;
- lexical visibility of generic type variables in local declarations/functions;
- rejection of unknown nominal types;
- consistent local-function hoisting in loop/catch blocks;
- runtime enforcement of concrete typed bindings/fields after `any`;
- deep REPL rollback for object and captured-closure mutation;
- fail-fast rejection of non-Send local Saga functions at `task.spawn`;
- structured failure for host stack exhaustion during source-unit traversal;
- runtime function-signature checks for `any -> fn[...]`;
- concrete runtime substitution of generic type variables at dynamic boundaries;
- standard/native `list[any]`-style host wildcards without weakening user-generic invariance.

The fourth-review regression module contains **16 / 16 passing tests**. Split-suite regression runs before final manifest generation are repeated after the final checker fix; the final non-platform and platform totals are recorded below. The remaining 9 platform/evidence tests are executed only after the final source manifest is regenerated because they intentionally reject a modified tree with a stale manifest.

## Final fourth-review regression summary

- Non-platform unittest groups after the final checker/runtime fixes: **267 / 267 PASS**.
- Platform/evidence unittest group after source-manifest regeneration: **9 / 9 PASS**.
- Total unittest inventory: **276 / 276 PASS** when executed in bounded groups.
- Fourth-review dedicated regression module: **16 / 16 PASS**.
- Formatter parse/compile round-trip over standalone compilable repository Saga sources: **55 / 55 PASS**.
- `python -m compileall` over `saga/`, `tests/`, and `tools/`: PASS.
- Built-in Python Self Conformance: **24 / 24 PASS**.
- Fuzz smoke: **100,000 parser + 25,000 expression cases**, unexpected host exceptions: **0**.
- Independent Go implementation: `go test ./...` — PASS.
- Python↔Go differential Natural/Standard corpus: **15 / 24 match**; the 9 Natural 0.29 frontend cases remain an explicit independent-implementation parity blocker.

A long single-process aggregate run was also attempted. Resource inspection after completed modules showed one live Python thread, stable file-descriptor count, and no live child processes; no persistent Saga runtime resource leak was demonstrated. The aggregate run could stall in the external attestation-verifier test because that test lacked subprocess timeouts. The test now uses a 30-second fail-closed timeout. The release claim is therefore the bounded-group **276 / 276** result above, not an unsubstantiated single-process PASS claim.

## Fifth-review validation — propagation/AOT/task/path hardening

The fifth review added executable regression coverage for:

- `result` and `option` postfix `?` propagation, early return, and incompatible enclosing/error contracts;
- Standard native bundle execution of `?` after Python↔Go differential parity was confirmed;
- scalar AOT rejection of exact rational division rather than integer truncation;
- checked int64 overflow rather than silent signed wraparound;
- lexical block-scope preservation in scalar AOT;
- multi-argument print layout and UTF-8/non-BMP text emission;
- single, left-to-right evaluation of range endpoints;
- fail-closed lowering when C cannot preserve effectful operand order;
- single evaluation of `abs` arguments;
- checked modulo-by-zero and the signed-overflow remainder corner;
- C-keyword-safe deterministic identifier mangling;
- preservation of Saga `throw` identity through `task.await` and `task.all`;
- no-symlink source-entry enforcement across CLI, project manifests, debugger, capability audit, and AOT entry paths.

### Pre-manifest regression

- Fifth-review dedicated regression module: **17 / 17 PASS**.
- Non-platform unittest inventory: **284 / 284 PASS** in bounded groups.
- `python -m compileall -q saga tests tools`: PASS.
- Specification final-candidate lint: PASS (all checks).
- Python Self Conformance after adding propagation coverage: **25 / 25 PASS**.
- Fuzz smoke: **100,000 parser + 25,000 expression cases**, unexpected host exceptions: **0**.
- Independent Go implementation: `go test ./...` — PASS.

Platform/evidence tests, Python↔Go differential evidence, final source-manifest digest, and extracted-package verification are executed after this report is source-bound and are recorded in the final subsection below.

### Final fifth-review regression summary

- Final non-platform unittest inventory after all fifth-review code changes: **284 / 284 PASS**.
- Final platform/evidence inventory is rerun against the regenerated exact-tree source manifest; the expected inventory is **9 tests** and any failure blocks the reviewed package.
- Total Python unittest inventory for this review: **293 tests**.
- Fifth-review dedicated regression module: **17 / 17 PASS**.
- Python Self Conformance inventory: **25 / 25 PASS** (the added `SC025-result-propagation` case exercises postfix `?`).
- Fuzz smoke: **125,000 / 125,000 generated cases** completed with **0 unexpected host exceptions**.
- Independent Go implementation regression: `go test ./...` — PASS.
- Expanded Python↔Go differential inventory: **16 / 25 match**. The new propagation case matches across both implementations; the remaining nine mismatches are the previously identified Natural 0.29 frontend/parsing cases (`SC015`–`SC020`, `SC022`–`SC024`).
- The release remains **Natural Core Preview** because full Natural 0.29 independent-implementation parity is not complete.

The source-manifest, platform/evidence rerun, and packaged-ZIP extraction checks are performed after this file is finalized so the evidence binds to the exact distributed source tree rather than to an earlier working directory state.

## Sixth-review validation — alias/path/AOT/structured-join hardening

The sixth review added 17 dedicated regression tests covering:

- alias/identity preservation across isolated task globals, receivers, and repeated arguments;
- `task.all` completion-before-failure semantics;
- no-symlink directory writes for `fmt` and `migrate --write`;
- symlinked manifest/project-root rejection before canonicalization in source, CLI, and package paths;
- explicit and default package-output symlink protection;
- scalar-AOT output symlink protection;
- fail-closed scalar-AOT top-level binding capture/mutation;
- scalar-AOT forward top-level calls;
- byte-exact UTF-8 C emission including post-escape hex digits and embedded U+0000;
- finite inclusive range behavior when the endpoint executes `continue`.

### Pre-manifest regression

- Sixth-review dedicated regression module: **17 / 17 PASS**.
- Final non-platform unittest inventory: **301 / 301 PASS** in bounded groups (152 + 149, no overlap).
- `python -m compileall -q saga tests`: PASS.

The source manifest is regenerated only after this report is finalized. Platform/evidence tests and final archive extraction checks therefore bind to the exact reviewed tree rather than an earlier intermediate tree.

### Sixth-review pre-freeze evidence

Before the final source-manifest freeze, the reviewed code produced the following results:

- Python non-platform unittest inventory: **301 / 301 PASS**.
- Platform/evidence unittest inventory on the immediately preceding exact-tree manifest: **9 / 9 PASS**.
- Python Self Conformance: **25 / 25 PASS**.
- Specification review lint: **PASS** (all checks).
- Fuzz smoke: **100,000 parser + 25,000 expression cases**, unexpected host exceptions: **0**.
- Independent Go implementation: `go test ./...` — **PASS**.
- Python↔Go differential inventory: **16 / 25 match**. The same nine Natural 0.29 frontend cases remain unmatched (`SC015`–`SC020`, `SC022`–`SC024`); no new differential regression was introduced by this review.

After these results are written into the source-bound report, `release/source-manifest-0.29.0.json` is regenerated once more. The final distribution procedure then reruns source-manifest verification, the 9 platform/evidence tests, the 17 sixth-review regressions, Self Conformance, and extracted-ZIP verification without modifying source-bound files again. The machine-readable package verification summary is distributed beside the archive rather than recursively modifying this report.

## Seventh-review validation — equality/snapshot/AOT observable semantics

The seventh review adds six dedicated regression tests for:

- result-wrapper equality preserving Saga object identity semantics;
- cyclic `option` and `result` wrapper identity across isolated task snapshots;
- the same cyclic wrapper preservation in REPL rollback snapshots;
- scalar-AOT bool output parity (`true`/`false`, not `1`/`0`);
- eager left-to-right materialization of all native scalar `print` arguments before outer output, including `unit` values;
- fail-closed handling of unit-valued scalar-AOT function parameters instead of emitting invalid C.

### Pre-freeze evidence

- Sixth-review distributed ZIP source manifest verified before modification: PASS (`5c1cd1709a696e159b230b455df87a12e4704f0bc94b70975baac56016af2f0a`).
- Seventh-review dedicated regression module: **6 / 6 PASS**.
- Full non-platform unittest inventory in bounded per-module runs: **307 / 307 PASS**.
- Affected AOT/Language/Package regression subset after the final unit-parameter change: **139 / 139 PASS**.
- Python Self Conformance: **25 / 25 PASS**.
- Specification review lint: PASS.
- Fuzz smoke: **100,000 parser + 25,000 expression cases**, unexpected host exceptions: **0**.
- Independent Go implementation: `go test ./...` — PASS.
- Python↔Go differential inventory before final source-document binding: **16 / 25 match**; the same nine Natural 0.29 frontend cases remain unmatched.

After this report is source-bound, `release/source-manifest-0.29.0.json` is regenerated from the exact final tree. The platform/evidence 9-test inventory, seventh-review regressions, Self Conformance, differential evidence, and extracted-ZIP verification are then rerun without further source changes.

## Eighth-review validation — full-language readiness

The eighth review validates the language as a whole rather than only the defects found in the preceding review passes.

### Pre-freeze executable evidence

- Eighth-review dedicated Python regression module: **9 / 9 PASS**.
- Full non-platform Python unittest inventory, run in bounded groups: **316 / 316 PASS**.
- Independent Go implementation: `go test ./...` — **PASS**.
- Python Self Conformance: **44 / 44 PASS**.
- Go Self Conformance: **44 / 44 PASS**, including a runtime zero-divisor diagnostic. The harness now executes runtime-error cases instead of stopping after a successful checker pass.
- Python↔Go common differential corpus: **44 / 44 match**.
- Additional deterministic generated-source differential run: **1,000 programs, 0 mismatches** after the remainder-zero diagnostic identity was aligned.
- Specification review lint: **PASS** (all checks).
- Fuzz smoke: **100,000 parser + 25,000 expression cases**, unexpected host exceptions: **0**.
- Formatter round-trip/idempotence: **56 / 56 standalone-compilable repository Saga sources PASS**.
- Synthetic large compilation unit: **3,001 lines / 120,796 bytes / 3,000 functions**. Python `saga check`: PASS (about 1.12 s, 124,256 KiB max RSS on this host); Go `saga check`: PASS (about 0.06 s, 22,528 KiB max RSS on this host). These are smoke measurements, not an industrial benchmark.
- Standard Native bundle: Natural binding/closure/pipeline and same-line bare-call/trailing-block programs build and execute with reference-observable output.
- `python -m compileall -q saga tools`: PASS.

### Release boundary

These results establish substantial implementation maturity and independent common-profile agreement, but they do not establish formal implementation equivalence, industry-scale performance, public ecosystem maturity, independent security certification, or physical-device qualification. The release label therefore remains **Saga 0.29.0 Natural Core Preview**.

After this report is finalized, the exact-tree source manifest is regenerated. The **9 platform/evidence tests**, official source-bound differential report, Self Conformance evidence, and extracted-distribution verification are rerun against that frozen tree. Any failure blocks the reviewed package.
