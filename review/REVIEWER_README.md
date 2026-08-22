# Saga 0.26.2 independent review handoff

This directory is the reviewer entry point for the Saga 0.26.2 GA 1.0 review candidate.

## First principle

Do not accept a claim because a project report says PASS. Bind every review to the exact source tree first:

```sh
python tools/review_evidence.py --verify release/source-manifest-0.26.2.json
python tools/reviewer_preflight.py
```

A changed source tree invalidates evidence that names the previous manifest.

## Four GA evidence tracks

1. **Language Specification 1.0 Final** — review `SAGA_LANGUAGE_SPECIFICATION_1.0_FINAL_CANDIDATE.md` and the normative grammar/companion profiles. Sign only the exact proposed-Final hash if no normative-blocking issue remains. See `review/spec/SPEC_REVIEW_GUIDE.md`.
2. **Windows/macOS native-host qualification** — run the same source manifest on the named native OS. Cross-compilation is not accepted. See `review/native-host/NATIVE_HOST_REVIEW.md`.
3. **Public HTTPS Registry Protocol v1** — deploy the provided registry behind verified public HTTPS and run the opt-in live qualification. Localhost/private addresses do not count. See `review/registry/REGISTRY_REVIEW.md`.
4. **Independent security audit** — review source and execute dynamic testing over the mandatory scope. Deliver a report plus a signed, source-manifest-bound attestation. See `review/security/SECURITY_AUDIT_SCOPE.md` and `review/security/SECURITY_REVIEW_COMMANDS.md`.

## Acceptance rule

`python tools/ga_readiness.py` may return `ga_ready: true` only when all mandatory evidence for the *same 0.26.2 source* is present and valid. Internal review is not substituted for an independent review, and hosted VMs/cross-builds are not described as physical hardware.

## Reporting findings

For each finding provide: severity, affected path/line or protocol operation, reproduction, security/correctness impact, expected behavior, and whether it blocks 1.0 Final/GA. Please avoid sending private signing keys, Registry bearer tokens, cloud credentials, or unredacted user data.
