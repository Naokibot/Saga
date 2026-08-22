# Saga 0.26.2 — Independent Security Review Scope

This document is the minimum scope for an external reviewer. The reviewer is not asked to certify that Saga is vulnerability-free. The requested conclusion is whether the reviewed release has any **open Critical or High severity** finding within the agreed scope and whether the release evidence accurately represents what was tested.

## In-scope components

1. **compiler** — parser, checker, diagnostics, self-host compiler boundary, malformed-source handling;
2. **runtime** — interpreter/native runtime, concurrency/task boundary, file/network/process resource handling;
3. **package-manager** — lock verification, package extraction, publisher trust, staging/rollback, path traversal and archive-bomb resistance;
4. **registry** — authentication, signed publication, immutable versions, identity binding, HTTP limits, TLS deployment boundary;
5. **capability-sandbox** — plugin/processor isolation, `--allow-*` capabilities, fail-closed unsupported platforms;
6. **crypto-tls** — use of platform cryptography, password KDF bounds, AES-GCM, signature verification, certificate/hostname verification;
7. **native-host-boundaries** — Windows/macOS/Linux process/file behavior, FFI/JIT optional boundaries, unsafe/native escape hatches.

## Required methods

The signed attestation must state that both `source-review` and `dynamic-testing` were performed. Fuzzing, dependency review, SAST, manual adversarial tests, or penetration testing may be added and should be described in the report.

## Required evidence

The report must identify the exact `release/source-manifest-0.26.2.json` SHA-256, review dates, reviewer and organization, exclusions, tools, findings, remediation retests, and residual Medium/Low findings. The report itself is bound by SHA-256 in the signed attestation.

## Severity gate

GA security evidence fails closed if any Critical or High finding remains open. Medium/Low findings may remain only when explicitly documented with rationale and owner/timeline.

## Independence

The attestation field `independent` must be `true`. The project must obtain the auditor public key through a channel independent of the submitted attestation. The verifier checks cryptographic integrity; it cannot prove the real-world identity or independence of the key holder.
