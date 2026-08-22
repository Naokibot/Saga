# Saga 0.9.0 review report

Date: 2026-08-07

## Review objective

Review Saga 0.8.0 as an international-standard candidate with particular emphasis on beginner-readable diagnostics, locale independence, Unicode portability, conformance-test stability, editor integration, specification/implementation consistency, packaging, and release installation.

This is a project-internal engineering review, not an ISO/IEC approval, independent security audit, or independent laboratory certificate.

## Findings and fixes

| Severity | Finding | Resolution in 0.9.0 |
|---|---|---|
| High | Portable conformance tests depended on Japanese error prose, so a semantically identical English implementation could fail. | Failure cases now use exit status + stable diagnostic category; the Python reference suite additionally checks detailed machine diagnostic IDs. |
| High | Malformed UTF-8 could fail in the CLI file reader before reaching Saga diagnostics. | Source reading is unified through the compiler source-unit reader; malformed UTF-8 is `SAGA-L001` / detailed `SAGA-L104`. |
| High | The 0.8 Working Draft said Saga had no fixed normative ceilings while the project manifest still imposed a 64-character project-name ceiling. | Removed the Saga-fixed project-name length ceiling; retained NFC/XID/path-safety rules. |
| High | A first LSP bridge using Saga scalar columns would be wrong after non-BMP characters because LSP historically uses UTF-16 positions. | Implemented LSP position-encoding negotiation and UTF-16 conversion; regression test uses an emoji before an error. |
| Medium | Broad diagnostics such as `SAGA-T001` did not tell learners what specifically failed. | Added stable detailed IDs, localized titles, causes, repair suggestions, explanations and `saga explain`. |
| Medium | NFC failures and bidi-control failures were grouped under generic lexical errors. | Added `SAGA-L105` and `SAGA-L106` with security-oriented explanations. |
| Medium | Diagnostic text was primarily Japanese and CLI locale options were closed to two enumerated values. | Added Japanese/English catalogue, BCP-47-style locale input, deterministic English fallback, and locale-independent machine output. |
| Medium | CI/editor tooling would need to scrape terminal text. | Added JSON diagnostic schema 2, SARIF 2.1.0, machine-readable diagnostic catalogue, JSON Schema, and stdio LSP diagnostics. |
| Medium | SARIF metadata used a placeholder `example.invalid` information URL. | Removed invented external product URL; SARIF carries only verifiable local tool metadata. |
| Medium | Compatibility snapshot tooling was tied to an older grammar path. | Snapshot now records `spec/saga-0.9.ebnf` and explicit 0.9 semantic/tooling changes. |
| Medium | The independent-lab packager referenced an unavailable compatibility snapshot in the older release. | Added the 0.8 baseline snapshot and current 0.9 snapshot; lab package is generated from current files with SHA-256 manifest. |
| Medium | Fuzz smoke tooling required an unstated `PYTHONPATH` environment configuration. | Tool resolves and inserts the repository root itself, making the published command reproducible. |
| Medium | Native installer verified versions but did not execute post-install language conformance. | Installer now runs `saga conformance --json` and refuses a deployment that does not report `pass=true`. |
| Low | Terminal range rendering counted some Unicode format/mark characters as visible width. | Combining marks and format characters are zero-width in the human renderer while normative columns remain Unicode-scalar based. |
| Low | Active documentation retained stale 0.8 limits and installer names. | Updated active 0.9 documentation and separated historical versioned documents from current aliases. |

## Diagnostic architecture

Saga now separates three layers:

1. **broad stable category** — `SAGA-L001`, `SAGA-P001`, `SAGA-T001`, `SAGA-R001`, resource/internal variants;
2. **specific stable diagnostic ID** — e.g. `SAGA-T101` immutable assignment, `SAGA-T102` unknown name, `SAGA-L104` malformed UTF-8;
3. **localized presentation** — title, dynamic detail, repair suggestion and explanation.

Conformance tools consume layers 1–2 and source ranges. They do not parse layer 3.

## Source compatibility

The API snapshot comparison found no removed builtins, keywords, or standard-module functions from 0.8 to 0.9. Source compatibility is reported as true. The compatibility checker intentionally reports behavioral/tooling incompatibility because diagnostics, invalid-UTF classification, project-name acceptance, and editor integration semantics changed.

## International-standard readiness judgment

0.9.0 is materially more reviewable as an international-standard candidate because:

- English normative prose and machine-readable EBNF are versioned together;
- Unicode identifier acceptance is frozen to a vendored version instead of the host runtime;
- human language is separated from conformance semantics;
- diagnostic interfaces are documented for CLI, CI, SARIF and LSP;
- exact arithmetic, task isolation, resource exhaustion, capabilities and unspecified behavior are separately specified;
- reference and independent PCL1 implementations have a differential suite;
- release packaging, compatibility snapshots and lab handoff are reproducible project artifacts.

Remaining external/engineering gates are intentionally not marked complete: eligible standards sponsorship, Project Leader and international experts, global market evidence, independent full Standard Core implementation, independent conformance/security review, name/trademark clearance, committee ballots, and publication.
