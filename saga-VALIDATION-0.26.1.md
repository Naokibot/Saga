# Saga 0.26.1 validation report

Validation host: Linux x86-64. Release purpose: second independent-review-candidate hardening pass.

## Current completed validation

| Validation | Result |
|---|---:|
| Python regression | **195/195 PASS + 4 subtests** |
| Go full test suite | **PASS** |
| `go vet ./...` | **PASS** |
| `sagaffi`, `sagajit`, combined FFI+JIT tagged suites | **PASS** |
| `sagadesktop`, `sagadesktop+sagavulkan` tagged suites | **PASS** |
| Go Race Detector | **87/87 named tests PASS in split qualification** |
| Hosted API | **168/168 PASS across 28 modules** |
| Registry Protocol v1 Python↔Go interoperability | **8/8 PASS** |
| Python↔Go differential conformance | **13/13 PASS** |
| Defensive security API | **PASS** |
| Native Game API | **101/101 PASS** |
| Browser Host API | **101/101 PASS** |
| Universal App Action API | **PASS** |
| Machine smoke | **PASS** |
| Real Chromium | **Chrome/144.0.7559.96 Blink/V8 PASS** |
| Parser fuzz | **100,000 cases; 0 unexpected host exceptions** |
| Expression fuzz | **25,000 cases; 0 unexpected host exceptions** |
| Internal automated security audit | **PASS / 0 unresolved findings** |
| SH-3 Standard Core | **23/23 PASS** |
| SH-3 diagnostics | **11/11 PASS** |
| SH-3 Edition 2027 | **15/15 PASS** |
| SH-3 source-boundary audit | **0 problems** |

## Go Race qualification

The monolithic Race Detector invocation can exceed the outer execution harness window and is not treated as successful merely because of a timeout. The current Go package exposes **87 named tests**; all 87 were executed under `-race` in bounded split groups and passed. The reviewer-facing qualification enumerates the current test names rather than relying on a hard-coded historical count.

## SH-3 fixed-point evidence

The monolithic SH-3 helper likewise can exceed one outer execution window, so the gates were executed independently rather than relabeling the timeout as PASS.

- strict C11 bootstrap VM/launcher: PASS
- compiler Stage2 == Stage3: PASS
  - SHA-256: `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`
- canonical kernel Stage2 == Stage3: PASS
  - SHA-256: `a044627a6abde1783bcece40ffa976f72d129a0cf31538d06b62162c4dce4237`
- Standard Core success corpus: 23/23 PASS
- diagnostic corpus: 11/11 PASS
- Edition 2027 corpus: 15/15 PASS
- source loader: PASS, output `42`
- deterministic SH3IMG1 generation/execution: PASS
  - image SHA-256: `aaa2661cdec4a115f61df6c8bc37cafc090eb388725fbb8e331755c7e286c060`
- empty-PATH `saga run`, `saga info`, and `sagac` compile/execute: PASS
- source-boundary audit: 0 problems

The authoritative current SH-3 input corpora are stored under `conformance/sh3/` so that the frozen source manifest binds the test vectors as well as the implementation.

## Registry evidence

The local interoperability validation exercises both directions:

- Go client publishes a signed package to the Python server;
- Python search/install verifies and explicitly trusts the Go publisher;
- Python client publishes a signed package to the Go server;
- Go search/install verifies and explicitly trusts the Python publisher;
- immutable-version semantics and package identity are checked.

Persisted packages are revalidated on read/idempotent retry, lock snapshots are checked after staged extraction in both implementations, duplicate key/path ambiguity is rejected and resource limits are enforced.

The **public external HTTPS** qualification is intentionally separate from this local interoperability evidence. Its qualifier requires a globally routable actual TLS peer, verified TLS/SNI, current-source binding and the cross-implementation roundtrip.

## Security/evidence-chain validation

Regression tests cover current-source rebinding, stale/malformed evidence rejection, exact audit-report hashing, source-manifest duplicate/symlink/mismatch rejection, post-review Final-spec promotion semantics, Registry bearer-token non-disclosure, exclusive key generation, lock parity and stored-package corruption handling.

## External limitations / non-claims

The following are not claimed PASS on this Linux validation host:

- independent specification approval and Final promotion;
- Windows target-host qualification for the frozen current source;
- macOS target-host qualification for the frozen current source;
- a live non-local globally routable verified-HTTPS Registry qualification;
- an independent third-party signed security audit;
- optional physical GPU/gamepad/GPIO/mobile/vendor-service evidence where the corresponding hardware/service is absent.

Cross-builds, mocks, software renderers, local Registry servers and project-internal security review do not satisfy those external gates.
