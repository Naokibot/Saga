# Saga 0.26.1 — independent reviewer handoff

Start at `review/REVIEWER_README.md`.

## Candidate identity

This archive is a **Core GA 1.0 review candidate**, not GA and not an ISO/IEC publication. The exact review source is bound by `release/source-manifest-0.26.1.json`. Verify that manifest before reviewing or producing evidence. Evidence that names 0.26.1 but does not bind to that exact manifest/tree is not sufficient.

## Recommended order

1. Run `python tools/review_evidence.py --verify release/source-manifest-0.26.1.json`.
2. Run `python tools/reviewer_preflight.py --quick`; run the full preflight before final disposition.
3. Review the Language Specification Final Candidate using `review/spec/SPEC_REVIEW_GUIDE.md`. Do not create Final by title change; use the signed review/promotion path.
4. Produce native Windows/macOS evidence on those actual operating systems using `review/native-host/NATIVE_HOST_REVIEW.md` and `tools/native_host_qualification.py`.
5. Review/deploy Registry Protocol v1 and execute the external HTTPS run using `review/registry/REGISTRY_REVIEW.md` and `tools/registry_live_qualification.py`.
6. Conduct the independent security review using `review/security/SECURITY_AUDIT_SCOPE.md` and `SECURITY_REVIEW_COMMANDS.md`, then verify the signed attestation with `tools/verify_external_security_attestation.py`.
7. Run `python tools/ga_readiness.py` only after accepted evidence files are placed under `validation/`.

## Evidence principle

Every external PASS must identify the exact current release/source under review. `pass: true` alone is not trusted by the GA aggregator. Cross-builds, localhost registries, private-only addresses, invalid/unverified TLS, project-internal audits, unsigned reviewer claims and stale prior-release evidence do not satisfy the corresponding Core GA gate.

The generated `SAGA_LANGUAGE_SPECIFICATION_1.0.md` is a deliberate post-review artifact: it is accepted only when its exact bytes equal the independently signed proposed-Final SHA-256. Candidate source, grammar and promotion tooling remain frozen by the source manifest.

## 0.26.1 second-review hardening

This patch additionally hardens source-manifest self-integrity, Registry token/key handling, package lock parity, persisted-package corruption detection, repeatable live qualification, actual global TLS peer evidence, source-bound SH-3 qualification corpora and Race/preflight output capture. See `saga-REVIEW_REPORT-0.26.1.md` for findings and `saga-VALIDATION-0.26.1.md` for executed evidence.
