# Saga 0.23.0 validation report

Validation host: Linux x86-64. Release focus: Universal App Action Protocol plus regression preservation of Saga 0.22 functionality.

## Results

| Validation | Result |
|---|---:|
| Go Native tests | PASS |
| Go `vet` | PASS |
| Go Race Detector | PASS |
| Python reference | **155/155 PASS + 4 subtests** |
| Native game API alignment | **101/101 PASS** |
| Browser Host API alignment | **101/101 PASS** |
| Universal App source API | **10/10 PASS** |
| Universal App browser operation manifest | **53 operations PASS** |
| Real Chromium | **Chrome/144.0.7559.96 PASS** |
| Parser fuzz | **100,000; 0 unexpected host exceptions** |
| Expression fuzz | **25,000; 0 unexpected host exceptions** |
| Internal automated security review | **PASS; 0 unresolved issues** |
| SH-3 Standard Core | **23/23 PASS** |
| SH-3 diagnostics | **11/11 PASS** |
| SH-3 Edition 2027 | **15/15 PASS** |
| SH-3 source-boundary audit | **0 problems** |

## Real Chromium

Chromium executes the canonical SH-3 browser kernel and Edition 2027 Saga source inside real Blink/V8 via CDP. DOM/title/attributes/classes/styles/forms, Canvas PNG generation, click/input/timer/fetch, Universal App host/capability discovery, synchronous invocation, asynchronous action event and lifecycle event paths pass. The machine is managed with `URLBlocklist=["*"]`; the validator does not change or bypass that policy, so HTTP top-level PWA navigation/service-worker registration is not claimed from this Chromium run.

## Universal App Action qualification

The action manifest contains 10 Saga source methods and 53 first-party browser operation identifiers. Validation checks the checker, canonical SH-3 kernel, browser host protocol, Native protocol and absence of a raw browser-eval escape hatch. Native tests exercise system snapshot, filesystem roundtrip, UUID formatting, unknown-operation rejection and JSON-object payload enforcement.

## SH-3 fixed point

Compiler Stage2/Stage3 SHA-256: `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`.

Canonical kernel Stage2/Stage3 SHA-256: `ac6b15c0c3b0f4e7d0e290ad1edf6d3d28fb10a7ad4b1871209104bfcfe044e6`.

The monolithic SH-3 validator exceeded a single execution window; qualification was therefore rerun in split stages. Timed-out work is not counted as PASS. The split stages cover compiler fixed point, kernel fixed point, Standard Core, diagnostics, Edition 2027, source loader/image, empty-PATH distribution and source-boundary audit.

## Limits

This release proves language-level expressibility and selected host adapters; it does not prove every external vendor API, hardware device, account, payment provider or mobile entitlement works on every platform. Permission- or device-dependent operations must be qualified on the target host. The security review is project-internal, not an independent third-party audit.
